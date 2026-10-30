"""Build the Polish blog (pl-pl/) from tools/blog-pl/.

Usage: python3 tools/build_blog_pl.py

The Polish articles are written for Polish buyers and are not translations
of the EN/DE/ES articles, so they have their own source: one body file per
article (tools/blog-pl/<slug>.html, as written for the old eGO editor) and
tools/blog-pl/articles.json with title, description, author, dates, photo
and "en" (the matching article in tools/blog, used for hreflang both ways).
Pages keep the live eGO addresses (/pl-pl/<slug>). The script also builds
pl-pl/blog.html and the <!-- blog-pl --> block of sitemap.xml.
"""
import json
import os
import re

import build_blog as bb
import build_blog_index as bi

ROOT, SITE, esc = bb.ROOT, bb.SITE, bb.esc
SRC = os.path.join(ROOT, "tools", "blog-pl")
OUT = os.path.join(ROOT, "pl-pl")

UI = dict(home="Strona główna", props="Nieruchomości", blog="Blog", about="O nas", contact="Kontakt", menu="Otwórz menu",
          main="Menu główne", crumbs="Ścieżka nawigacji", by="Autor:", updated="aktualizacja", read="min czytania",
          contents="Spis treści", faq="Najczęstsze pytania", author="O autorce",
          reg="Agencja wpisana do rejestru pośredników nieruchomości Regionu Walencji (RAICV) pod nr 2321.",
          months=["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
                  "października", "listopada", "grudnia"])
ROLE = "Doradca ds. nieruchomości"
BIO = {
    "anita": "Założycielka Elite World Estates. Od 2018 roku pomaga Polakom kupować domy i mieszkania na Costa Blanca i Costa del Sol.",
    "lucyna": "Pomaga klientom znaleźć dom na Costa Blanca i Costa del Sol i pisze o życiu w Hiszpanii.",
    "aleksandra": "Prowadzi klientów przez cały zakup w Hiszpanii, od pierwszego oglądania do notariusza.",
}
TOPIC = dict(buying="Kupno nieruchomości", owning="Własność i podatki", living="Życie w Hiszpanii", places="Miejsca i inwestycje")
IDX = dict(title="Blog: kupno nieruchomości i życie w Hiszpanii | Elite World Estates",
           desc="Praktyczne, sprawdzone poradniki o zakupie nieruchomości w Hiszpanii, podatkach, życiu na miejscu i najlepszych miejscach na Costa Blanca i Costa del Sol.",
           eyebrow="Blog Elite World Estates", h1="Kupno, własność i życie w Hiszpanii",
           lead="Poradniki naszych doradczyń z Costa Blanca i Costa del Sol, pisane z myślą o Polakach. Każdy artykuł jest sprawdzony i aktualny na 2026 rok.",
           all="Wszystkie artykuły", latest="Najnowszy artykuł", read_more="Przeczytaj artykuł", count="Artykuły: {n}",
           more="Pokaż więcej artykułów (jeszcze {n})", cta_h="Szukasz domu w Hiszpanii?",
           cta_p="Napisz, czego szukasz, a wyślemy Ci pasujące oferty.", cta_b="Napisz do nas")

# Live eGO pages that the new site replaces with its own pages
TOWNS = {"alicante", "altea", "benidorm", "calpe", "cumbre-del-sol", "javea", "orihuela-costa", "torrevieja"}
PAGE_LINKS = {"kontakt": "../index.html#contact", "o-nas": "../about-us.html", "blog": "blog.html"}


def load():
    arts = json.load(open(os.path.join(SRC, "articles.json"), encoding="utf-8"))
    for slug, a in arts.items():
        a["slug"] = slug
        a["body"] = open(os.path.join(SRC, slug + ".html"), encoding="utf-8").read()
        a["topic"] = bi.TOPIC_OF.get(a["topic_of"], "buying")
        a["en_json"] = json.load(open(os.path.join(bb.SRC, a["en"] + ".json"), encoding="utf-8")) if a["en"] else None
    return arts


