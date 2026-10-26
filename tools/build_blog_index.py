"""Build the blog index pages (blog.html, de-de/blog.html, es-es/blog.html).

Usage: python3 tools/build_blog_index.py

Lists every article in tools/blog/*.json (newest first) with a photo,
topic, summary, author and date. The newest article is shown large at
the top. Topic buttons filter the list and a button shows 12 more
articles at a time; without JavaScript every article is listed, so search engines see them all.
Card photos (960px) are made once in assets/blog/thumbs/.
"""
import json
import os
import re

from PIL import Image

import build_blog as bb

ROOT, SRC, SITE, LANGS, DIRS = bb.ROOT, bb.SRC, bb.SITE, bb.LANGS, bb.DIRS
esc = bb.esc

# Topic of each article (file name in tools/blog without .json)
TOPICS = {
    "buying": ["costa-blanca-or-costa-del-sol", "how-to-buy", "luxury-villa-in-spain", "mortgage-spain", "near-the-sea",
               "new-build-vs-resale", "new-construction", "nie-number", "nota-simple", "pool", "property-prices",
               "squatters-in-spain", "spain-or-italy", "villa-or-apartment", "buying-through-a-company", "investment"],
    "owning": ["banks", "comunidad", "home-care", "home-insurance", "ibi-property-tax", "inheriting-property",
               "long-term-rental", "short-term-rentals", "resident-vs-non-resident", "property-taxes-spain", "non-eu-tax"],
    "living": ["best-paid-jobs-in-spain", "cost-of-living", "moving-to-spain", "retirement-in-spain",
               "staying-over-90-days", "tipping-in-spain", "traffic-fines-spain", "weather-in-alicante",
               "education-in-spain", "off-season", "best-places-for-seniors", "healthcare-in-spain",
               "is-spain-safe", "facts-about-spain", "spain-by-car", "life-after-moving", "life-on-the-costa-blanca", "easter-in-spain", "three-kings-day", "new-year-in-spain", "christmas-in-spain", "valentines-day-spain"],
    "places": ["altea", "cumbre-del-sol", "la-hoya", "la-zagaleta", "new-developments-alicante", "santa-rosalia", "calpe-property-market", "alicante-property-market", "torrevieja-property-market", "wellness-costa-blanca", "costa-blanca-beaches", "puerto-banus", "golf-costa-del-sol", "javea-guide", "marbella-what-to-see", "costa-del-sol-top-10", "beautiful-cities-spain", "calpe-what-to-see", "torrevieja-what-to-see", "benidorm-what-to-see", "alicante-what-to-see", "top-hotels-alicante", "golf-costa-blanca"],
}
TOPIC_OF = {n: t for t, names in TOPICS.items() for n in names}

