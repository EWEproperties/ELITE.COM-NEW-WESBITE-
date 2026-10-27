"""Build the golf pages: the Spain overview, one page per coast and one page per golf course.

Usage:
  python3 tools/golf/build_golf.py

Reads tools/golf/golf.json (the written content) and tools/golf/data/<page>-listings.json
(written by prepare_golf.py), and writes the pages to the site root at the live URLs:
  golf-properties-for-sale-in-spain.html            Spain: links to both coasts
  golf-properties-for-sale-in-costa-blanca.html     Costa Blanca: one card per golf course
  golf-properties-for-sale-in-costa-del-sol.html    Costa del Sol: the listings and the golf areas
  golf-properties-for-sale-in-costa-calida.html     Costa Cálida: one section per golf course with the nearest listings
  properties-for-sale-<course>-golf.html            one page per Costa Blanca golf course
The page layout and listing cards are the same as the town pages (tools/towns/build_town.py).
"""
import html
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "towns"))
from build_town import SITE, card, clean_title, local_pages, price_value  # noqa: E402

e = html.escape
SPAIN, CB, CDS = "golf-properties-for-sale-in-spain", "golf-properties-for-sale-in-costa-blanca", "golf-properties-for-sale-in-costa-del-sol"
CC = "golf-properties-for-sale-in-costa-calida"
# eGO municipality -> the name buyers know
TOWN_NAMES = {"Orihuela": "Orihuela Costa", "Rojales": "Ciudad Quesada"}


def listings(page, pages):
    items = json.load(open(os.path.join(HERE, "data", page + "-listings.json"), encoding="utf-8"))
    for i in items:
        i["town"] = TOWN_NAMES.get(i["loc"][-1], i["loc"][-1])
    key = lambda i: (price_value(i["price"]) is None, price_value(i["price"]) or 0)
    own = sorted([i for i in items if not i["near"]], key=key)
    near = sorted([i for i in items if i["near"]], key=key)
    return own, near


def low_price(items):
    return min(price_value(i["price"]) for i in items if price_value(i["price"]))


def url_of(i, pages):
    return (SITE + "/" + pages[i["ref"]]) if i["ref"] in pages else f"{SITE}/property-details/{i['slug']}/{i['id']}"


def size(rel):
    return Image.open(os.path.join(ROOT, rel)).size


def grid(items, pages, title, intro, eyebrow="For sale now", anchor="listings"):
    if not items:
        return ""
    return f"""
  <section class="t-section" id="{anchor}">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">{eyebrow}</p>
          <h2>{e(title)}</h2>
          <p class="lead">{intro}</p>
        </div>
      </div>
      <div class="t-grid" data-limit="12">
{chr(10).join(card(i, pages) for i in items)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline t-more" hidden>Show all {len(items)} properties</button></div>
    </div>
  </section>
"""


def tiles(cards):
    """Photo cards linking to another page (golf courses, coasts, blog articles)."""
    out = []
    for c in cards:
        line = f"\n        <p>{e(c['line'])}</p>" if c.get("line") else ""
        out.append(f"""      <a class="t-read" href="{c['href']}">
        <img src="{c['img']}" alt="{e(c.get('alt', ''))}" width="960" height="540" loading="lazy" decoding="async">
        <span class="tag">{e(c['tag'])}</span>
        <h3>{e(c['title'])}</h3>{line}
      </a>""")
    return "\n".join(out)


def faq_html(faq, fill):
    return "\n".join(f"""      <details>
        <summary>{e(q)}</summary>
        <p>{fill(a)}</p>
      </details>""" for q, a in faq)


def costs_html(rows, place, intro):
    body = "\n".join(f"          <tr><th scope=\"row\">{r[0]}</th><td>{r[1]}</td></tr>" for r in rows)
    return f"""
  <section class="t-section t-costs">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">Budget</p>
        <h2>What it costs to buy {e(place)}</h2>
        <p>{intro}</p>
        <p><a class="link-more" href="how-to-buy-an-apartment-or-house-in-spain.html">How to buy in Spain, step by step &rarr;</a></p>
      </div>
      <table class="cost-table t-table">
        <tbody>
{body}
        </tbody>
      </table>
    </div>
  </section>
"""


