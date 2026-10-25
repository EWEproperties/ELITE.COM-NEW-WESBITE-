"""Build a town page: "Property for sale in <town>" with listings, a short guide and FAQ.

Usage:
  python3 tools/towns/build_town.py alicante

Reads tools/towns/<town>.json (the written content) and tools/towns/data/<town>-listings.json
(the listings, for now read from the live site; later from the eGO generator), and writes
<page>.html in the site root. One page per town replaces the old pair of thin pages
(/<town> guide + /properties-for-sale-in-<town>), so they no longer compete in Google.
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SITE = "https://www.eliteworldestates.com"
e = html.escape


def local_pages():
    """EWE reference -> local property page, for listings that already have a new page."""
    out = {}
    folder = os.path.join(ROOT, "properties")
    for f in sorted(os.listdir(folder)):
        m = re.search(r"EWE\d{4}", open(os.path.join(folder, f), encoding="utf-8").read())
        if m:
            out.setdefault(m.group(0), "properties/" + f)
    return out


def price_value(p):
    digits = re.sub(r"\D", "", p)
    return int(digits) if digits else None


def fmt_price(p):
    v = price_value(p)
    return f"€{v:,}" if v else "Price on request"


def clean_title(t):
    t = re.sub(r"\bapartament\b", "apartment", t, flags=re.I)
    t = re.sub(r"\bappartment\b", "apartment", t, flags=re.I)
    t = re.sub(r"\bapartmens\b", "apartments", t, flags=re.I)
    return t.strip()


def facts(d):
    parts = []
    beds, baths, area = d.get("ROOMS"), d.get("BATHS"), d.get("AREA")
    if beds and beds != "0":
        parts.append(f"{beds} bedroom{'s' if beds != '1' else ''}")
    if baths and baths != "0":
        parts.append(f"{baths} bathroom{'s' if baths != '1' else ''}")
    if area:
        parts.append(f"{float(area):g} m²")
    return " · ".join(parts)


def card(i, pages):
    href = pages.get(i["ref"]) or f"{SITE}/property-details/{i['slug']}/{i['id']}"
    ext = "" if not href.startswith("http") else ' target="_blank" rel="noopener"'
    town = i["town"]
    return f"""        <a class="tcard" href="{href}"{ext}>
          <div class="tcard-photo"><img src="{i['photo']}" alt="{e(i['alt'] or clean_title(i['title']))}" width="800" height="600" loading="lazy" decoding="async"><span class="tcard-ref">{i['ref']}</span></div>
          <div class="tcard-body">
            <p class="tcard-town">{e(town)}</p>
            <h3>{e(clean_title(i['title']))}</h3>
            <p class="tcard-price">{fmt_price(i['price'])}</p>
            <p class="tcard-facts"><span>{facts(i['det'])}</span><span class="tcard-refno">Ref. {i['ref']}</span></p>
          </div>
        </a>"""


def main(slug):
    c = json.load(open(os.path.join(HERE, slug + ".json"), encoding="utf-8"))
    listings = json.load(open(os.path.join(HERE, "data", slug + "-listings.json"), encoding="utf-8"))
    pages = local_pages()
    missing = [i["id"] for i in listings if not re.fullmatch(r"EWE\d+", i.get("ref", ""))]
    if missing:  # every card must show its reference number
        sys.exit(f"Listings without an EWE reference: {missing}")
    town_names = c["town_names"]  # eGO municipality -> display name
    for i in listings:
        i["town"] = town_names.get(i["loc"][-1], i["loc"][-1])
        i["photo"] = f"assets/towns/{slug}/listings/{i['id']}.jpg"
    key = lambda i: (price_value(i["price"]) is None, price_value(i["price"]) or 0)
    city = sorted([i for i in listings if i["town"] == c["town"]], key=key)
    near = sorted([i for i in listings if i["town"] != c["town"]], key=key)
    prices = [price_value(i["price"]) for i in city if price_value(i["price"])]
    low = min(prices)
    url = f"{SITE}/{c['page']}"
    page_file = c["page"] + ".html"

    def fill(s):
        return (s.replace("{count}", str(len(city))).replace("{count_all}", str(len(listings)))
                 .replace("{from}", f"€{low:,}").replace("{near_count}", str(len(near))))

    # Schema: breadcrumb, the page with its listings, FAQ
    item_list = [{"@type": "ListItem", "position": n + 1,
                  "url": (SITE + "/" + pages[i["ref"]]) if i["ref"] in pages else f"{SITE}/property-details/{i['slug']}/{i['id']}",
                  "name": clean_title(i["title"])} for n, i in enumerate(city + near)]
    schema = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Costa Blanca", "item": SITE + "/costa-blanca"},
            {"@type": "ListItem", "position": 3, "name": c["town"], "item": url}]},
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": fill(c["h1"]), "url": url,
         "description": fill(c["description"]), "inLanguage": "en",
         "about": {"@type": "City", "name": c["town"], "containedInPlace": {"@type": "AdministrativeArea", "name": "Province of Alicante"}},
         "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", fill(a))}}
            for q, a in c["faq"]]},
    ]

    areas = "\n".join(f"""        <div class="t-area">
          <h3>{e(a['name'])}</h3>
          <p>{a['text']}</p>
        </div>""" for a in c["areas"])
    from PIL import Image
    gw, gh = Image.open(os.path.join(ROOT, "assets", "towns", slug, c["guide_photo"])).size
    guide = "\n".join(f"        <p>{fill(p)}</p>" for p in c["guide"])
    costs = "\n".join(f"          <tr><th scope=\"row\">{r[0]}</th><td>{r[1]}</td></tr>" for r in c["costs"])
    faq = "\n".join(f"""      <details>
        <summary>{e(q)}</summary>
        <p>{fill(a)}</p>
      </details>""" for q, a in c["faq"])
    reads = "\n".join(f"""      <a class="t-read" href="{r['href']}">
        <img src="{r['img']}" alt="" width="960" height="540" loading="lazy" decoding="async">
        <span class="tag">{r['tag']}</span>
        <h3>{e(r['title'])}</h3>
      </a>""" for r in c["reads"])
    facts_band = "\n".join(f'      <li><strong>{fill(v)}</strong><span>{fill(k)}</span></li>' for v, k in c["facts"])
    near_names = ", ".join(c.get("near_towns", []))
    near_block = f"""
  <section class="t-section t-near">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">A short drive away</p>
          <h2>Near {e(c['town'])}: {e(near_names)}</h2>
          <p class="lead">{fill(c.get('near_intro', ''))}</p>
        </div>
      </div>
      <div class="t-grid" data-limit="12">
{chr(10).join(card(i, pages) for i in near)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline t-more" hidden>Show all {len(near)} properties</button></div>
    </div>
  </section>
""" if near else ""

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(fill(c['title']))}</title>
  <meta name="description" content="{e(fill(c['description']))}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="en" href="{url}">
  <link rel="alternate" hreflang="x-default" href="{url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:locale" content="en_GB">
  <meta property="og:title" content="{e(fill(c['title']))}">
  <meta property="og:description" content="{e(fill(c['description']))}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}/assets/towns/{slug}/hero.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="assets/logo.png" type="image/png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,400&family=Prata&display=swap" rel="stylesheet">
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
      <a href="index.html#properties" class="active">Properties</a>
      <a href="blog.html">Blog</a>
      <a href="about-us.html">About Us</a>
      <a href="#contact">Contact Us</a>
      <div class="lang">
        <a href="{page_file}" class="active" hreflang="en">EN</a>
        <a href="https://eliteworldestates.pl" hreflang="pl">PL</a>
      </div>
    </nav>
  </div>
</header>

<main class="town-page">
  <section class="t-hero" style="background-image:url(assets/towns/{slug}/hero.jpg)">
    <div class="container">
      <nav class="t-crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> <span>/</span> <a href="https://www.eliteworldestates.com/costa-blanca">Costa Blanca</a> <span>/</span> {e(c['town'])}</nav>
      <p class="t-kicker">{e(c['kicker'])}</p>
      <h1>{e(fill(c['h1']))}</h1>
      <p class="t-lead">{fill(c['lead'])}</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="#listings">See the properties</a>
        <a class="btn t-btn-light" href="#contact">Ask us about {e(c['town'])}</a>
      </div>
    </div>
  </section>

  <ul class="t-facts container">
{facts_band}
  </ul>

  <section class="t-section" id="listings">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">For sale now</p>
          <h2>{e(c.get('listings_title', 'Properties for sale in ' + c['town']))}</h2>
          <p class="lead">{fill(c['listings_intro'])}</p>
        </div>
      </div>
      <div class="t-grid" data-limit="12">
{chr(10).join(card(i, pages) for i in city)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline t-more" hidden>Show all {len(city)} properties</button></div>
    </div>
  </section>
{near_block}
  <section class="t-section t-guide">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">The city</p>
        <h2>{e(c['guide_title'])}</h2>
{guide}
      </div>
      <img class="t-photo" src="assets/towns/{slug}/{c['guide_photo']}" alt="{e(c['guide_photo_alt'])}" width="{gw}" height="{gh}" loading="lazy" decoding="async">
    </div>
  </section>

  <section class="t-section">
    <div class="container">
      <p class="eyebrow dark">Where to buy</p>
      <h2>{e(c['areas_title'])}</h2>
      <div class="t-areas">
{areas}
      </div>
    </div>
  </section>

  <section class="t-section t-costs">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">Budget</p>
        <h2>What it costs to buy in {e(c['town'])}</h2>
        <p>{fill(c['costs_intro'])}</p>
        <p><a class="link-more" href="how-to-buy-an-apartment-or-house-in-spain.html">How to buy in Spain, step by step &rarr;</a></p>
      </div>
      <table class="cost-table t-table">
        <tbody>
{costs}
        </tbody>
      </table>
    </div>
  </section>

  <section class="t-section t-faq">
    <div class="container">
      <p class="eyebrow dark">Questions</p>
      <h2>Buying property in {e(c['town'])}: questions and answers</h2>
{faq}
    </div>
  </section>

  <section class="t-section">
    <div class="container">
      <p class="eyebrow dark">From our blog</p>
      <h2>Read before you buy</h2>
      <div class="t-reads">
{reads}
      </div>
    </div>
  </section>

  <section class="t-contact" id="contact">
    <div class="container">
      <h2>Looking for a home in {e(c['town'])}?</h2>
      <p>Tell us your budget and what you need. We reply within one working day, in English, German, Spanish or Polish.</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="mailto:info@eliteworldestates.com?subject={e(c['town'])}%20property">Email us</a>
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
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="js/main.js"></script>
<script>
// Show the first 12 cards; the rest stay in the HTML for search engines and open with the button
document.querySelectorAll(".t-grid[data-limit]").forEach(function (g) {{
  var n = +g.dataset.limit, cards = g.querySelectorAll(".tcard"), btn = g.parentNode.querySelector(".t-more");
  if (cards.length <= n) return;
  cards.forEach(function (c, k) {{ if (k >= n) c.hidden = true; }});
  btn.hidden = false;
  btn.addEventListener("click", function () {{ cards.forEach(function (c) {{ c.hidden = false; }}); btn.remove(); }});
}});
</script>
</body>
</html>
"""
    open(os.path.join(ROOT, page_file), "w", encoding="utf-8").write(out)
    print(f"{page_file}: {len(city)} in {c['town']}, {len(near)} nearby, from €{low:,}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "alicante")
