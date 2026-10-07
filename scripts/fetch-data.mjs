#!/usr/bin/env node
// Populate the site's build inputs from the scraper's published data.
//
//   node scripts/fetch-data.mjs                    # download over HTTPS (default)
//   node scripts/fetch-data.mjs --local <data-dir> # copy from a local scraper data dir
//   node scripts/fetch-data.mjs --if-missing       # no-op when the data is already present
//
// Env: SITE_DATA_BASE_URL overrides the default public bucket URL.
//
// No credentials, no bucket listing: the file list is derived from the data
// itself (partners.json events_url/past_events_url, image_src fields).
// Everything is staged in a temp dir and validated before the site's
// directories are touched, so a failed fetch leaves the previous data intact.
// src/data/partners.json (hand-curated) is never written; SCHEMA.md is not copied.

import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const DEFAULT_BASE_URL =
  "https://jtl-stem-ecosystem-scrape.sfo3.digitaloceanspaces.com/data/";

const SRC_ONLY = ["opportunities.json", "scrape-meta.json", "ads.json", "yield-history.json"];
const BOTH = ["teams.json", "places.json", "clubs.json"];
const ENVELOPE = "partners.json";
const CONCURRENCY = 16;

class FetchError extends Error {}

function httpSource(baseUrl, fetchImpl = fetch) {
  const base = baseUrl.endsWith("/") ? baseUrl : baseUrl + "/";
  return async (rel) => {
    const url = base + rel;
    let lastErr;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const res = await fetchImpl(url);
        if (res.status === 200) return Buffer.from(await res.arrayBuffer());
        if (res.status < 500) throw new FetchError(`HTTP ${res.status} for ${url}`);
        lastErr = new FetchError(`HTTP ${res.status} for ${url}`);
      } catch (e) {
        if (e instanceof FetchError) throw e;
        lastErr = new FetchError(`network error for ${url}: ${e.message}`);
      }
    }
    throw lastErr;
  };
}

function localSource(dir) {
  return async (rel) => {
    try {
      return await fs.readFile(path.join(dir, rel));
    } catch (e) {
      throw new FetchError(`cannot read ${path.join(dir, rel)}: ${e.code ?? e.message}`);
    }
  };
}

async function pool(items, fn) {
  const queue = [...items];
  const errors = [];
  const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
    while (queue.length) {
      try {
        await fn(queue.shift());
      } catch (e) {
        errors.push(e);
      }
    }
  });
  await Promise.all(workers);
  return errors;
}

function parseJson(buf, rel) {
  try {
    return JSON.parse(buf.toString("utf8"));
  } catch (e) {
    throw new FetchError(`invalid JSON in ${rel}: ${e.message}`);
  }
}

async function write(file, buf) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, buf);
}

// Safe relative path under data/: rejects absolute paths and traversal.
function safeRel(rel, what) {
  const norm = path.posix.normalize(String(rel));
  if (!rel || norm.startsWith("..") || norm.startsWith("/") || /^[a-z]+:/i.test(norm)) {
    throw new FetchError(`unsafe ${what}: ${JSON.stringify(rel)}`);
  }
  return norm;
}

/**
 * Fetch (or copy) the data into the site tree rooted at `root`.
 * `read(rel)` returns a Buffer for a path relative to the data/ prefix.
 * Resolves to a summary object; rejects with FetchError on any problem.
 */