T = {
    "en": dict(title="Blog: Buying, Owning and Living in Spain | Elite World Estates",
               desc="Practical, fact-checked guides on buying property in Spain, taxes and owning a home, everyday life and the best places on the Costa Blanca and Costa del Sol.",
               eyebrow="Elite World Estates blog", h1="Buying, owning and living in Spain",
               lead="Practical guides from our property advisers on the Costa Blanca and the Costa del Sol. Every article is checked and updated for 2026.",
               all="All articles", latest="Latest article", read_more="Read the article", count="{n} articles",
               topics=dict(buying="Buying a home", owning="Owning and taxes", living="Living in Spain", places="Places and developments"),
               more="Show more articles ({n} more)", cta_h="Looking for a home in Spain?", cta_p="Tell us what you are looking for and we will send you homes that match.", cta_b="Contact us"),
    "de": dict(title="Blog: Kaufen, Besitzen und Leben in Spanien | Elite World Estates",
               desc="Praktische, geprüfte Ratgeber zum Immobilienkauf in Spanien, zu Steuern und Eigentum, zum Alltag und zu den schönsten Orten an der Costa Blanca und Costa del Sol.",
               eyebrow="Blog von Elite World Estates", h1="Kaufen, besitzen und leben in Spanien",
               lead="Praktische Ratgeber unserer Immobilienberaterinnen an der Costa Blanca und der Costa del Sol. Jeder Artikel ist geprüft und für 2026 aktualisiert.",
               all="Alle Artikel", latest="Neuester Artikel", read_more="Artikel lesen", count="{n} Artikel",
               topics=dict(buying="Immobilienkauf", owning="Eigentum und Steuern", living="Leben in Spanien", places="Orte und Projekte"),
               more="Weitere Artikel anzeigen ({n} weitere)", cta_h="Sie suchen eine Immobilie in Spanien?", cta_p="Sagen Sie uns, was Sie suchen, und wir senden Ihnen passende Angebote.", cta_b="Kontakt"),
    "es": dict(title="Blog: comprar, tener y vivir en España | Elite World Estates",
               desc="Guías prácticas y verificadas sobre comprar vivienda en España, impuestos y propiedad, la vida diaria y los mejores lugares de la Costa Blanca y la Costa del Sol.",
               eyebrow="Blog de Elite World Estates", h1="Comprar, tener y vivir en España",
               lead="Guías prácticas de nuestras asesoras inmobiliarias en la Costa Blanca y la Costa del Sol. Cada artículo está revisado y actualizado para 2026.",
               all="Todos los artículos", latest="Último artículo", read_more="Leer el artículo", count="{n} artículos",
               topics=dict(buying="Comprar vivienda", owning="Propiedad e impuestos", living="Vivir en España", places="Lugares y promociones"),
               more="Ver más artículos ({n} más)", cta_h="¿Buscas casa en España?", cta_p="Cuéntanos qué buscas y te enviaremos viviendas que encajen.", cta_b="Contacta con nosotros"),
}


def thumb(src, name):
    """Make a 960px card photo next to the article photos (once)."""
    rel = f"assets/blog/thumbs/{name}.jpg"
    out = os.path.join(ROOT, rel)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(os.path.join(ROOT, src)) or Image.open(out).width < 960:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im = Image.open(os.path.join(ROOT, src)).convert("RGB")
        w, h = im.size
        ch = int(w * 9 / 16)
        if ch < h:
            top = (h - ch) // 2
            im = im.crop((0, top, w, top + ch))
        im.thumbnail((960, 540))
        im.save(out, "JPEG", quality=78, optimize=True, progressive=True)
    return rel


def minutes(t):
    words = len(bb.strip_tags(" ".join([t["short"]] + t["intro"] + [s["html"] for s in t["sections"]] + [t["closing"]["html"]])).split())
    return max(3, round(words / 200))


def load():
    arts = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".json"):
            continue
        name = f[:-5]
        a = json.load(open(os.path.join(SRC, f), encoding="utf-8"))
        a["_name"] = name
        a["_topic"] = TOPIC_OF.get(name, "buying")
        a["_thumb"] = thumb(a["hero"], name)
        arts.append(a)
    # Wellness article is a hand-made English page, not built from JSON
    p = os.path.join(ROOT, "wellness-retreats-in-marbella.html")
    if os.path.exists(p):
        s = open(p, encoding="utf-8").read()
        meta = lambda k: re.search(r'<meta (?:name|property)="%s" content="([^"]*)"' % k, s).group(1)
        hero = meta("og:image").replace(SITE + "/", "")
        arts.append({"_name": "wellness-retreats-in-marbella", "_topic": "places", "_only": "en", "hero": hero,
                     "_thumb": thumb(hero, "wellness-retreats-in-marbella"), "author": "lucyna",
                     "published": meta("article:published_time"), "_minutes": 7,
                     "en": {"slug": "wellness-retreats-in-marbella", "description": bb.html.unescape(meta("description")),
                            "eyebrow": "Costa del Sol · Lifestyle",
                            "h1": bb.html.unescape(re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S).group(1).strip())}})
    arts.sort(key=lambda a: a["published"], reverse=True)
    return arts


