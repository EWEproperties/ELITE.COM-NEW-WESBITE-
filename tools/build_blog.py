"""Build blog article pages (EN, DE, ES) from tools/blog/<slug>.json.

Usage: python3 tools/build_blog.py [slug ...]   (no args = all articles)

Each JSON file holds one article: shared fields (author, dates, images,
cards) and a block per language ("en", "de", "es") with the text.
English pages go to the site root, German to de-de/, Spanish to es-es/,
keeping the live eGO addresses so existing rankings carry over.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "blog")
SITE = "https://www.eliteworldestates.com"
LANGS = ("en", "de", "es")
DIRS = {"en": "", "de": "de-de/", "es": "es-es/"}
LOCALE = {"en": "en_GB", "de": "de_DE", "es": "es_ES"}

AUTHORS = {
    "anita": {
        "name": "Anita Orłowska", "photo": "assets/about/anita-orlowska.jpg",
        "phone": "+34 672 51 98 09", "tel": "+34672519809", "email": "anita@eliteworldestates.com",
        "role": {"en": "Property Adviser", "de": "Immobilienberaterin", "es": "Asesora inmobiliaria"},
        "bio": {
            "en": "Founder of Elite World Estates. Anita has helped buyers find homes on the Costa Blanca and Costa del Sol since 2018.",
            "de": "Gründerin von Elite World Estates. Anita hilft Käufern seit 2018, ihr Zuhause an der Costa Blanca und der Costa del Sol zu finden.",
            "es": "Fundadora de Elite World Estates. Desde 2018 ayuda a compradores a encontrar su casa en la Costa Blanca y la Costa del Sol.",
        },
    },
    "lucyna": {
        "name": "Lucyna Gacek", "photo": "assets/about/lucyna-gacek.jpg",
        "phone": "+34 604 33 53 23", "tel": "+34604335323", "email": "lucy@eliteworldestates.com",
        "role": {"en": "Property Adviser", "de": "Immobilienberaterin", "es": "Asesora inmobiliaria"},
        "bio": {
            "en": "Lucyna helps buyers find homes on the Costa Blanca and Costa del Sol and writes about life in Spain.",
            "de": "Lucyna hilft Käufern bei der Suche nach einem Zuhause an der Costa Blanca und der Costa del Sol und schreibt über das Leben in Spanien.",
            "es": "Lucyna ayuda a compradores a encontrar casa en la Costa Blanca y la Costa del Sol y escribe sobre la vida en España.",
        },
    },
    "aleksandra": {
        "name": "Aleksandra Kobus", "photo": "assets/about/aleksandra-kobus.jpg",
        "phone": "+34 613 80 29 23", "tel": "+34613802923", "email": "aleksandra@eliteworldestates.com",
        "role": {"en": "Property Adviser", "de": "Immobilienberaterin", "es": "Asesora inmobiliaria"},
        "bio": {
            "en": "Aleksandra guides buyers through every step of buying in Spain, from the first viewing to the notary.",
            "de": "Aleksandra begleitet Käufer durch jeden Schritt des Immobilienkaufs in Spanien, von der ersten Besichtigung bis zum Notar.",
            "es": "Aleksandra acompaña a los compradores en cada paso de la compra en España, desde la primera visita hasta la notaría.",
        },
    },
}

# Property cards that can be shown under an article (live eGO links for now).
CARDS = {
    "20927700": ("Costa del Sol", "villa", "Benahavís", "https://www.eliteworldestates.com/property-details/spectacular-villa-with-sea-views-in-benahavis/20927700"),
    "26627092": ("Costa del Sol", "villa", "El Higuerón", "https://www.eliteworldestates.com/property-details/prestigious-villa-with-panoramic-sea-views-in-el-higueron/26627092"),
    "26614054": ("Costa del Sol", "villa", "Estepona", "https://www.eliteworldestates.com/property-details/exclusive-villa-with-private-pool-2-km-from-the-beach-in-estepona/26614054"),
    "26232807": ("Costa del Sol", "luxury", "Real de la Quinta", "https://www.eliteworldestates.com/property-details/26232807"),
    "18595762": ("Costa Blanca", "luxury", "Altea", "https://www.eliteworldestates.com/property-details/18595762"),
    "26234196": ("Costa Blanca", "luxury", "Jávea", "https://www.eliteworldestates.com/property-details/26234196"),
    "20598512": ("Costa Blanca", "luxury", "Cumbre del Sol", "https://www.eliteworldestates.com/property-details/20598512"),
    "23527637": ("Costa Blanca", "luxury", "Benissa", "https://www.eliteworldestates.com/property-details/23527637"),
    "26157630": ("Costa Blanca", "villa", "El Campello", "https://www.eliteworldestates.com/property-details/26157630"),
    "21034180": ("Costa Blanca", "villa", "La Nucía", "https://www.eliteworldestates.com/property-details/21034180"),
    "24623926": ("Costa Blanca", "villa", "Finestrat", "https://www.eliteworldestates.com/property-details/24623926"),
    "26239846": ("Costa Blanca", "villa", "Torrevieja", "https://www.eliteworldestates.com/property-details/26239846"),
    "24758318": ("Costa Blanca", "apartment", "Calpe", "https://www.eliteworldestates.com/property-details/24758318"),
    "23844656": ("Costa Blanca", "apartment", "Villajoyosa", "https://www.eliteworldestates.com/property-details/23844656"),
    "23935651": ("Costa Blanca", "apartment", "Benidorm", "https://www.eliteworldestates.com/property-details/23935651"),
}
CARD_TYPE = {
    "villa": {"en": ("Villa", "Villa for sale in {t}"), "de": ("Villa", "Villa zum Verkauf in {t}"), "es": ("Villa", "Villa en venta en {t}")},
    "luxury": {"en": ("Luxury villa", "Luxury villa for sale in {t}"), "de": ("Luxusvilla", "Luxusvilla zum Verkauf in {t}"), "es": ("Villa de lujo", "Villa de lujo en venta en {t}")},
    "apartment": {"en": ("Apartment", "Apartment for sale in {t}"), "de": ("Wohnung", "Wohnung zum Verkauf in {t}"), "es": ("Apartamento", "Apartamento en venta en {t}")},
}

UI = {
    "en": dict(home="Home", props="Properties", blog="Blog", about="About Us", contact="Contact Us", menu="Open menu",
               main="Main", crumbs="Breadcrumb", by="By", updated="updated", read="min read", contents="Contents",
               short="In short:", faq="Frequently asked questions", author="About the author", view="View property",
               cards="Properties on the {c}", reg="Registered in the Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) no. 2321.",
               months=["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]),
    "de": dict(home="Startseite", props="Immobilien", blog="Blog", about="Über uns", contact="Kontakt", menu="Menü öffnen",
               main="Hauptmenü", crumbs="Navigationspfad", by="Von", updated="aktualisiert", read="Min. Lesezeit", contents="Inhalt",
               short="Kurz gesagt:", faq="Häufige Fragen", author="Über die Autorin", view="Immobilie ansehen",
               cards="Immobilien an der {c}", reg="Eingetragen im Register der Immobilienvermittler der Region Valencia (RAICV) unter Nr. 2321.",
               months=["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]),
    "es": dict(home="Inicio", props="Propiedades", blog="Blog", about="Sobre nosotros", contact="Contacto", menu="Abrir menú",
               main="Principal", crumbs="Ruta de navegación", by="Por", updated="actualizado", read="min de lectura", contents="Índice",
               short="En resumen:", faq="Preguntas frecuentes", author="Sobre la autora", view="Ver propiedad",
               cards="Propiedades en la {c}", reg="Inscrita en el Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) con el n.º 2321.",
               months=["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]),
}


def esc(t):
    return html.escape(t, quote=True)


def strip_tags(t):
    return html.unescape(re.sub(r"<[^>]+>", "", t))


def nice_date(iso, lang):
    y, m, d = (int(x) for x in iso.split("-"))
    mon = UI[lang]["months"][m - 1]
    return f"{d}. {mon} {y}" if lang == "de" else (f"{d} de {mon} de {y}" if lang == "es" else f"{d} {mon} {y}")


_PL_EN = None


def pl_pair(a):
    """True if a["pl"] is the Polish article that names this one as its match (hreflang must go both ways)."""
    global _PL_EN
    if _PL_EN is None:
        p = os.path.join(ROOT, "tools", "blog-pl", "articles.json")
        pl = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        _PL_EN = {f"{SITE}/pl-pl/{k}": json.load(open(os.path.join(SRC, v["en"] + ".json"), encoding="utf-8"))["en"]["slug"]
                  for k, v in pl.items() if v.get("en")}
    return _PL_EN.get(a.get("pl")) == a["en"]["slug"]


def url(a, lang):
    return f"{SITE}/{DIRS[lang]}{a[lang]['slug']}"


def figure(src, alt, up, eager=False):
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<figure><img src="{up}{src}" alt="{esc(alt)}" width="1280" height="720" {load}></figure>')


def page(a, lang):
    t = a[lang]
    ui = UI[lang]
    au = AUTHORS[a["author"]]
    up = "" if lang == "en" else "../"
    canon = url(a, lang)
    hero = a["hero"]
    words = len(strip_tags(" ".join([t["short"]] + t["intro"] + [s["html"] for s in t["sections"]] + [t["closing"]["html"]])).split())
    minutes = max(3, round(words / 200))

    alts = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{url(a, l)}">' for l in LANGS)
    alts += f'\n  <link rel="alternate" hreflang="x-default" href="{url(a, "en")}">'
    langs = "\n        ".join(
        f'<a href="{url(a, l)}"{" class=\"active\"" if l == lang else ""} hreflang="{l}">{l.upper()}</a>' for l in LANGS)
    if a.get("pl"):
        pl_href = a["pl"]
        if pl_href.startswith(SITE + "/pl-pl/"):  # Polish blog on this site
            pl_href = up + pl_href[len(SITE) + 1:] + ".html"
        langs += f'\n        <a href="{pl_href}" hreflang="pl">PL</a>'
        if pl_pair(a):
            alts += f'\n  <link rel="alternate" hreflang="pl" href="{a["pl"]}">'

    faq_ld = [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip_tags(ans)}} for q, ans in t["faq"]]
    ld = [
        {"@context": "https://schema.org", "@type": "BlogPosting", "@id": canon + "#article", "mainEntityOfPage": canon,
         "headline": t["h1"], "description": t["description"], "image": f"{SITE}/{hero}",
         "datePublished": a["published"], "dateModified": a["modified"], "inLanguage": lang,
         "author": {"@type": "Person", "name": au["name"], "jobTitle": au["role"][lang], "image": f"{SITE}/{au['photo']}",
                    "url": f"{SITE}/about-us.html", "worksFor": {"@id": f"{SITE}/#organization"}},
         "publisher": {"@id": f"{SITE}/#organization"}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": ui["home"], "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": ui["blog"], "item": f"{SITE}/blog"},
            {"@type": "ListItem", "position": 3, "name": t["crumb"], "item": canon}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faq_ld},
        {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": f"{SITE}/#organization", "name": "Elite World Estates",
         "url": f"{SITE}/", "logo": f"{SITE}/assets/logo.png", "telephone": "+34 672 519 809", "email": "info@eliteworldestates.com"},
    ]

    toc = ""
    if len(t["sections"]) >= 4:
        items = "\n".join(f'            <li><a href="#{s["id"]}">{s["h2"]}</a></li>' for s in t["sections"])
        toc = f'''
        <nav class="toc" aria-label="{ui["contents"]}">
          <p class="toc-title">{ui["contents"]}</p>
          <ol>
{items}
          </ol>
        </nav>
'''
    secs = []
    for i, s in enumerate(t["sections"]):
        img = a.get("images", {}).get(s["id"])
        fig = ("\n        " + figure(img, s["alt"], up)) if img else ""
        secs.append(f'        <h2 id="{s["id"]}">{s["h2"]}</h2>{fig}\n        {s["html"]}')
    faq = "\n".join(f"          <details><summary>{q}</summary><p>{ans}</p></details>" for q, ans in t["faq"])
    c = t["closing"]
    cimg = a.get("images", {}).get("closing")
    cfig = ("\n        " + figure(cimg, c["alt"], up)) if cimg else ""

    sources = ""
    if a.get("sources"):
        label = {"en": "Sources", "de": "Quellen", "es": "Fuentes"}[lang]
        links = " · ".join(f'<a href="{u}" rel="noopener" target="_blank">{esc(n)}</a>' for n, u in a["sources"])
        sources = f'        <p class="small-print sources">{label}: {links}</p>'

    cards = ""
    if a.get("cards"):
        coast = CARDS[a["cards"][0]][0]
        cs = []
        for cid in a["cards"]:
            _, kind, town, link = CARDS[cid]
            badge, title = CARD_TYPE[kind][lang]
            title = title.format(t=town)
            cs.append(f'''      <a class="card" href="{link}" target="_blank" rel="noopener">
        <div class="card-photo"><img src="{up}assets/properties/{cid}.jpg" alt="{esc(title)}" width="512" height="288" loading="lazy" decoding="async"><span class="badge">{badge}</span></div>
        <div class="card-body">
          <h3>{title}</h3>
          <span class="card-link">{ui["view"]} &rarr;</span>
        </div>
      </a>''')
        cards = f'''
    <section class="similar" aria-label="{esc(ui["cards"].format(c=coast))}">
      <h2>{ui["cards"].format(c=coast)}</h2>
      <div class="grid">
{chr(10).join(cs)}
      </div>
    </section>'''

    pub, mod = a["published"], a["modified"]
    upd = f' · {ui["updated"]} <time datetime="{mod}">{nice_date(mod, lang)}</time>' if mod != pub else ""
    return f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(t["title"])}</title>
  <meta name="description" content="{esc(t["description"])}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <meta name="author" content="{au["name"]}">
  <link rel="canonical" href="{canon}">
{alts}
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:title" content="{esc(t["h1"])}">
  <meta property="og:description" content="{esc(t["description"])}">
  <meta property="og:url" content="{canon}">
  <meta property="og:image" content="{SITE}/{hero}">
  <meta property="og:image:width" content="1280">
  <meta property="og:image:height" content="720">
  <meta property="og:locale" content="{LOCALE[lang]}">
  <meta property="article:published_time" content="{pub}">
  <meta property="article:modified_time" content="{mod}">
  <meta property="article:author" content="{au["name"]}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{up}assets/logo.png" type="image/png">
  <link rel="preload" as="image" href="{up}{hero}" fetchpriority="high">
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
      <a href="{up}{DIRS[lang]}blog.html" class="active">{ui["blog"]}</a>
      <a href="{up}about-us.html">{ui["about"]}</a>
      <a href="{up}index.html#contact">{ui["contact"]}</a>
      <div class="lang">
        {langs}
      </div>
    </nav>
  </div>
</header>

<main class="article-page">
  <div class="container article-wrap">
    <nav class="breadcrumb" aria-label="{ui["crumbs"]}">
      <a href="{up}index.html">{ui["home"]}</a> <span>/</span> <a href="{up}{DIRS[lang]}blog.html">{ui["blog"]}</a> <span>/</span> <span aria-current="page">{t["crumb"]}</span>
    </nav>

    <article class="post">
      <header class="post-head">
        <p class="eyebrow">{t["eyebrow"]}</p>
        <h1>{t["h1"]}</h1>
        <p class="byline">
          <img src="{up}{au["photo"]}" alt="" width="48" height="48">
          <span>{ui["by"]} <a href="{up}about-us.html">{au["name"]}</a> · <time datetime="{pub}">{nice_date(pub, lang)}</time>{upd} · {minutes} {ui["read"]}</span>
        </p>
      </header>

      <figure class="post-hero">
        <img src="{up}{hero}" alt="{esc(t["hero_alt"])}" width="1280" height="720" fetchpriority="high">
      </figure>

      <div class="post-body">
        <div class="in-short">
          <p><strong>{ui["short"]}</strong> {t["short"]}</p>
        </div>

        {"".join("<p>" + p + "</p>" for p in t["intro"])}
{toc}
{chr(10).join(secs)}

        <h2>{ui["faq"]}</h2>
        <div class="faq">
{faq}
        </div>

        <h2>{c["h2"]}</h2>{cfig}
        {c["html"]}
{sources}

        <aside class="author-box" aria-label="{ui["author"]}">
          <img src="{up}{au["photo"]}" alt="{au["name"]}, {au["role"][lang]} – Elite World Estates" width="96" height="96" loading="lazy">
          <div>
            <p class="author-name">{au["name"]}</p>
            <p>{au["role"][lang]} – Elite World Estates. {au["bio"][lang]}</p>
            <p><a href="tel:{au["tel"]}">{au["phone"]}</a> · <a href="mailto:{au["email"]}">{au["email"]}</a></p>
          </div>
        </aside>
      </div>
    </article>
{cards}
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
</body>
</html>
'''


def build(slug):
    a = json.load(open(os.path.join(SRC, slug + ".json"), encoding="utf-8"))
    out = []
    for lang in LANGS:
        path = os.path.join(ROOT, DIRS[lang], a[lang]["slug"] + ".html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # html fields may use {up} for links back to the site root
        open(path, "w", encoding="utf-8").write(page(a, lang).replace("{up}", "" if lang == "en" else "../"))
        out.append(os.path.relpath(path, ROOT))
    return a, out


def update_sitemap(articles):
    """Rewrite the blog block of sitemap.xml from all article sources."""
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"  <!-- blog -->.*?<!-- /blog -->\n", "", s, flags=re.S)
    blocks = []
    for a in articles:
        alt = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{url(a, l)}"/>\n' for l in LANGS)
        alt += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url(a, "en")}"/>\n'
        if pl_pair(a):
            alt += f'    <xhtml:link rel="alternate" hreflang="pl" href="{a["pl"]}"/>\n'
        for l in LANGS:
            blocks.append(f"  <url>\n    <loc>{url(a, l)}</loc>\n    <lastmod>{a['modified']}</lastmod>\n{alt}"
                          f"    <image:image><image:loc>{SITE}/{a['hero']}</image:loc></image:image>\n  </url>\n")
    s = s.replace("</urlset>", "  <!-- blog -->\n" + "".join(blocks) + "  <!-- /blog -->\n</urlset>")
    open(p, "w", encoding="utf-8").write(s)


if __name__ == "__main__":
    slugs = sys.argv[1:] or sorted(f[:-5] for f in os.listdir(SRC) if f.endswith(".json"))
    for sl in slugs:
        _, files = build(sl)
        print("built", " ".join(files))
    allarts = [json.load(open(os.path.join(SRC, f), encoding="utf-8")) for f in sorted(os.listdir(SRC)) if f.endswith(".json")]
    update_sitemap(allarts)
    print("sitemap: %d articles" % len(allarts))
