// node scrape_list.js <start url> <out.json> : every listing on every page of an eGO list/search page
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [start, out] = process.argv.slice(2);
  const b = await chromium.launch();
  const todo = [start], done = new Set(), items = {};
  while (todo.length) {
    const u = todo.shift(); if (done.has(u)) continue; done.add(u);
    const p = await b.newPage();
    await p.goto(u, { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(800);
    const r = await p.evaluate(() => {
      const res = [];
      document.querySelectorAll('.propertyReference').forEach(ref => {
        let c = ref; for (let k = 0; k < 8 && !(c.querySelector('a[href*="/property-details/"]') && c.querySelector('img.propertyImage')); k++) c = c.parentElement;
        const a = c.querySelector('a[href*="/property-details/"]'), img = c.querySelector('img.propertyImage');
        const q = s => (c.querySelector(s) || {}).textContent || '';
        const det = {}; c.querySelectorAll('.detailItem').forEach(d => { const k = [...d.classList].find(x => x !== 'detailItem'); det[k] = d.textContent.replace(/\s+/g, ' ').trim(); });
        res.push({ href: a && a.getAttribute('href'), img: img && img.getAttribute('src'), alt: img && img.alt,
          ref: ref.textContent.replace('Ref:', '').trim(), title: q('.propertyTitle').trim(), price: q('.propertyPrice').replace(/\s+/g, ' ').trim(),
          loc: [...c.querySelectorAll('[class^="loc-level"]')].map(x => x.textContent.trim()).filter(Boolean), det });
      });
      const pages = [...document.querySelectorAll('a[href*="pag="]')].map(a => a.href);
      return { res, pages };
    });
    for (const i of r.res) if (i.href && !items[i.ref]) items[i.ref] = i;
    for (const pg of r.pages) if (!done.has(pg) && !todo.includes(pg)) todo.push(pg);
    await p.close();
  }
  const list = Object.values(items).map(i => { const m = i.href.match(/property-details\/([^/]+)\/(\d+)/); return { ...i, slug: m[1], id: m[2] }; });
  fs.writeFileSync(out, JSON.stringify(list, null, 1));
  console.log(list.length, 'listings from', done.size, 'pages');
  await b.close();
})();
