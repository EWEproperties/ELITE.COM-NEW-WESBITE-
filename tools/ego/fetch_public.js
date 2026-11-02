// Reads the full photo gallery (and website fields) of listings from the live
// eliteworldestates.com in a headless browser, the way a visitor would, and saves the
// listing data the page receives from eGO into tools/ego/cache/<id>.json.
// The eGO Global API (fetch_ego.py) only gives the main photo, so run this first;
// fetch_ego.py then updates texts, prices and features and keeps these photos.
// Only works while the old site is online.
// Usage: node tools/ego/fetch_public.js <id> [<id> ...]   (website ids)
//        node tools/ego/fetch_public.js --all [--missing]  (every listing in the live sitemap)
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const CACHE = path.join(__dirname, "cache");
const LIVE = "https://www.eliteworldestates.com";
const WORKERS = 4;

(async () => {
  const args = process.argv.slice(2);
  fs.mkdirSync(CACHE, { recursive: true });
  // The live sitemap gives each listing's page address
  const xml = await (await fetch(`${LIVE}/sitemap-en-gb.xml`)).text();
  const urls = {};
  for (const m of xml.matchAll(/<loc>([^<]*\/property-details\/[^<]*\/(\d+))<\/loc>/g)) urls[m[2]] = m[1];

  let ids = args.includes("--all") ? Object.keys(urls) : args.filter((a) => !a.startsWith("--"));
  if (args.includes("--missing")) {
    ids = ids.filter((id) => {
      const f = path.join(CACHE, `${id}.json`);
      return !fs.existsSync(f) || !(JSON.parse(fs.readFileSync(f, "utf8")).Images || []).length
        || JSON.parse(fs.readFileSync(f, "utf8"))._source === "egocrm";
    });
  }
  console.log(`${ids.length} listings to read`);

  const browser = await chromium.launch();
  let done = 0;
  const queue = [...ids];
  async function worker() {
    const page = await browser.newPage();
    for (let id; (id = queue.shift()); ) {
      if (!urls[id]) { console.log("not on the live site:", id); continue; }
      try {
        const resp = page.waitForResponse((r) => r.url().includes(`/v1/Properties/${id}?`) && r.status() === 200, { timeout: 60000 });
        await page.goto(urls[id], { waitUntil: "domcontentloaded", timeout: 60000 });
        const data = await (await resp).json();
        fs.writeFileSync(path.join(CACHE, `${id}.json`), JSON.stringify(data, null, 1));
        done++;
        if (done % 25 === 0) console.log(`fetched ${done} of ${ids.length}`);
      } catch (e) {
        console.log("failed", id, e.message.split("\n")[0]);
      }
    }
    await page.close();
  }
  await Promise.all(Array.from({ length: WORKERS }, worker));
  console.log(`fetched ${done} of ${ids.length}`);
  await browser.close();
})();
