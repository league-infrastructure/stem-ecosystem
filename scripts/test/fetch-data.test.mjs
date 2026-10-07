import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fetchData, httpSource, localSource } from "../fetch-data.mjs";

const j = (o) => JSON.stringify(o);

function fixture({ missingImage = false } = {}) {
  const files = {
    "opportunities.json": j([{ id: 1, image_src: "aaa.jpg" }, { id: 2, image_src: "" }]),
    "scrape-meta.json": j({}),
    "ads.json": j([]),
    "yield-history.json": j([]),
    "teams.json": j([]),
    "places.json": j([]),
    "clubs.json": j([]),
    "partners.json": j({
      partners: [
        { id: 1, slug: "p1", events_url: "partners/p1/events.json", past_events_url: "partners/p1/past-events.json" },
      ],
    }),
    "partners/p1/events.json": j({ events: [{ image_src: "bbb.jpg" }] }),
    "partners/p1/past-events.json": j({ events: [] }),
    "images/opportunities/aaa.jpg": "A",
  };
  if (!missingImage) files["images/opportunities/bbb.jpg"] = "B";
  return files;
}

async function tmpRoot() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "site-root-"));
  await fs.mkdir(path.join(root, "src/data"), { recursive: true });
  await fs.writeFile(path.join(root, "src/data/partners.json"), "CURATED");
  // stale content that mirroring must remove
  await fs.mkdir(path.join(root, "public/data/partners/stale"), { recursive: true });
  await fs.mkdir(path.join(root, "public/images/opportunities"), { recursive: true });
  await fs.writeFile(path.join(root, "public/images/opportunities/old.jpg"), "x");
  return root;
}

const exists = (p) => fs.access(p).then(() => true, () => false);

async function serve(files, { status = {} } = {}) {
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.replace(/^\/data\//, ""));
    if (status[rel]) { res.statusCode = status[rel]; return res.end("no"); }
    if (rel in files) { res.statusCode = 200; return res.end(files[rel]); }
    res.statusCode = 404; res.end("nf");
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { server, url: `http://127.0.0.1:${server.address().port}/data/` };
}

test("http success: mapping, mirror-delete, curated partners.json untouched", async () => {
  const root = await tmpRoot();
  const { server, url } = await serve(fixture());
  try {
    const s = await fetchData({ root, read: httpSource(url) });
    assert.deepEqual(s, { opportunities: 2, partners: 1, eventFiles: 2, images: 2 });
    assert.ok(await exists(path.join(root, "src/data/opportunities.json")));
    assert.ok(await exists(path.join(root, "src/data/teams.json")));
    assert.ok(await exists(path.join(root, "public/data/teams.json")));
    assert.ok(!(await exists(path.join(root, "public/data/opportunities.json"))));
    assert.ok(await exists(path.join(root, "public/data/partners.json")));
    assert.ok(await exists(path.join(root, "public/data/partners/p1/events.json")));
    assert.ok(await exists(path.join(root, "public/images/opportunities/bbb.jpg")));
    assert.ok(!(await exists(path.join(root, "public/data/partners/stale"))));
    assert.ok(!(await exists(path.join(root, "public/images/opportunities/old.jpg"))));
    assert.equal(await fs.readFile(path.join(root, "src/data/partners.json"), "utf8"), "CURATED");
  } finally { server.close(); }
});

test("missing referenced image fails and leaves site untouched", async () => {
  const root = await tmpRoot();
  const { server, url } = await serve(fixture({ missingImage: true }));
  try {
    await assert.rejects(fetchData({ root, read: httpSource(url) }), /image missing: bbb\.jpg/);
    assert.ok(await exists(path.join(root, "public/images/opportunities/old.jpg")));
    assert.ok(!(await exists(path.join(root, "src/data/opportunities.json"))));
  } finally { server.close(); }
});

test("HTTP error on a data file fails", async () => {
  const root = await tmpRoot();
  const { server, url } = await serve(fixture(), { status: { "partners/p1/events.json": 403 } });
  try {
    await assert.rejects(fetchData({ root, read: httpSource(url) }), /HTTP 403/);
  } finally { server.close(); }
});

test("invalid JSON fails", async () => {
  const root = await tmpRoot();
  const files = fixture();
  files["places.json"] = "{nope";
  const { server, url } = await serve(files);
  try {
    await assert.rejects(fetchData({ root, read: httpSource(url) }), /invalid JSON in places\.json/);
  } finally { server.close(); }
});

test("--local copies from a directory with the same mapping and checks", async () => {
  const root = await tmpRoot();
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "local-data-"));
  for (const [rel, body] of Object.entries(fixture())) {
    await fs.mkdir(path.dirname(path.join(dir, rel)), { recursive: true });
    await fs.writeFile(path.join(dir, rel), body);
  }
  const s = await fetchData({ root, read: localSource(dir) });
  assert.equal(s.images, 2);
  assert.ok(await exists(path.join(root, "public/data/partners/p1/past-events.json")));
  assert.equal(await fs.readFile(path.join(root, "src/data/partners.json"), "utf8"), "CURATED");
  await fs.rm(path.join(dir, "images/opportunities/bbb.jpg"));
  await assert.rejects(fetchData({ root, read: localSource(dir) }), /image missing: bbb\.jpg/);
});
