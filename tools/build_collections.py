"""Build the property collection pages: the all-properties search, the coast hubs and the
category pages (luxury villas, sea views, featured...).

Content: tools/collections/pages.json (one entry per page, keyed by the page address).
Listings: feeds/properties.json, written by tools/ego/build_properties.py, so run that first.
Each page holds every matching card in the HTML (for Google), with a small filter bar
(area, type, bedrooms, budget, sort) that works in the browser.

Usage:
  python3 tools/build_collections.py            # every page
  python3 tools/build_collections.py featured-properties
Then run tools/link_properties.py.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "ego"))
from build_properties import ego_photo, place, replace_block, short_town  # noqa: E402
import datetime

SITE = "https://www.eliteworldestates.com"
e = lambda s: html.escape(str(s), quote=True)
PAGES = json.load(open(os.path.join(ROOT, "tools", "collections", "pages.json"), encoding="utf-8"))

COSTS = {
    "Valencian Community": [("New build", "10% VAT (IVA) + 1.4% stamp duty (AJD)"),
                            ("Resale home", "9% transfer tax (ITP), 11% above €1 million")],
    "Andalusia": [("New build", "10% VAT (IVA) + 1.2% stamp duty (AJD)"), ("Resale home", "7% transfer tax (ITP)")],
    "Region of Murcia": [("New build", "10% VAT (IVA) + 1.5% stamp duty (AJD)"), ("Resale home", "7.75% transfer tax (ITP)")],
}
COMMON_COSTS = [("Notary, registry, lawyer", "about 1.5–2.5% of the price"),
                ("Every year", "IBI property tax and community fees, which depend on the home")]
TYPE_GROUP = {"Apartment": "Apartment", "Ground floor": "Apartment", "Duplex": "Apartment", "Penthouse": "Penthouse",
              "Villa": "Villa", "Chalet": "Villa", "House": "Villa", "Semi-Detached": "Townhouse",
              "Semi-Detached House": "Townhouse", "Town House": "Townhouse", "Duplex House": "Townhouse"}
SEA = re.compile(r"sea[ -]?views?|views? (of|over|to) the sea|panoramic|frontline|front line|first line", re.I)


def page_title(slug):
    """Title of another page on the site, for the 'more' links."""
    if slug in PAGES:
        return PAGES[slug]["h1"]
    t = open(os.path.join(ROOT, slug + ".html"), encoding="utf-8").read()
    h = re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", h.group(1))).strip()


def featured_refs():
    t = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    block = re.search(r'<section class="featured".*?</section>', t, re.S).group(0)
    return list(dict.fromkeys(re.findall(r'class="badge">(EWE\d+)<', block)))


def load():
    props = json.load(open(os.path.join(ROOT, "feeds", "properties.json"), encoding="utf-8"))["properties"]
    for p in props:
        p["place"] = place({"title": p["title"], "area": p.get("area") or "", "town": p["town"]})
        p["group"] = TYPE_GROUP.get(p["type"], "Villa")
        p["sea"] = "Sea" in (p.get("views") or []) or bool(SEA.search(p["title"]))
        p["href"] = p["url"].replace(SITE + "/", "")
    return props


def matches(p, f, feat):
    if f.get("coast") and p["coast"] not in f["coast"]:
        return False
    if f.get("types") and p["type"] not in f["types"]:
        return False
    if f.get("min_price") and (p["price"] or 0) < f["min_price"]:
        return False
    if f.get("sea_view") and not p["sea"]:
        return False
    if f.get("featured") and p["reference"] not in feat:
        return False
    return True


def euro(v):
    return f"€{int(v):,}"


def card(p):
    facts = []
    if p["bedrooms"]:
        facts.append(f"{p['bedrooms']} bedroom{'s' if p['bedrooms'] != 1 else ''}")
    if p["bathrooms"]:
        facts.append(f"{p['bathrooms']} bathroom{'s' if p['bathrooms'] != 1 else ''}")
    if p["built_m2"]:
        facts.append(f"{p['built_m2']:g} m²")
    price = (("From " if p["price_from"] else "") + euro(p["price"])) if p["price"] else "Price on request"
    img = ego_photo(p["photos"][0], "Z800x600") if p["photos"] else ""
    return f"""        <a class="tcard" href="{p['href']}" data-coast="{e(p['coast'])}" data-town="{e(p['place'])}" data-type="{p['group']}" data-beds="{p['bedrooms'] or 0}" data-price="{int(p['price'] or 0)}" data-new="{p['created']}">
          <div class="tcard-photo"><img src="{img}" alt="{e(p['title'])}" width="800" height="600" loading="lazy" decoding="async"><span class="tcard-ref">{p['reference']}</span></div>
          <div class="tcard-body">
            <p class="tcard-town">{e(p['place'])}</p>
            <h3>{e(p['title'])}</h3>
            <p class="tcard-price">{price}</p>
            <p class="tcard-facts"><span>{' · '.join(facts)}</span><span class="tcard-refno">Ref. {p['reference']}</span></p>
          </div>
        </a>"""


def options(values, label):
    return f'<option value="">{label}</option>' + "".join(f'<option value="{e(v)}">{e(v)}</option>' for v in values)


def filter_bar(items):
    coasts = sorted({p["coast"] for p in items})
    towns = sorted({p["place"] for p in items})
    types = [t for t in ("Apartment", "Penthouse", "Townhouse", "Villa") if any(p["group"] == t for p in items)]
    coast_sel = (f'<label><span>Coast</span><select id="f-coast">{options(coasts, "All coasts")}</select></label>'
                 if len(coasts) > 1 else "")
    budgets = [b for b in (200000, 300000, 400000, 500000, 750000, 1000000, 2000000, 3000000)
               if any((p["price"] or 0) <= b for p in items)]
    return f"""      <form class="c-filter" id="filter" aria-label="Filter the properties">
        {coast_sel}
        <label><span>Town</span><select id="f-town">{options(towns, "All towns")}</select></label>
        <label><span>Type</span><select id="f-type">{options(types, "All types")}</select></label>
        <label><span>Bedrooms</span><select id="f-beds"><option value="">Any</option><option value="1">1+</option><option value="2">2+</option><option value="3">3+</option><option value="4">4+</option></select></label>
        <label><span>Budget up to</span><select id="f-price"><option value="">Any price</option>{''.join(f'<option value="{b}">{euro(b)}</option>' for b in budgets)}</select></label>
        <label><span>Sort</span><select id="f-sort"><option value="price-asc">Price, low to high</option><option value="price-desc">Price, high to low</option><option value="new">Newest first</option></select></label>
      </form>
      <p class="c-count" id="count" aria-live="polite">{len(items)} properties</p>"""


SCRIPT = """<script>
// Filter and sort the cards. Every card is in the HTML, so search engines see them all.
(function () {
  var grid = document.getElementById("cards"), cards = Array.prototype.slice.call(grid.children);
  var more = document.getElementById("more"), count = document.getElementById("count");
  var step = 24, shown = step;
  function val(id) { var el = document.getElementById(id); return el ? el.value : ""; }
  function apply(reset) {
    if (reset) shown = step;
    var coast = val("f-coast"), town = val("f-town"), type = val("f-type"), beds = +val("f-beds") || 0, max = +val("f-price") || 0, sort = val("f-sort");
    var list = cards.filter(function (c) {
      var d = c.dataset, p = +d.price;
      return (!coast || d.coast === coast) && (!town || d.town === town) && (!type || d.type === type) &&
             (+d.beds >= beds) && (!max || (p && p <= max));
    });
    list.sort(function (a, b) {
      var pa = +a.dataset.price || 1e12, pb = +b.dataset.price || 1e12;
      if (sort === "price-desc") return (+b.dataset.price) - (+a.dataset.price);
      if (sort === "new") return a.dataset.new < b.dataset.new ? 1 : -1;
      return pa - pb;
    });
    cards.forEach(function (c) { c.hidden = true; });
    list.forEach(function (c, i) { grid.appendChild(c); c.hidden = i >= shown; });
    count.textContent = list.length === 1 ? "1 property" : list.length + " properties";
    more.hidden = list.length <= shown;
    more.textContent = "Show more (" + (list.length - shown) + " more)";
  }
  // Choices sent from the home page search: ?type=Villa&coast=Costa+Blanca&max=500000
  var q = new URLSearchParams(location.search);
  [["type", "f-type"], ["coast", "f-coast"], ["max", "f-price"], ["town", "f-town"]].forEach(function (k) {
    var el = document.getElementById(k[1]), v = q.get(k[0]);
    if (el && v && Array.prototype.some.call(el.options, function (o) { return o.value === v; })) el.value = v;
  });
  // Town list shows only the towns on the chosen coast
  function towns() {
    var el = document.getElementById("f-town"), coast = val("f-coast");
    if (!el || !document.getElementById("f-coast")) return;
    var have = {};
    cards.forEach(function (c) { if (!coast || c.dataset.coast === coast) have[c.dataset.town] = 1; });
    Array.prototype.forEach.call(el.options, function (o) {
      var ok = !o.value || have[o.value];
      o.hidden = !ok; o.disabled = !ok;
    });
    if (el.value && !have[el.value]) el.value = "";
  }
  towns();
  document.getElementById("filter").addEventListener("change", function (ev) {
    if (ev.target.id === "f-coast") towns();
    apply(true);
  });
  more.addEventListener("click", function () { shown += step; apply(false); });
  apply(true);
})();
</script>"""


def town_cards(coast):
    out = []
    for f in sorted(os.listdir(os.path.join(ROOT, "tools", "towns"))):
        if not f.endswith(".json"):
            continue
        c = json.load(open(os.path.join(ROOT, "tools", "towns", f), encoding="utf-8"))
        if c.get("coast", "Costa Blanca") != coast:
            continue
        slug = f[:-5]
        data = json.load(open(os.path.join(ROOT, "tools", "towns", "data", slug + "-listings.json"), encoding="utf-8"))
        prices = [int(re.sub(r"\D", "", i["price"])) for i in data if re.sub(r"\D", "", i["price"])]
        out.append((c["town"], c["page"], len(data), min(prices) if prices else 0, slug))
    return "\n".join(f"""        <a class="c-town" href="{page}.html">
          <img src="assets/towns/{slug}/hero.jpg" alt="{e(town)}" width="1200" height="800" loading="lazy" decoding="async">
          <span class="c-town-name">{e(town)}</span>
          <span class="c-town-meta">{n} properties · from {euro(low)}</span>
        </a>""" for town, page, n, low, slug in sorted(out, key=lambda x: -x[2]))


def build(slug, props, feat):
    c = PAGES[slug]
    items = [p for p in props if matches(p, c["filter"], feat)]
    if c["filter"].get("featured"):
        items.sort(key=lambda p: feat.index(p["reference"]))
    if not items:
        print("no listings, skipped", slug)
        return
    low = min(p["price"] for p in items if p["price"])
    fill = lambda s: s.replace("{count}", str(len(items))).replace("{from}", euro(low))
    url = f"{SITE}/{slug}"
    title, desc = fill(c["title"]), fill(c["description"])
    crumbs = [("Home", SITE + "/")]
    if c["kind"] != "search":
        crumbs.append(("All properties", SITE + "/properties-for-sale-in-spain"))
    crumbs.append((c["h1"], url))

    faq = c.get("faq", [])
    schema = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "name": name, "item": link} for n, (name, link) in enumerate(crumbs)]},
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": c["h1"], "url": url, "description": desc,
         "inLanguage": "en", "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
             {"@type": "ListItem", "position": n + 1, "url": p["url"], "name": p["title"]} for n, p in enumerate(items)]}},
    ]
    if faq:
        schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", fill(a))}}
            for q, a in faq]})

    crumb_html = " <span>/</span> ".join(f'<a href="{"index.html" if n == 0 else link.replace(SITE + "/", "") + ".html"}">{e(name)}</a>'
                                          for n, (name, link) in enumerate(crumbs[:-1])) + f" <span>/</span> {e(c['h1'])}"
    towns = {p["place"] for p in items}
    facts = [(str(len(items)), "properties for sale"), (euro(low), "lowest price"),
             (str(len(towns)), "towns" if len(towns) != 1 else "town"),
             (str(sum(1 for p in items if p["condition"] == "new build")), "new builds")]
    facts_html = "\n".join(f"      <li><strong>{v}</strong><span>{k}</span></li>" for v, k in facts)

    sections = ""
    if c.get("intro"):
        sections += f"""
  <section class="t-section c-intro">
    <div class="container t-narrow">
      <p class="eyebrow dark">{e(c['kicker'])}</p>
      <h2>{e(c['intro_title'])}</h2>
      <p>{fill(c['intro'])}</p>
    </div>
  </section>
