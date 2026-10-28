"""Sample: move the resale template pages into elite.com (resale/ folder + hub page).

Reads the resale template files (SRC) and writes elite.com pages into OUT.
"""
import html, json, re, shutil, sys
from pathlib import Path

SRC = Path(sys.argv[1])            # resale template files
REPO = Path(sys.argv[2])           # elite.com repo
OUT = Path(sys.argv[3])            # where the merged site is written
HUB = "resale-properties-for-sale-in-spain"
WWW = "https://www.eliteworldestates.com"
NAV_LABEL = "Resale properties"


def header(p, active):
    def a(href, label, key):
        cls = ' class="active"' if key == active else ""
        return f'      <a href="{p}{href}"{cls}>{label}</a>\n'
    return (
        '<header class="site-header" id="top">\n  <div class="container header-inner">\n'
        f'    <a class="logo" href="{p}index.html" aria-label="Elite World Estates – Home">\n'
        f'      <img src="{p}assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">\n'
        '    </a>\n    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false">&#9776;</button>\n'
        '    <nav class="main-nav" aria-label="Main">\n'
        + a("index.html", "Home", "home")
        + a("index.html#featured", "New builds", "new")
        + a(f"{HUB}.html", NAV_LABEL, "resale")
        + a("blog.html", "Blog", "blog")
        + a("about-us.html", "About Us", "about")
        + '      <a href="#contact">Contact Us</a>\n'
        '    </nav>\n  </div>\n</header>'
    )


def footer(p):
    return (
        '<footer class="site-footer">\n  <div class="container footer-bottom">\n'
        f'    <p><a href="{p}index.html">Elite World Estates</a> · <a href="{p}{HUB}.html">{NAV_LABEL}</a> · '
        '<a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>\n'
        '    <p>Resale descriptions are based on information supplied by the owner. The Nota Simple and the purchase contract are binding.</p>\n'
        '    <p>Registered in the Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) no. 2321.</p>\n'
        '    <p>&copy; <span id="year"></span> Elite World Estates</p>\n  </div>\n</footer>'
    )


def common(s, p):
    s = re.sub(r'<header class="site-header".*?</header>', lambda m: header(p, "resale"), s, count=1, flags=re.S)
    s = re.sub(r'<footer class="site-footer">.*?</footer>', lambda m: footer(p), s, count=1, flags=re.S)
    # absolute URLs
    s = s.replace("https://resale.eliteworldestates.com/properties.html", f"{WWW}/{HUB}")
    s = s.replace("https://resale.eliteworldestates.com/properties/", f"{WWW}/resale/")
    s = s.replace("https://resale.eliteworldestates.com/assets/listings/", f"{WWW}/assets/resale/")
    s = s.replace("https://resale.eliteworldestates.com/assets/agents/", f"{WWW}/assets/about/")
    s = s.replace("https://resale.eliteworldestates.com/", f"{WWW}/")
    s = s.replace("Elite World Estates Resale", "Elite World Estates")
    s = s.replace('value="EWE Resale: ', 'value="Resale enquiry: ')
    return s


def fix_property(s):
    s = common(s, "../")
    s = s.replace('href="../properties/', 'href="')
    s = s.replace("../assets/listings/", "../assets/resale/")
    s = s.replace("../assets/agents/", "../assets/about/")
    s = s.replace('href="../properties.html?area=costa-blanca"', f'href="../{HUB}.html"')
    s = s.replace('href="../properties.html"', f'href="../{HUB}.html"')
    s = s.replace(f'<a href="../{HUB}.html">Properties</a>', f'<a href="../{HUB}.html">{NAV_LABEL}</a>')
    s = s.replace('"name": "Properties",', f'"name": "{NAV_LABEL}",')
    # one Costa Blanca crumb would point to the hub twice: drop it
    s = s.replace(f' <span>/</span> <a href="../{HUB}.html">Costa Blanca</a>', "")
    s = s.replace('<p class="eyebrow dark">For sale · ', '<p class="eyebrow dark">Resale · ')
    return s


def fix_hub(s, intro):
    s = common(s, "")
    s = s.replace('href="properties/', 'href="resale/')
    s = s.replace('"assets/listings/', '"assets/resale/')
    s = re.sub(r"<title>.*?</title>", "<title>Resale Properties for Sale in Spain | Elite World Estates</title>", s)
    desc = ("Resale villas, apartments and townhouses for sale on the Costa Blanca: hand-picked second-hand homes "
            "you can move into now, checked by the Elite World Estates team.")
    s = re.sub(r'(<meta name="description" content=")[^"]*', r"\g<1>" + desc, s)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*', r"\g<1>" + desc, s)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*', r"\g<1>Resale Properties for Sale in Spain", s)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{WWW}/{HUB}">', s)
    s = re.sub(r'(<meta property="og:url" content=")[^"]*', rf"\g<1>{WWW}/{HUB}", s)
    s = re.sub(r'<header class="listings-head">.*?</header>', intro, s, count=1, flags=re.S)
    return s


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(REPO, OUT, ignore=shutil.ignore_patterns(".git", "cache"))
    (OUT / "resale").mkdir()
    shutil.copytree(SRC / "assets" / "listings", OUT / "assets" / "resale")
    shutil.copy(SRC / "assets" / "hero.jpg", OUT / "assets" / "resale" / "hero.jpg")
    for f in sorted((SRC / "properties").glob("*.html")):
        (OUT / "resale" / f.name).write_text(fix_property(f.read_text()))
    intro = (Path(__file__).parent / "hub_intro.html").read_text()
    hub = fix_hub((SRC / "properties.html").read_text(), intro)
    hub = hub.replace("</main>", (Path(__file__).parent / "hub_after.html").read_text() + "\n</main>", 1)
    (OUT / f"{HUB}.html").write_text(hub)
    shutil.copy(SRC / "js" / "filters.js", OUT / "js" / "filters.js")
    shutil.copy(Path(__file__).parent / "enquiry.js", OUT / "js" / "enquiry.js")
    shutil.copy(Path(__file__).parent / "resale.css", OUT / "css" / "resale.css")
    print("pages:", len(list((OUT / "resale").glob("*.html"))))