export async function fetchData({ root, read, log = () => {} }) {
  const stage = await fs.mkdtemp(path.join(os.tmpdir(), "stem-data-"));
  try {
    const stagePath = (...p) => path.join(stage, ...p);
    const fail = (errors) => {
      throw new FetchError(errors.map((e) => e.message).join("\n"));
    };

    // 1. Root files.
    const rootFiles = [...SRC_ONLY, ...BOTH, ENVELOPE];
    const json = {};
    let errs = await pool(rootFiles, async (f) => {
      const buf = await read(f);
      json[f] = parseJson(buf, f);
      await write(stagePath("data", f), buf);
    });
    if (errs.length) fail(errs);

    // 2. Per-partner event files named by the envelope.
    const partners = json[ENVELOPE].partners;
    if (!Array.isArray(partners)) throw new FetchError(`${ENVELOPE}: "partners" is not an array`);
    const eventRels = new Set();
    for (const p of partners) {
      for (const k of ["events_url", "past_events_url"]) {
        if (p[k]) eventRels.add(safeRel(p[k], `${k} of partner ${p.id ?? p.slug}`));
      }
    }
    const imageNames = new Set();
    const addImage = (src) => {
      if (src) imageNames.add(path.posix.basename(String(src)));
    };
    for (const o of json["opportunities.json"]) addImage(o.image_src);
    errs = await pool([...eventRels], async (rel) => {
      const buf = await read(rel);
      const data = parseJson(buf, rel);
      for (const e of data.events ?? []) addImage(e.image_src);
      await write(stagePath("data", rel), buf);
    });
    if (errs.length) fail(errs);

    // 3. Referenced images; any miss is fatal.
    errs = await pool([...imageNames], async (name) => {
      const buf = await read(`images/opportunities/${name}`).catch((e) => {
        throw new FetchError(`referenced image missing: ${name} (${e.message})`);
      });
      await write(stagePath("images", name), buf);
    });
    if (errs.length) fail(errs);

    // 4. Install. Everything validated; now mirror into the site tree.
    const srcData = path.join(root, "src/data");
    const pubData = path.join(root, "public/data");
    const pubImg = path.join(root, "public/images/opportunities");
    await fs.mkdir(srcData, { recursive: true });
    await fs.mkdir(pubData, { recursive: true });
    const cp = (from, to) => fs.cp(from, to, { recursive: true });

    for (const f of SRC_ONLY) await cp(stagePath("data", f), path.join(srcData, f));
    for (const f of BOTH) {
      await cp(stagePath("data", f), path.join(srcData, f));
      await cp(stagePath("data", f), path.join(pubData, f));
    }
    await cp(stagePath("data", ENVELOPE), path.join(pubData, ENVELOPE));

    // Mirror (delete stale): partners dir and images dir are replaced wholesale.
    await fs.rm(path.join(pubData, "partners"), { recursive: true, force: true });
    await fs.mkdir(path.join(pubData, "partners"), { recursive: true });
    if (eventRels.size) await cp(stagePath("data", "partners"), path.join(pubData, "partners"));
    await fs.rm(pubImg, { recursive: true, force: true });
    await fs.mkdir(pubImg, { recursive: true });
    if (imageNames.size) await cp(stagePath("images"), pubImg);

    return {
      opportunities: json["opportunities.json"].length,
      partners: partners.length,
      eventFiles: eventRels.size,
      images: imageNames.size,
    };
  } finally {
    await fs.rm(stage, { recursive: true, force: true });
  }
}

/** True when the generated inputs already exist (used by --if-missing). */
export async function dataPresent(root) {
  const need = [
    "src/data/opportunities.json",
    "src/data/teams.json",
    "public/data/partners.json",
    "public/data/partners",
    "public/images/opportunities",
  ];
  for (const n of need) {
    try {
      await fs.access(path.join(root, n));
    } catch {
      return false;
    }
  }
  return true;
}

async function main(argv) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  let local = null;
  let ifMissing = false;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--local") {
      local = argv[++i];
      if (!local) throw new FetchError("--local needs a data directory");
    } else if (argv[i] === "--if-missing") ifMissing = true;
    else throw new FetchError(`unknown argument: ${argv[i]} (use --local <dir>, --if-missing)`);
  }
  if (ifMissing && (await dataPresent(root))) {
    console.log("fetch-data: site data present, skipping (--if-missing)");
    return;
  }
  let read;
  if (local) {
    const stat = await fs.stat(local).catch(() => null);
    if (!stat?.isDirectory()) throw new FetchError(`--local: not a directory: ${local}`);
    read = localSource(path.resolve(local));
  } else {
    read = httpSource(process.env.SITE_DATA_BASE_URL || DEFAULT_BASE_URL);
  }
  const s = await fetchData({ root, read });
  console.log(
    `fetched: ${s.opportunities} opportunities, ${s.partners} partners, ` +
      `${s.eventFiles} event files, ${s.images} images, 0 missing`,
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch((e) => {
    console.error(`error: ${e.message}`);
    process.exit(1);
  });
}
export { httpSource, localSource, FetchError };