def page(p, *, crumbs, hero, kicker, h1, lead, body, schema, contact_name, cta="#listings", cta_label="See the properties"):
    url = f"{SITE}/{p['page']}"
    crumb_html = " <span>/</span> ".join(
        [f'<a href="{href}">{e(name)}</a>' for name, href in crumbs[:-1]] + [e(crumbs[-1][0])])
    schema = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": name, "item": SITE + "/" + (href.replace(".html", "") if href != "index.html" else "")}
        for n, (name, href) in enumerate(crumbs)]}] + schema
    title, desc = p["_title"], p["_description"]
    return f"""<!DOCTYPE html>
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
  <meta property="og:image" content="{SITE}/{hero}">
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
        <a href="{p['page']}.html" class="active" hreflang="en">EN</a>
        <a href="https://eliteworldestates.pl" hreflang="pl">PL</a>
      </div>
    </nav>
  </div>
</header>

<main class="town-page">
  <section class="t-hero" style="background-image:url({hero})">
    <div class="container">
      <nav class="t-crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
      <p class="t-kicker">{e(kicker)}</p>
      <h1>{e(h1)}</h1>
      <p class="t-lead">{lead}</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="{cta}">{e(cta_label)}</a>
        <a class="btn t-btn-light" href="#contact">Ask us about {e(contact_name)}</a>
      </div>
    </div>
  </section>
{body}
  <section class="t-contact" id="contact">
    <div class="container">
      <h2>Looking for a golf home {e(p['_where'])}?</h2>
      <p>Tell us your budget and what you need. We reply within one working day, in English, German, Spanish or Polish.</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="mailto:info@eliteworldestates.com?subject={e(contact_name).replace(' ', '%20')}%20property">Email us</a>
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


def filler(count, low, near_count=0):
    def fill(s):
        return (s.replace("{count}", str(count)).replace("{from}", f"€{low:,}")
                 .replace("{near_count}", str(near_count)))
    return fill


def collection(name, url, desc, items, about=None):
    d = {"@context": "https://schema.org", "@type": "CollectionPage", "name": name, "url": url, "description": desc, "inLanguage": "en",
         "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": [
             {"@type": "ListItem", "position": n + 1, "url": u, "name": t} for n, (u, t) in enumerate(items)]}}
    if about:
        d["about"] = about
    return d


def faq_schema(faq, fill):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", fill(a))}} for q, a in faq]}


def section(eyebrow, title, inner, cls="t-section"):
    return f"""
  <section class="{cls}">
    <div class="container">
      <p class="eyebrow dark">{eyebrow}</p>
      <h2>{e(title)}</h2>
{inner}
    </div>
  </section>
"""


def write(p, out):
    open(os.path.join(ROOT, p["page"] + ".html"), "w", encoding="utf-8").write(out)


def facts_band(facts, fill):
    return "\n  <ul class=\"t-facts container\">\n" + "\n".join(
        f'      <li><strong>{fill(v)}</strong><span>{fill(k)}</span></li>' for v, k in facts) + "\n  </ul>\n"


def build_course(c, cfg, pages, others):
    own, near = listings(c["page"], pages)
    low = low_price(own or near)
    fill = filler(len(own), low, len(near))
    c["_title"], c["_description"], c["_where"] = fill(c["title"]), fill(c["description"]), "at " + c["short"]
    url = f"{SITE}/{c['page']}"
    gw, gh = size(f"assets/golf/{c['photo']}")
    golf = "\n".join(f"        <p>{fill(x)}</p>" for x in c["golf"])
    why = "\n".join(f"        <p>{fill(x)}</p>" for x in c["why"])
    body = facts_band(c["facts"], fill)
    body += grid(own, pages, c.get("listings_title", "Properties for sale in " + c["short"]), fill(c.get("listings_intro", "")))
    body += grid(near, pages, c.get("near_title", "Nearby"), fill(c.get("near_intro", "")), "A short drive away",
                 "listings" if not own else "nearby")
    body += f"""
  <section class="t-section t-guide">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">The course</p>
        <h2>Golf at {e(c['name'])}</h2>
{golf}
      </div>
      <figure class="t-figure">
        <img class="t-photo" src="assets/golf/{c['photo']}" alt="{e(c['photo_alt'])}" width="{gw}" height="{gh}" loading="lazy" decoding="async">
      </figure>
    </div>
  </section>

  <section class="t-section">
    <div class="container t-narrow">
      <p class="eyebrow dark">Living here</p>
      <h2>Why buy a property at {e(c['short'])}?</h2>
{why}
    </div>
  </section>