main()


CARD = re.compile(
    r'<a class="card" href="properties/(?P<slug>[^"]+)"[^>]*data-town="(?P<town>[^"]+)".*?'
    r'<img src="assets/listings/(?P<ref>[^/]+)/01\.jpg" alt="(?P<alt>[^"]*)".*?'
    r'<span class="badge">(?P<type>[^<]*)</span>.*?<p class="price">(?P<price>[^<]*)</p>.*?'
    r'<p class="card-town">(?P<tname>[^<]*)</p>.*?<h3>(?P<title>[^<]*)</h3>.*?<p class="facts">(?P<facts>[^<]*)</p>',
    re.S)


def resale_cards(town_slugs, limit):
    src = (SRC / "properties.html").read_text()
    out = []
    for m in CARD.finditer(src):
        if m["town"] in town_slugs:
            out.append(
                f'        <a class="tcard" href="resale/{m["slug"]}">\n'
                f'          <div class="tcard-photo"><img src="assets/resale/{m["ref"]}/01.jpg" alt="{m["alt"]}" width="640" height="480" loading="lazy" decoding="async"><span class="tcard-ref">Resale</span></div>\n'
                f'          <div class="tcard-body">\n            <p class="tcard-town">{m["tname"]}</p>\n            <h3>{m["title"]}</h3>\n'
                f'            <p class="tcard-price">{m["price"]}</p>\n'
                f'            <p class="tcard-facts"><span>{m["facts"]}</span><span class="tcard-refno">Ref. {m["ref"]}</span></p>\n          </div>\n        </a>\n')
    return out[:limit], len(out)


def nav_items(s):
    """Rename Properties -> New builds and add the resale item after it."""
    return re.sub(r'<a href="(?:index\.html)?#properties"( class="active")?>Properties</a>',
                  f'<a href="index.html#featured">New builds</a>\n      <a href="{HUB}.html">{NAV_LABEL}</a>',
                  s, count=1)


def patch_home():
    f = OUT / "index.html"
    s = nav_items(f.read_text())
    tiles = f'''
<section class="coasts choose">
  <div class="container">
    <div class="coasts-head">
      <p class="eyebrow dark">New build or resale?</p>
      <h2>Two ways to buy, one team</h2>
    </div>
    <div class="coasts-grid">
      <a class="coast" href="#featured" style="background-image:url(assets/costa-blanca.jpg)">
        <span class="coast-inner"><span class="coast-kicker">Straight from the developer</span><span class="coast-name">New builds</span><span class="coast-towns">Modern homes, 10-year guarantee</span><span class="coast-link">See new builds &rarr;</span></span>
      </a>
      <a class="coast" href="{HUB}.html" style="background-image:url(assets/towns/altea/hero.jpg)">
        <span class="coast-inner"><span class="coast-kicker">Ready to move into</span><span class="coast-name">Resale properties</span><span class="coast-towns">Hand-picked second-hand homes</span><span class="coast-link">See resale homes &rarr;</span></span>
      </a>
    </div>
  </div>
</section>
'''
    s = s.replace('<section class="coasts">', tiles + '\n<section class="coasts">', 1)
    f.write_text(s)


def patch_town(page, town_slugs, town_name):
    f = OUT / page
    s = nav_items(f.read_text())
    cards, total = resale_cards(town_slugs, 6)
    more = (f'<p class="t-more-wrap"><a class="btn t-btn-outline" href="{HUB}.html?town={town_slugs[0]}">'
            f'See all {total} resale homes in {town_name}</a></p>')
    block = f'''
  <section class="t-section t-resale" id="resale">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">Resale · ready to move into</p>
          <h2>Resale homes in {town_name}</h2>
          <p class="lead">Hand-picked second-hand homes in {town_name}, checked by our team: owner, debts and licences.</p>
        </div>
      </div>
      <div class="t-grid">
{"".join(cards)}      </div>
      {more}
    </div>
  </section>
'''
    s = s.replace('  <section class="t-section t-near">', block + '\n  <section class="t-section t-near">', 1)
    f.write_text(s)


patch_home()
patch_town("properties-for-sale-in-altea.html", ["altea"], "Altea")