def redirects():
    """Old /pl-pl/ address -> new one, for merged and removed articles."""
    out = {}
    for line in open(os.path.join(ROOT, "tools", "redirects.csv"), encoding="utf-8").read().splitlines()[1:]:
        old, new = line.split(",")[:2]
        if old.startswith("/pl-pl/"):
            out[old[7:]] = new[7:]
    return out


def fix_link(target, arts, moved):
    target = moved.get(target, target)
    if target in arts:
        return target + ".html"
    if target in PAGE_LINKS:
        return PAGE_LINKS[target]
    town = target.replace("nieruchomosci-na-sprzedaz-w-", "")
    if town in TOWNS:
        return f"../properties-for-sale-in-{town}.html"
    return "../index.html#properties"  # coast, luxury and golf listing pages


def slugify(t):
    t = bb.strip_tags(t).lower()
    t = t.translate(str.maketrans("ąćęłńóśźżáéíóúñ", "acelnoszzaeioun"))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def clean(body, arts, moved):
    """Turn the eGO body (inline styles) into site markup; split off the FAQ."""
    b = re.sub(r'<div style="border-left[^"]*">\s*<p><strong>W skrócie</strong></p>', '<div class="in-short">\n<p><strong>W skrócie</strong></p>', body)
    b = re.sub(r'<div style="overflow-x:auto[^"]*">', '<div class="tablewrap">', b)
    b = re.sub(r'<table style="[^"]*">', '<table class="compare-table">', b)
    b = re.sub(r'<p style="font-size:14px[^"]*">', '<p class="small-print">', b)
    b = re.sub(r' style="[^"]*"', "", b)
    b = re.sub(r'href="/pl-pl/([^"#]+)"', lambda m: f'href="{fix_link(m.group(1), arts, moved)}"', b)
    head, _, faq = b.partition("<h2>Najczęstsze pytania</h2>")
    qa = re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", faq, re.S)
    tail = re.split(r"<h3>.*?</h3>\s*<p>.*?</p>", faq, flags=re.S)[-1].strip()
    # ids for the table of contents
    secs = []

    def h2(m):
        i = slugify(m.group(1))
        secs.append((i, m.group(1)))
        return f'<h2 id="{i}">{m.group(1)}</h2>'
    head = re.sub(r"<h2>(.*?)</h2>", h2, head)
    return head.strip(), secs, qa, tail


def nice_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {UI['months'][m - 1]} {y}"


def url(a):
    return f"{SITE}/pl-pl/{a['slug']}"


def header(up, langs, active_blog=True):
    return f'''<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="{up}index.html" aria-label="Elite World Estates – {UI["home"]}">
      <img src="{up}assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="{UI["menu"]}" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="{UI["main"]}">
      <a href="{up}index.html">{UI["home"]}</a>
      <a href="{up}index.html#properties">{UI["props"]}</a>
      <a href="blog.html" class="active">{UI["blog"]}</a>
      <a href="{up}about-us.html">{UI["about"]}</a>
      <a href="{up}index.html#contact">{UI["contact"]}</a>
      <div class="lang">
        {langs}
      </div>
    </nav>
  </div>
</header>'''


FOOTER = f'''<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="../index.html">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>{UI["reg"]}</p>
    <p class="footer-legal">{bb.legal_links("../", "pl")}</p>
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>'''


def head_tags(title, desc, canon, alts, og_type, image):
    return f'''  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{canon}">
{alts}
  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{canon}">
  <meta property="og:image" content="{SITE}/{image}">
  <meta property="og:locale" content="pl_PL">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="../assets/logo.png" type="image/png">
  <link rel="stylesheet" href="../css/style.css">'''