"""
    if c["kind"] == "hub":
        sections += f"""
  <section class="t-section">
    <div class="container">
      <p class="eyebrow dark">Town guides</p>
      <h2>Towns on the {e(c['coast'])}</h2>
      <p class="lead">Each town page has its own homes for sale, a short guide to the areas and what buying really costs there.</p>
      <div class="c-towns">
{town_cards(c['coast'])}
      </div>
    </div>
  </section>

  <section class="t-section t-guide">
    <div class="container t-narrow">
      <p class="eyebrow dark">The coast</p>
      <h2>{e(c['guide_title'])}</h2>
{chr(10).join(f"      <p>{fill(x)}</p>" for x in c['guide'])}
    </div>
  </section>

  <section class="t-section t-costs">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">Budget</p>
        <h2>What it costs to buy on the {e(c['coast'])}</h2>
        <p>On top of the price you pay tax and fees. The taxes are set by the region, here the {e(c['region'])}. Always ask us for the exact figure for the home you like.</p>
        <p><a class="link-more" href="how-to-buy-an-apartment-or-house-in-spain.html">How to buy in Spain, step by step &rarr;</a></p>
      </div>
      <table class="cost-table t-table">
        <tbody>
{chr(10).join(f'          <tr><th scope="row">{k}</th><td>{v}</td></tr>' for k, v in COSTS[c['region']] + COMMON_COSTS)}
        </tbody>
      </table>
    </div>
  </section>