"""
    body += costs_html(cfg["val_costs"], "at " + c["short"], "On top of the price you pay tax and fees. New builds pay VAT and stamp duty, resale homes pay transfer tax. Always ask us for the exact figure for the home you like.")
    body += section("Questions", f"{c['short']}: questions and answers", faq_html(c["faq"], fill), "t-section t-faq")
    body += section("More golf on the Costa Blanca", "Other golf resorts", '      <div class="t-reads">\n' + tiles(others) + "\n      </div>")
    body += section("From our blog", "Read before you buy", '      <div class="t-reads">\n' + tiles(cfg["costa_blanca"]["reads"]) + "\n      </div>")
    about = {"@type": "GolfCourse", "name": c["name"], "address": {"@type": "PostalAddress", "addressLocality": c["area"], "addressRegion": "Alicante", "addressCountry": "ES"}}
    schema = [collection(c["_title"].split(" | ")[0], url, c["_description"], [(url_of(i, pages), clean_title(i["title"])) for i in own + near], about),
              faq_schema(c["faq"], fill)]
    out = page(c, crumbs=[("Home", "index.html"), ("Golf properties", SPAIN + ".html"), ("Costa Blanca", CB + ".html"), (c["short"], c["page"] + ".html")],
               hero=f"assets/golf/{c['photo']}", kicker=f"Costa Blanca · {c['area']}", h1=c["title"].split(" | ")[0].replace("Properties for Sale", "Properties for sale"),
               lead=fill(c["lead"]), body=body, schema=schema, contact_name=c["short"])
    write(c, out)
    print(f"{c['page']}.html: {len(own)} at the course, {len(near)} nearby, from €{low:,}")
    return own, near


def course_tiles(cfg, counts, skip=None):
    out = []
    for c in cfg["courses"]:
        if c["key"] == skip:
            continue
        own, near = counts[c["key"]]
        n = f"{len(own)} properties" if own else f"{len(near)} nearby"
        out.append({"href": c["page"] + ".html", "img": f"assets/golf/{c.get('card_photo', c['photo'])}", "alt": c["photo_alt"],
                    "tag": f"{c['area']} · {n}", "title": c["short"], "line": c["card_line"]})
    return out


def main():
    cfg = json.load(open(os.path.join(HERE, "golf.json"), encoding="utf-8"))
    pages = local_pages()
    counts = {c["key"]: listings(c["page"], pages) for c in cfg["courses"]}
    for c in cfg["courses"]:
        build_course(c, cfg, pages, course_tiles(cfg, counts, c["key"]))

    # Costa Blanca: one card per golf course
    cb = cfg["costa_blanca"]
    cb_items = {i["ref"]: i for own, near in counts.values() for i in own + near}
    cb_low = low_price(list(cb_items.values()))
    fill = filler(len(cb_items), cb_low)
    cb["_title"], cb["_description"], cb["_where"] = fill(cb["title"]), fill(cb["description"]), "on the Costa Blanca"
    intro = "\n".join(f"        <p>{fill(x)}</p>" for x in cb["intro"])
    body = facts_band([["{count}", "golf properties for sale"], ["from {from}", "for an apartment"], [str(len(cfg["courses"])), "golf resorts"], ["320+", "days of sun a year"]], fill)
    body += f"""
  <section class="t-section" id="courses">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">Choose a golf resort</p>
          <h2>Properties near the best golf courses on the Costa Blanca</h2>
          <div class="lead">
{intro}
          </div>
        </div>
      </div>
      <div class="t-reads">
{tiles(course_tiles(cfg, counts))}
      </div>
    </div>
  </section>
