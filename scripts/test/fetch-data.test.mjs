import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fetchData, httpSource, localSource, dataPresent } from "../fetch-data.mjs";

const j = (o) => JSON.stringify(o);

function fixture({ missingImage = false, missingLogo = false } = {}) {
  const files = {
    "opportunities.json": j([
      { id: 1, image_src: "aaa.jpg", logo_src: "partners/p1/logo.PNG" },
      { id: 2, image_src: "", logo_src: "legacy.png" },
    ]),
    "scrape-meta.json": j({}),
    "ads.json": j([{ headline: "h", logo_src: "partners/p1/logo.PNG" }]),
    "yield-history.json": j([]),
    "teams.json": j([]),
    "places.json": j([]),
    "clubs.json": j([]),
    "partners.json": j({
      partners: [
        { id: 1, slug: "p1", name: "P1", logo_src: "partners/p1/logo.PNG", events_url: "partners/p1/events.json", past_events_url: "partners/p1/past-events.json" },
        { id: 2, slug: "p2", name: "P2", logo_src: "", events_url: "partners/p2/events.json", past_events_url: "partners/p2/past-events.json" },
      ],
    }),
    "partners/p1/events.json": j({ events: [{ image_src: "bbb.jpg" }] }),
    "partners/p1/past-events.json": j({ events: [] }),
    "partners/p2/events.json": j({ events: [] }),
    "partners/p2/past-events.json": j({ events: [] }),
    "partners/p1/logo.PNG": "LOGO1",
    "images/opportunities/aaa.jpg": "A",
  };
  if (missingLogo) delete files["partners/p1/logo.PNG"];
  if (!missingImage) files["images/opportunities/bbb.jpg"] = "B";
  return files;
}

async function tmpRoot() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "site-root-"));
  await fs.mkdir(path.join(root, "src/data"), { recursive: true });
  await fs.writeFile(path.join(root, "src/data/partners.json"), "PREVIOUS");
  await fs.mkdir(path.join(root, "public/images/logos"), { recursive: true });
  await fs.writeFile(path.join(root, "public/images/logos/default-partner.svg"), "FALLBACK");
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

test("http success: mapping, mirror-delete, roster and logos", async () => {
  const root = await tmpRoot();
  const { server, url } = await serve(fixture());
  try {
    const s = await fetchData({ root, read: httpSource(url) });
    assert.deepEqual(s, { opportunities: 2, partners: 2, eventFiles: 4, images: 2, logos: 1 });
    assert.ok(await exists(path.join(root, "src/data/opportunities.json")));
    assert.ok(await exists(path.join(root, "src/data/teams.json")));
    assert.ok(await exists(path.join(root, "public/data/teams.json")));
    assert.ok(!(await exists(path.join(root, "public/data/opportunities.json"))));
    assert.ok(await exists(path.join(root, "public/data/partners.json")));
    assert.ok(await exists(path.join(root, "public/data/partners/p1/events.json")));
    assert.ok(await exists(path.join(root, "public/images/opportunities/bbb.jpg")));
    assert.ok(!(await exists(path.join(root, "public/data/partners/stale"))));
    assert.ok(!(await exists(path.join(root, "public/images/opportunities/old.jpg"))));
    const roster = JSON.parse(await fs.readFile(path.join(root, "src/data/partners.json"), "utf8"));
    assert.deepEqual(roster, [
      { id: 1, slug: "p1", name: "P1", logo_src: "p1.png" },
      { id: 2, slug: "p2", name: "P2", logo_src: "" },
    ]);
    assert.equal(await fs.readFile(path.join(root, "public/images/logos/p1.png"), "utf8"), "LOGO1");
    assert.equal(await fs.readFile(path.join(root, "public/images/logos/default-partner.svg"), "utf8"), "FALLBACK");
    const opps = JSON.parse(await fs.readFile(path.join(root, "src/data/opportunities.json"), "utf8"));
    assert.deepEqual(opps.map((o) => o.logo_src), ["p1.png", "legacy.png"]);
    const ads = JSON.parse(await fs.readFile(path.join(root, "src/data/ads.json"), "utf8"));
    assert.equal(ads[0].logo_src, "p1.png");
    // the public envelope keeps its bucket-form paths
    const env = JSON.parse(await fs.readFile(path.join(root, "public/data/partners.json"), "utf8"));
    assert.equal(env.partners[0].logo_src, "partners/p1/logo.PNG");
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
  assert.equal(s.logos, 1);
  assert.ok(await exists(path.join(root, "public/data/partners/p1/past-events.json")));
  assert.ok(await exists(path.join(root, "public/images/logos/p1.png")));
  await fs.rm(path.join(dir, "images/opportunities/bbb.jpg"));
  await assert.rejects(fetchData({ root, read: localSource(dir) }), /image missing: bbb\.jpg/);
});

test("missing partner logo fails and leaves roster and logos untouched", async () => {
  const root = await tmpRoot();
  const { server, url } = await serve(fixture({ missingLogo: true }));
  try {
    await assert.rejects(fetchData({ root, read: httpSource(url) }), /partner logo missing: partners\/p1\/logo\.PNG/);
    assert.equal(await fs.readFile(path.join(root, "src/data/partners.json"), "utf8"), "PREVIOUS");
    assert.ok(!(await exists(path.join(root, "public/images/logos/p1.png"))));
    assert.ok(!(await exists(path.join(root, "src/data/opportunities.json"))));
  } finally { server.close(); }
});

test("non-bucket logo_src in the roster is rejected", async () => {
  const root = await tmpRoot();
  const files = fixture();
  files["partners.json"] = j({ partners: [{ id: 1, slug: "p1", logo_src: "old.png" }] });
  const { server, url } = await serve(files);
  try {
    await assert.rejects(fetchData({ root, read: httpSource(url) }), /logo_src "old\.png" is not partners/);
  } finally { server.close(); }
});

test("--if-missing: dataPresent needs the fetched roster", async () => {
  const root = await tmpRoot();
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "local-data-"));
  for (const [rel, body] of Object.entries(fixture())) {
    await fs.mkdir(path.dirname(path.join(dir, rel)), { recursive: true });
    await fs.writeFile(path.join(dir, rel), body);
  }
  assert.equal(await dataPresent(root), false);
  await fetchData({ root, read: localSource(dir) });
  assert.equal(await dataPresent(root), true);
  await fs.rm(path.join(root, "src/data/partners.json"));
  assert.equal(await dataPresent(root), false);
});