"""
    if faq:
        sections += f"""
  <section class="t-section t-faq">
    <div class="container">
      <p class="eyebrow dark">Questions</p>
      <h2>Questions and answers</h2>
{chr(10).join(f'''      <details>
        <summary>{e(q)}</summary>
        <p>{fill(a)}</p>
      </details>''' for q, a in faq)}
    </div>
  </section>
"""
    links = "\n".join(f'        <a class="c-link" href="{l}.html">{e(page_title(l))} <span aria-hidden="true">&rarr;</span></a>'
                      for l in c.get("links", []))
    if links:
        sections += f"""
  <section class="t-section c-more">
    <div class="container">
      <p class="eyebrow dark">Keep looking</p>
      <h2>More homes and guides</h2>
      <div class="c-links">
{links}
      </div>
    </div>
  </section>
"""

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="en" href="{url}">
  <link rel="alternate" hreflang="x-default" href="{url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:locale" content="en_GB">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}/{c['hero']}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="assets/logo.png" type="image/png">
  <link rel="stylesheet" href="css/style.css">
  <script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=1)}
  </script>
</head>
<body>

<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="index.html" aria-label="Elite World Estates – Home">
      <img src="assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="Main">
      <a href="index.html">Home</a>
      <a href="properties-for-sale-in-spain.html" class="active">Properties</a>
      <a href="blog.html">Blog</a>
      <a href="about-us.html">About Us</a>
      <a href="contact-us.html">Contact Us</a>
      <div class="lang">
        <a href="{slug}.html" class="active" hreflang="en">EN</a>
        <a href="https://eliteworldestates.pl" hreflang="pl">PL</a>
      </div>
    </nav>
  </div>
</header>

<main class="town-page collection-page">
  <section class="t-hero c-hero" style="background-image:url({c['hero']})">
    <div class="container">
      <nav class="t-crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
      <p class="t-kicker">{e(c['kicker'])}</p>
      <h1>{e(c['h1'])}</h1>
      <p class="t-lead">{fill(c['lead'])}</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="#listings">See the properties</a>
        <a class="btn t-btn-light" href="contact-us.html">Ask us</a>
      </div>
    </div>
  </section>

  <ul class="t-facts container">
{facts_html}
  </ul>

  <section class="t-section" id="listings">
    <div class="container">
{filter_bar(items)}
      <div class="t-grid" id="cards">
{chr(10).join(card(p) for p in items)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline" id="more" hidden>Show more</button></div>
    </div>
  </section>
{sections}
  <section class="t-contact" id="contact">
    <div class="container">
      <h2>Not sure which home fits?</h2>
      <p>Tell us your budget and what you need. We reply within one working day, in English, German, Spanish or Polish.</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="contact-us.html">Contact us</a>
        <a class="btn t-btn-outline" href="tel:+34672519809">Call 0034 672 519 809</a>
        <a class="btn t-btn-outline" href="https://wa.me/34672519809" target="_blank" rel="noopener">WhatsApp</a>
      </div>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="index.html">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>Registered in the Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) no. 2321.</p>
    <p class="footer-legal"><a href="terms-and-conditions.html">Legal notice</a> · <a href="privacy-policy.html">Privacy policy</a> · <a href="cookie-policy.html">Cookie policy</a></p>
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="js/main.js"></script>
{SCRIPT}
</body>
</html>
"""
    open(os.path.join(ROOT, slug + ".html"), "w", encoding="utf-8").write(out)
    print(f"{slug}.html: {len(items)} properties from {euro(low)}")


def update_index():
    """sitemap.xml and llms.txt: the collection pages and the contact page."""
    today = datetime.date.today().isoformat()
    slugs = list(PAGES) + ["contact-us"]
    sm = "".join(f"  <url>\n    <loc>{SITE}/{s}</loc>\n    <lastmod>{today}</lastmod>\n  </url>\n" for s in slugs)
    replace_block(os.path.join(ROOT, "sitemap.xml"), "  <!-- collections -->", "  <!-- /collections -->", sm, "  <!-- towns -->")
    txt = "## Property search, coasts and categories\n" + "".join(
        f"- [{PAGES[s]['h1'] if s in PAGES else 'Contact us'}]({SITE}/{s}): "
        f"{(PAGES[s]['lead'] if s in PAGES else 'Phone, WhatsApp, email and the team.')}\n" for s in slugs) + "\n"
    replace_block(os.path.join(ROOT, "llms.txt"), "<!-- collections -->", "<!-- /collections -->", txt, "<!-- properties -->")


def main(args):
    props, feat = load(), featured_refs()
    for slug in args or PAGES:
        build(slug, props, feat)
    update_index()


if __name__ == "__main__":
    main(sys.argv[1:])