"""
    body += costs_html(cfg["val_costs"], "on the Costa Blanca", "On top of the price you pay tax and fees. New builds pay VAT and stamp duty, resale homes pay transfer tax. Always ask us for the exact figure for the home you like.")
    body += section("Questions", "Golf properties on the Costa Blanca: questions and answers", faq_html(cb["faq"], fill), "t-section t-faq")
    body += section("From our blog", "Read before you buy", '      <div class="t-reads">\n' + tiles(cb["reads"]) + "\n      </div>")
    cb_url = f"{SITE}/{CB}"
    schema = [collection(cb["h1"], cb_url, cb["_description"], [(f"{SITE}/{c['page']}", c["name"]) for c in cfg["courses"]]), faq_schema(cb["faq"], fill)]
    write(cb, page(cb, crumbs=[("Home", "index.html"), ("Golf properties", SPAIN + ".html"), ("Costa Blanca", CB + ".html")],
                   hero=f"assets/golf/{cb['photo']}", kicker="Golf · Costa Blanca", h1=cb["h1"], lead=fill(cb["lead"]), body=body,
                   schema=schema, contact_name="Costa Blanca golf", cta="#courses", cta_label="Choose a golf resort"))
    print(f"{CB}.html: {len(cfg['courses'])} courses, {len(cb_items)} properties")

    # Costa del Sol: the listings and the golf areas
    cds = cfg["costa_del_sol"]
    own, _ = listings(CDS, pages)
    cds_low = low_price(own)
    fill = filler(len(own), cds_low)
    cds["_title"], cds["_description"], cds["_where"] = fill(cds["title"]), fill(cds["description"]), "on the Costa del Sol"
    areas = "\n".join(f"""        <div class="t-area">
          <h3>{e(a['name'])}</h3>
          <p>{a['text']}</p>
        </div>""" for a in cds["areas"])
    body = facts_band([["{count}", "golf properties for sale"], ["from {from}", "for an apartment"], ["70+", "golf courses on the coast"], ["about 30–60 min", "to Málaga airport"]], fill)
    body += grid(own, pages, "Golf properties for sale on the Costa del Sol", fill(cds["listings_intro"]))
    body += section("Where to buy", "The golf areas of the Costa del Sol", '      <div class="t-areas">\n' + areas + "\n      </div>")
    body += costs_html(cds["costs"], "on the Costa del Sol", "On top of the price you pay tax and fees. In Andalusia new builds pay VAT and stamp duty, resale homes pay transfer tax. Always ask us for the exact figure for the home you like.")
    body += section("Questions", "Golf properties on the Costa del Sol: questions and answers", faq_html(cds["faq"], fill), "t-section t-faq")
    body += section("From our blog", "Read before you buy", '      <div class="t-reads">\n' + tiles(cds["reads"]) + "\n      </div>")
    cds_url = f"{SITE}/{CDS}"
    schema = [collection(cds["h1"], cds_url, cds["_description"], [(url_of(i, pages), clean_title(i["title"])) for i in own]), faq_schema(cds["faq"], fill)]
    write(cds, page(cds, crumbs=[("Home", "index.html"), ("Golf properties", SPAIN + ".html"), ("Costa del Sol", CDS + ".html")],
                    hero=f"assets/golf/{cds['photo']}", kicker="Golf · Costa del Sol", h1=cds["h1"], lead=fill(cds["lead"]), body=body,
                    schema=schema, contact_name="Costa del Sol golf"))
    print(f"{CDS}.html: {len(own)} properties")

    # Costa Cálida: one section per golf course, each with the homes we sell nearest to it
    cc = cfg["costa_calida"]
    cc_groups = [(g, listings(f"{CC}--{g['key']}", pages)[0]) for g in cc["courses"]]
    cc_all = [i for _, items in cc_groups for i in items]
    cc_low = low_price(cc_all)
    fill = filler(len(cc_all), cc_low)
    cc["_title"], cc["_description"], cc["_where"] = fill(cc["title"]), fill(cc["description"]), "on the Costa Cálida"
    intro = "\n".join(f"        <p>{fill(x)}</p>" for x in cc["intro"])
    jump = " · ".join(f'<a href="#{g["key"]}">{e(g["name"])}</a>' for g, _ in cc_groups)
    body = facts_band([["{count}", "golf properties for sale"], ["from {from}", "for an apartment"], [str(len(cc_groups)), "golf areas with our homes"], ["20+", "golf courses in Murcia"]], fill)
    body += f"""
  <section class="t-section" id="courses">
    <div class="container">
      <p class="eyebrow dark">The golf courses</p>
      <h2>Golf courses on the Costa Cálida and the homes near them</h2>
      <div class="t-narrow">
{intro}
        <p class="g-jump">{jump}</p>
      </div>
    </div>
  </section>