def card(a, lang, up, big=False):
    t = a[lang]
    tx = T[lang]
    au = bb.AUTHORS[a["author"]]
    mins = a.get("_minutes") or minutes(t)
    href = f'{up}{DIRS[lang]}{t["slug"]}.html' if lang == "en" else f'{t["slug"]}.html'
    head = "h2" if big else "h3"
    load = 'fetchpriority="high"' if big else 'loading="lazy" decoding="async"'
    img = a["hero"] if big else a["_thumb"]
    more = f'\n        <span class="blog-more">{tx["read_more"]} &rarr;</span>' if big else ""
    return f'''    <article class="blog-card{" blog-feature" if big else ""}" data-topic="{a["_topic"]}">
      <a href="{href}">
        <img src="{up}{img}" alt="" width="{1280 if big else 960}" height="{720 if big else 540}" {load}>
        <div class="blog-card-body">
          <p class="tag">{esc(tx["topics"][a["_topic"]])}</p>
          <{head}>{esc(t["h1"])}</{head}>
          <p class="blog-excerpt">{esc(t["description"])}</p>
          <p class="blog-meta"><img src="{up}{au["photo"]}" alt="" width="28" height="28" loading="lazy"> {au["name"]} · <time datetime="{a["published"]}">{bb.nice_date(a["published"], lang)}</time> · {mins} {bb.UI[lang]["read"]}</p>{more}
        </div>
      </a>
    </article>'''


def page(arts, lang):
    tx = T[lang]
    ui = bb.UI[lang]
    up = "" if lang == "en" else "../"
    own = [a for a in arts if a.get("_only", lang) == lang]
    feat, rest = own[0], own[1:]
    canon = f"{SITE}/{DIRS[lang]}blog"
    alts = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{SITE}/{DIRS[l]}blog">' for l in LANGS)
    alts += f'\n  <link rel="alternate" hreflang="x-default" href="{SITE}/blog">\n  <link rel="alternate" hreflang="pl" href="https://eliteworldestates.pl/blog">'
    langs = "\n        ".join(f'<a href="{up}{DIRS[l]}blog.html"{" class=\"active\"" if l == lang else ""} hreflang="{l}">{l.upper()}</a>' for l in LANGS)
    langs += '\n        <a href="https://eliteworldestates.pl/blog" hreflang="pl">PL</a>'
    chips = f'<button type="button" class="chip active" data-topic="all">{tx["all"]}</button>' + "".join(
        f'<button type="button" class="chip" data-topic="{k}">{esc(v)}</button>' for k, v in tx["topics"].items())
    ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": tx["h1"], "description": tx["desc"],
         "url": canon, "inLanguage": lang,
         "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(own), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": f'{SITE}/{DIRS[lang]}{a[lang]["slug"]}', "name": a[lang]["h1"]}
             for i, a in enumerate(own)]}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": ui["home"], "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": ui["blog"], "item": canon}]},
    ]
    cards = "\n".join(card(a, lang, up) for a in rest)
    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(tx["title"])}</title>
  <meta name="description" content="{esc(tx["desc"])}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{canon}">
{alts}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:locale" content="{bb.LOCALE[lang]}">
  <meta property="og:title" content="{esc(tx["title"])}">
  <meta property="og:description" content="{esc(tx["desc"])}">
  <meta property="og:url" content="{canon}">
  <meta property="og:image" content="{SITE}/{feat["hero"]}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{up}assets/logo.png" type="image/png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,400&family=Prata&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{up}css/style.css">
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
</head>
<body>

<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="{up}index.html" aria-label="Elite World Estates – {ui["home"]}">
      <img src="{up}assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="{ui["menu"]}" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="{ui["main"]}">
      <a href="{up}index.html">{ui["home"]}</a>
      <a href="{up}index.html#properties">{ui["props"]}</a>
      <a href="{up}{DIRS[lang]}blog.html" class="active" aria-current="page">{ui["blog"]}</a>
      <a href="{up}about-us.html">{ui["about"]}</a>
      <a href="{up}index.html#contact">{ui["contact"]}</a>
      <div class="lang">
        {langs}
      </div>
    </nav>
  </div>