def page(a, arts, moved):
    au = bb.AUTHORS[a["author"]]
    canon = url(a)
    body, secs, qa, tail = clean(a["body"], arts, moved)
    minutes = max(3, round(len(bb.strip_tags(a["body"]).split()) / 200))
    e = a["en_json"]
    if e:
        alts = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{bb.url(e, l)}">' for l in bb.LANGS)
        alts += f'\n  <link rel="alternate" hreflang="pl" href="{canon}">\n  <link rel="alternate" hreflang="x-default" href="{bb.url(e, "en")}">'
        langs = "\n        ".join(f'<a href="../{bb.DIRS[l]}{e[l]["slug"]}.html" hreflang="{l}">{l.upper()}</a>' for l in bb.LANGS)
    else:
        alts = ""
        langs = "\n        ".join(f'<a href="../{bb.DIRS[l]}blog.html" hreflang="{l}">{l.upper()}</a>' for l in bb.LANGS)
    langs += '\n        <a href="blog.html" class="active" hreflang="pl">PL</a>'
    ld = [
        {"@context": "https://schema.org", "@type": "BlogPosting", "@id": canon + "#article", "mainEntityOfPage": canon,
         "headline": a["h1"], "description": a["description"], "image": f"{SITE}/{a['hero']}",
         "datePublished": a["published"], "dateModified": a["modified"], "inLanguage": "pl",
         "author": {"@type": "Person", "name": au["name"], "jobTitle": ROLE, "image": f"{SITE}/{au['photo']}",
                    "url": f"{SITE}/about-us.html", "worksFor": {"@id": f"{SITE}/#organization"}},
         "publisher": {"@id": f"{SITE}/#organization"}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": UI["home"], "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": UI["blog"], "item": f"{SITE}/pl-pl/blog"},
            {"@type": "ListItem", "position": 3, "name": a["h1"], "item": canon}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": bb.strip_tags(q), "acceptedAnswer": {"@type": "Answer", "text": bb.strip_tags(ans)}} for q, ans in qa]},
        {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": f"{SITE}/#organization", "name": "Elite World Estates",
         "url": f"{SITE}/", "logo": f"{SITE}/assets/logo.png", "telephone": "+34 672 519 809", "email": "info@eliteworldestates.com"},
    ]
    toc = ""
    if len(secs) >= 4:
        items = "\n".join(f'            <li><a href="#{i}">{t}</a></li>' for i, t in secs)
        toc = f'''        <nav class="toc" aria-label="{UI["contents"]}">
          <p class="toc-title">{UI["contents"]}</p>
          <ol>
{items}
          </ol>
        </nav>
'''
    # table of contents goes after the summary box and the intro paragraph
    m = re.match(r'(<div class="in-short">.*?</div>\s*(?:<p>.*?</p>\s*)?)(.*)', body, re.S)
    body = m.group(1) + "\n" + toc + m.group(2) if m else toc + body
    faq = "\n".join(f"          <details><summary>{q}</summary><p>{ans}</p></details>" for q, ans in qa)
    pub, mod = a["published"], a["modified"]
    upd = f' · {UI["updated"]} <time datetime="{mod}">{nice_date(mod)}</time>' if mod != pub else ""
    return f'''<!doctype html>
<html lang="pl">
<head>
{head_tags(a["title"], a["description"], canon, alts, "article", a["hero"])}
  <meta property="article:published_time" content="{pub}">
  <meta property="article:modified_time" content="{mod}">
  <meta property="article:author" content="{au["name"]}">
  <link rel="preload" as="image" href="../{a["hero"]}" fetchpriority="high">
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
</head>
<body>

{header("../", langs)}

<main class="article-page">
  <div class="container article-wrap">
    <nav class="breadcrumb" aria-label="{UI["crumbs"]}">
      <a href="../index.html">{UI["home"]}</a> <span>/</span> <a href="blog.html">{UI["blog"]}</a> <span>/</span> <span aria-current="page">{a["h1"].split(" – ")[0]}</span>
    </nav>

    <article class="post">
      <header class="post-head">
        <p class="eyebrow">{TOPIC[a["topic"]]}</p>
        <h1>{a["h1"]}</h1>
        <p class="byline">
          <img src="../{au["photo"]}" alt="" width="48" height="48">
          <span>{UI["by"]} <a href="../about-us.html">{au["name"]}</a> · <time datetime="{pub}">{nice_date(pub)}</time>{upd} · {minutes} {UI["read"]}</span>
        </p>
      </header>

      <figure class="post-hero">
        <img src="../{a["hero"]}" alt="{esc(a["hero_alt"])}" width="1280" height="720" fetchpriority="high">
      </figure>

      <div class="post-body">
{body}

        <h2 id="najczestsze-pytania">{UI["faq"]}</h2>
        <div class="faq">
{faq}
        </div>

        {tail}

        <aside class="author-box" aria-label="{UI["author"]}">
          <img src="../{au["photo"]}" alt="{au["name"]}, {ROLE} – Elite World Estates" width="96" height="96" loading="lazy">
          <div>
            <p class="author-name">{au["name"]}</p>
            <p>{ROLE} – Elite World Estates. {BIO[a["author"]]}</p>
            <p><a href="tel:{au["tel"]}">{au["phone"]}</a> · <a href="mailto:{au["email"]}">{au["email"]}</a></p>
          </div>
        </aside>
      </div>
    </article>
  </div>
</main>

{FOOTER}

<script src="../js/main.js"></script>
</body>
</html>
'''


def card(a, big=False):
    au = bb.AUTHORS[a["author"]]
    mins = max(3, round(len(bb.strip_tags(a["body"]).split()) / 200))
    hd = "h2" if big else "h3"
    load = 'fetchpriority="high"' if big else 'loading="lazy" decoding="async"'
    img = a["hero"] if big else a["thumb"]
    more = f'\n        <span class="blog-more">{IDX["read_more"]} &rarr;</span>' if big else ""
    return f'''    <article class="blog-card{" blog-feature" if big else ""}" data-topic="{a["topic"]}">
      <a href="{a["slug"]}.html">
        <img src="../{img}" alt="" width="{1280 if big else 960}" height="{720 if big else 540}" {load}>
        <div class="blog-card-body">
          <p class="tag">{TOPIC[a["topic"]]}</p>
          <{hd}>{esc(a["h1"])}</{hd}>
          <p class="blog-excerpt">{esc(a["description"])}</p>
          <p class="blog-meta"><img src="../{au["photo"]}" alt="" width="28" height="28" loading="lazy"> {au["name"]} · <time datetime="{a["published"]}">{nice_date(a["published"])}</time> · {mins} {UI["read"]}</p>{more}
        </div>
      </a>
    </article>'''


def index(arts):
    own = sorted(arts.values(), key=lambda a: a["published"], reverse=True)
    for a in own:
        a["thumb"] = bi.thumb(a["hero"], a["topic_of"])
    feat, rest = own[0], own[1:]
    canon = f"{SITE}/pl-pl/blog"
    alts = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{SITE}/{bb.DIRS[l]}blog">' for l in bb.LANGS)
    alts += f'\n  <link rel="alternate" hreflang="pl" href="{canon}">\n  <link rel="alternate" hreflang="x-default" href="{SITE}/blog">'
    langs = "\n        ".join(f'<a href="../{bb.DIRS[l]}blog.html" hreflang="{l}">{l.upper()}</a>' for l in bb.LANGS)
    langs += '\n        <a href="blog.html" class="active" hreflang="pl">PL</a>'
    chips = f'<button type="button" class="chip active" data-topic="all">{IDX["all"]}</button>' + "".join(
        f'<button type="button" class="chip" data-topic="{k}">{v}</button>' for k, v in TOPIC.items())
    ld = [
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": IDX["h1"], "description": IDX["desc"],
         "url": canon, "inLanguage": "pl", "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(own), "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": url(a), "name": a["h1"]} for i, a in enumerate(own)]}},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": UI["home"], "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": UI["blog"], "item": canon}]},
    ]
    # reuse the English index page, swapping in the Polish parts
    en = bi.page(bi.load(), "en")
    script = en[en.index("<script>"):]
    new = f'label = {json.dumps(IDX["count"], ensure_ascii=False)}, moreLabel = {json.dumps(IDX["more"], ensure_ascii=False)};'
    script = re.sub(r"label = .*?, moreLabel = .*?;", lambda m: new, script)
    cards = "\n".join(card(a) for a in rest)
    return f'''<!DOCTYPE html>
<html lang="pl">
<head>
{head_tags(IDX["title"], IDX["desc"], canon, alts, "website", feat["hero"])}
  <script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
  </script>
</head>
<body>

{header("../", langs)}

<main class="blog-page">
  <div class="container">
    <nav class="breadcrumb" aria-label="{UI["crumbs"]}">
      <a href="../index.html">{UI["home"]}</a> <span>/</span> <span aria-current="page">{UI["blog"]}</span>
    </nav>
    <header class="blog-head">
      <p class="eyebrow">{IDX["eyebrow"]}</p>
      <h1>{IDX["h1"]}</h1>
      <p class="lead">{IDX["lead"]}</p>
    </header>

    <p class="eyebrow blog-label">{IDX["latest"]}</p>
{card(feat, big=True)}

    <div class="blog-filter" role="group" aria-label="{UI["blog"]}">
      {chips}
    </div>
    <p class="blog-count" aria-live="polite">{IDX["count"].format(n=len(rest))}</p>

    <div class="blog-grid">
{cards}
    </div>
    <div class="blog-more-wrap"><button type="button" class="btn blog-show-more" hidden></button></div>

    <section class="blog-cta">
      <h2>{IDX["cta_h"]}</h2>
      <p>{IDX["cta_p"]}</p>
      <a class="btn btn-gold" href="../index.html#contact">{IDX["cta_b"]}</a>
    </section>
  </div>
</main>

{FOOTER}

<script src="../js/main.js"></script>
{script}'''