"""
    for g, items in cc_groups:
        link = f'<br><a class="link-more" href="{g["town_link"][0]}">{e(g["town_link"][1])} &rarr;</a>' if g.get("town_link") else ""
        text = " ".join(fill(x) for x in g["text"])
        intro_html = f'<span class="g-facts">{e(g["facts"])}</span><br>{text}{link}'
        body += grid(items, pages, f"{g['name']}, {g['area']}", intro_html, "Golf course", g["key"])
    others = "\n".join(f"""        <div class="t-area">
          <h3>{e(o['name'])}</h3>
          <p>{o['text']}</p>
        </div>""" for o in cc["others"])
    body += section("More golf", "Other golf courses in the Region of Murcia", '      <div class="t-areas">\n' + others + "\n      </div>")
    body += costs_html(cc["costs"], "on the Costa Cálida", "On top of the price you pay tax and fees. In the Region of Murcia new builds pay VAT and stamp duty, resale homes pay transfer tax. Always ask us for the exact figure for the home you like.")
    body += section("Questions", "Golf properties on the Costa Cálida: questions and answers", faq_html(cc["faq"], fill), "t-section t-faq")
    body += section("Read more", "Before you buy", '      <div class="t-reads">\n' + tiles(cc["reads"]) + "\n      </div>")
    cc_url = f"{SITE}/{CC}"
    schema = [collection(cc["h1"], cc_url, cc["_description"], [(url_of(i, pages), clean_title(i["title"])) for i in cc_all]), faq_schema(cc["faq"], fill)]
    write(cc, page(cc, crumbs=[("Home", "index.html"), ("Golf properties", SPAIN + ".html"), ("Costa Cálida", CC + ".html")],
                   hero=f"assets/golf/{cc['photo']}", kicker="Golf · Costa Cálida · Murcia", h1=cc["h1"], lead=fill(cc["lead"]), body=body,
                   schema=schema, contact_name="Costa Cálida golf", cta="#courses", cta_label="See the golf courses"))
    print(f"{CC}.html: {len(cc_groups)} golf areas, {len(cc_all)} properties")

    # Spain: the three coasts
    sp = cfg["spain"]
    total = len(cb_items) + len(own) + len(cc_all)
    fill = filler(total, min(cb_low, cds_low, cc_low))
    sp["_title"], sp["_description"], sp["_where"] = fill(sp["title"]), fill(sp["description"]), "in Spain"
    intro = "\n".join(f"      <p>{fill(x)}</p>" for x in sp["intro"])
    coasts = [{"href": CB + ".html", "img": f"assets/golf/{cb['photo']}", "alt": cb["photo_alt"], "tag": f"{len(cb_items)} properties · {len(cfg['courses'])} golf resorts",
               "title": "Golf properties on the Costa Blanca", "line": "Las Colinas, La Finca, Vistabella, Bonalba, Font del Llop, La Marquesa, Puig Campana and Alenda."},
              {"href": CDS + ".html", "img": f"assets/golf/{cds['photo']}", "alt": cds["photo_alt"], "tag": f"{len(own)} properties",
               "title": "Golf properties on the Costa del Sol", "line": "Estepona, Casares, Mijas, Marbella and Benahavís."},
              {"href": CC + ".html", "img": f"assets/golf/{cc['photo']}", "alt": cc["photo_alt"], "tag": f"{len(cc_all)} properties · Region of Murcia",
               "title": "Golf properties on the Costa Cálida", "line": "La Serena, Roda, La Torre, Hacienda del Álamo, El Valle and La Manga Club."}]
    body = facts_band([["{count}", "golf properties for sale"], ["from {from}", "for an apartment"], ["3", "coasts"], ["300+", "days of sun a year"]], fill)
    body += f"""
  <section class="t-section" id="coasts">
    <div class="container">
      <p class="eyebrow dark">Choose a coast</p>
      <h2>Golf properties on the Costa Blanca, Costa del Sol and Costa Cálida</h2>
      <div class="t-narrow">
{intro}
      </div>
      <div class="t-reads">
{tiles(coasts)}
      </div>
    </div>
  </section>
"""
    body += section("Costa Blanca", "Golf resorts on the Costa Blanca", '      <div class="t-reads">\n' + tiles(course_tiles(cfg, counts)) + "\n      </div>")
    body += section("Questions", "Buying a golf property in Spain: questions and answers", faq_html(sp["faq"], fill), "t-section t-faq")
    body += section("From our blog", "Read before you buy", '      <div class="t-reads">\n' + tiles(sp["reads"]) + "\n      </div>")
    sp_url = f"{SITE}/{SPAIN}"
    schema = [collection(sp["h1"], sp_url, sp["_description"], [(cb_url, "Golf properties on the Costa Blanca"), (cds_url, "Golf properties on the Costa del Sol"), (cc_url, "Golf properties on the Costa Cálida")]),
              faq_schema(sp["faq"], fill)]
    write(sp, page(sp, crumbs=[("Home", "index.html"), ("Golf properties", SPAIN + ".html")],
                   hero=f"assets/golf/{sp['photo']}", kicker="Golf · Spain", h1=sp["h1"], lead=fill(sp["lead"]), body=body,
                   schema=schema, contact_name="golf properties", cta="#coasts", cta_label="Choose a coast"))
    print(f"{SPAIN}.html: {total} properties")


if __name__ == "__main__":
    main()