</header>

<main class="blog-page">
  <div class="container">
    <nav class="breadcrumb" aria-label="{ui["crumbs"]}">
      <a href="{up}index.html">{ui["home"]}</a> <span>/</span> <span aria-current="page">{ui["blog"]}</span>
    </nav>
    <header class="blog-head">
      <p class="eyebrow">{tx["eyebrow"]}</p>
      <h1>{tx["h1"]}</h1>
      <p class="lead">{tx["lead"]}</p>
    </header>

    <p class="eyebrow blog-label">{tx["latest"]}</p>
{card(feat, lang, up, big=True)}

    <div class="blog-filter" role="group" aria-label="{ui["blog"]}">
      {chips}
    </div>
    <p class="blog-count" aria-live="polite">{tx["count"].format(n=len(rest))}</p>

    <div class="blog-grid">
{cards}
    </div>
    <div class="blog-more-wrap"><button type="button" class="btn blog-show-more" hidden></button></div>

    <section class="blog-cta">
      <h2>{tx["cta_h"]}</h2>
      <p>{tx["cta_p"]}</p>
      <a class="btn btn-gold" href="{up}index.html#contact">{tx["cta_b"]}</a>
    </section>
  </div>
</main>

<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="{up}index.html">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>{ui["reg"]}</p>
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="{up}js/main.js"></script>
<script>
(function () {{
  // Show 12 cards at a time; all cards stay in the HTML for search engines
  var STEP = 12, limit = STEP, topic = "all",
      chips = document.querySelectorAll(".blog-filter .chip"), cards = document.querySelectorAll(".blog-grid .blog-card"),
      count = document.querySelector(".blog-count"), more = document.querySelector(".blog-show-more"),
      label = {json.dumps(tx["count"])}, moreLabel = {json.dumps(tx["more"])};
  function render() {{
    var n = 0, shown = 0;
    cards.forEach(function (k) {{
      var match = topic === "all" || k.dataset.topic === topic;
      if (match) n++;
      k.hidden = !match || n > limit;
      if (!k.hidden) shown++;
    }});
    count.textContent = label.replace("{{n}}", n);
    more.hidden = shown >= n;
    more.textContent = moreLabel.replace("{{n}}", n - shown);
  }}
  chips.forEach(function (c) {{
    c.addEventListener("click", function () {{
      topic = c.dataset.topic; limit = STEP;
      chips.forEach(function (x) {{ x.classList.toggle("active", x === c); x.setAttribute("aria-pressed", x === c); }});
      render();
    }});
  }});
  more.addEventListener("click", function () {{
    var first = limit; limit += STEP; render();
    var next = Array.prototype.filter.call(cards, function (k) {{ return !k.hidden; }})[first];
    if (next) next.querySelector("a").focus({{ preventScroll: true }});
  }});
  render();
}})();
</script>
</body>
</html>
'''


def update_sitemap():
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"  <!-- blog-index -->.*?<!-- /blog-index -->\n", "", s, flags=re.S)
    alt = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE}/{DIRS[l]}blog"/>\n' for l in LANGS)
    alt += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/blog"/>\n'
    import datetime
    today = datetime.date.today().isoformat()
    blocks = "".join(f"  <url>\n    <loc>{SITE}/{DIRS[l]}blog</loc>\n    <lastmod>{today}</lastmod>\n{alt}  </url>\n" for l in LANGS)
    s = s.replace("</urlset>", "  <!-- blog-index -->\n" + blocks + "  <!-- /blog-index -->\n</urlset>")
    open(p, "w", encoding="utf-8").write(s)


if __name__ == "__main__":
    arts = load()
    for lang in LANGS:
        path = os.path.join(ROOT, DIRS[lang], "blog.html")
        open(path, "w", encoding="utf-8").write(page(arts, lang))
        print("built", os.path.relpath(path, ROOT))
    update_sitemap()
