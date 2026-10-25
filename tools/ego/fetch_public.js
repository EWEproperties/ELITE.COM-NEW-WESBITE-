// Testing only, until the eGO API key arrives: opens listing pages on the live
// eliteworldestates.com in a headless browser, the way a visitor would, and saves the
// listing data the page receives from eGO into tools/ego/cache/<id>.json.
// Usage: node tools/ego/fetch_public.js <id> [<id> ...]
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const CACHE = path.join(__dirname, "cache");
const LIVE = "https://www.eliteworldestates.com";

(async () => {
  const ids = process.argv.slice(2);
  fs.mkdirSync(CACHE, { recursive: true });
  // The live sitemap gives each listing's page address
  const xml = await (await fetch(`${LIVE}/sitemap-en-gb.xml`)).text();
  const urls = {};
  for (const m of xml.matchAll(/<loc>([^<]*\/property-details\/[^<]*\/(\d+))<\/loc>/g)) urls[m[2]] = m[1];

  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const id of ids) {
    if (!urls[id]) { console.log("not on the live site:", id); continue; }
    const resp = page.waitForResponse((r) => r.url().includes(`/v1/Properties/${id}?`) && r.status() === 200, { timeout: 60000 });
    await page.goto(urls[id], { waitUntil: "domcontentloaded", timeout: 60000 });
    const data = await (await resp).json();
    fs.writeFileSync(path.join(CACHE, `${id}.json`), JSON.stringify(data, null, 1));
    console.log("fetched", id);
  }
  await browser.close();
})();