def update_sitemap(arts):
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"  <!-- blog-pl -->.*?<!-- /blog-pl -->\n", "", s, flags=re.S)
    blocks = []
    for a in arts.values():
        alt = ""
        if a["en_json"]:
            alt = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{bb.url(a["en_json"], l)}"/>\n' for l in bb.LANGS)
            alt += f'    <xhtml:link rel="alternate" hreflang="pl" href="{url(a)}"/>\n'
            alt += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{bb.url(a["en_json"], "en")}"/>\n'
        blocks.append(f"  <url>\n    <loc>{url(a)}</loc>\n    <lastmod>{a['modified']}</lastmod>\n{alt}"
                      f"    <image:image><image:loc>{SITE}/{a['hero']}</image:loc></image:image>\n  </url>\n")
    alt = "".join(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{SITE}/{bb.DIRS[l]}blog"/>\n' for l in bb.LANGS)
    alt += f'    <xhtml:link rel="alternate" hreflang="pl" href="{SITE}/pl-pl/blog"/>\n    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/blog"/>\n'
    blocks.append(f"  <url>\n    <loc>{SITE}/pl-pl/blog</loc>\n    <lastmod>{max(a['modified'] for a in arts.values())}</lastmod>\n{alt}  </url>\n")
    s = s.replace("</urlset>", "  <!-- blog-pl -->\n" + "".join(blocks) + "  <!-- /blog-pl -->\n</urlset>")
    open(p, "w", encoding="utf-8").write(s)


if __name__ == "__main__":
    arts = load()
    moved = redirects()
    os.makedirs(OUT, exist_ok=True)
    for a in arts.values():
        open(os.path.join(OUT, a["slug"] + ".html"), "w", encoding="utf-8").write(page(a, arts, moved))
    open(os.path.join(OUT, "blog.html"), "w", encoding="utf-8").write(index(arts))
    update_sitemap(arts)
    print("built %d Polish articles + pl-pl/blog.html" % len(arts))
