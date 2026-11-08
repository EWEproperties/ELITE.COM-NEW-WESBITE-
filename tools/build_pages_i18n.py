"""German and Spanish versions of the home, About Us and Contact pages.

Usage:
  python3 tools/build_pages_i18n.py

The English pages stay the source. This script reads index.html, about-us.html and contact-us.html,
translates their texts with tools/i18n/<lang>.json, points every link at the page's own language
where that page exists (home, about, contact, blog, blog articles, town pages) and at the English
page otherwise, and writes de-de/ and es-es/. It also writes the hreflang links and the language
switcher into the English pages. Run it again after any change to the English pages.

Property titles on the cards come from eGO in English and the property pages are English only,
so the cards keep the English title until there are German and Spanish property pages.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "towns"))
import build_town as town  # noqa: E402  (language tables, blog map, town page paths)

SITE = "https://www.eliteworldestates.com"
LANGS = ("en", "de", "es")
DIRS = {"en": "", "de": "de-de/", "es": "es-es/"}
LOCALE = {"en": "en_GB", "de": "de_DE", "es": "es_ES"}
PAGES = {  # English file -> page name in each language (clean URL, no .html)
    "index.html": {"en": "", "de": "", "es": ""},
    "about-us.html": {"en": "about-us", "de": "uber-uns", "es": "acerca-de"},
    "contact-us.html": {"en": "contact-us", "de": "kontakt", "es": "contacto"},
}
TAGS = {
    "de": {"Places and developments": "Orte und Projekte", "Living in Spain": "Leben in Spanien",
           "Owning and taxes": "Eigentum und Steuern", "Buying a home": "Immobilienkauf"},
    "es": {"Places and developments": "Lugares y promociones", "Living in Spain": "Vivir en España",
           "Owning and taxes": "Propiedad e impuestos", "Buying a home": "Comprar vivienda"},
}
WORDS = {  # facts on the property cards
    "de": {"bedroom": ("Schlafzimmer", "Schlafzimmer"), "bathroom": ("Bad", "Bäder"), "unit": ("Einheit", "Einheiten"),
           "townhouse": ("Reihenhaus", "Reihenhäuser"), "from": "ab"},
    "es": {"bedroom": ("dormitorio", "dormitorios"), "bathroom": ("baño", "baños"), "unit": ("vivienda", "viviendas"),
           "townhouse": ("adosado", "adosados"), "from": "desde"},
}


def url(page, lang):
    return SITE + "/" + DIRS[lang] + page


def fix_head(s, en_file, lang):
    """hreflang for all three languages, canonical, og:url and og:locale for this one."""
    names = PAGES[en_file]
    alt = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{url(names[l], l)}">' for l in LANGS)
    alt += f'\n  <link rel="alternate" hreflang="x-default" href="{url(names["en"], "en")}">'
    s = re.sub(r'(  <link rel="alternate" hreflang="[^"]+" href="[^"]*">\n)+', alt + "\n", s, count=1)
    me = url(names[lang], lang)
    s = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{me}">', s)
    s = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{me}">', s)
    s = re.sub(r'<meta property="og:locale" content="[^"]*">', f'<meta property="og:locale" content="{LOCALE[lang]}">', s)
    return s


def switcher(s, en_file, lang):
    """The EN / PL / DE / ES links in the header."""
    up = "../" if lang != "en" else ""
    names = PAGES[en_file]

    def href(l):
        n = names[l]
        return up + DIRS[l] + (n + ".html" if n else "index.html")
    links = [f'        <a href="{href(l)}"{" class=\"active\"" if l == lang else ""} hreflang="{l}">{l.upper()}</a>' for l in LANGS]
    links.insert(1, '        <a href="https://www.eliteworldestates.pl/" hreflang="pl">PL</a>')
    return re.sub(r'<div class="lang">.*?</div>', '<div class="lang">\n' + "\n".join(links) + "\n      </div>", s, count=1, flags=re.S)


def link_map(lang, bm):
    """English file -> the file to link to from a page in de-de/ or es-es/ (relative to that folder)."""
    m = {"index.html": "index.html", "blog.html": "blog.html"}
    for en_file, names in PAGES.items():
        if names[lang]:
            m[en_file] = names[lang] + ".html"
    for en_file, b in bm.items():
        m[en_file] = b[lang]
    for f in os.listdir(os.path.join(town.HERE, "i18n", lang)):
        slug = f[:-5]
        m["properties-for-sale-in-" + slug + ".html"] = town.PREFIX[lang] + slug + ".html"
    return m


def relink(s, lang, m):
    def fix(match):
        attr, q, v = match.group(1), match.group(2), match.group(3)
        if v.startswith(("#", "http", "mailto:", "tel:", "data:", "../")) or not v:
            return match.group(0)
        path, frag = (v.split("#", 1) + [""])[:2]
        path, query = (path.split("?", 1) + [""])[:2]
        new = m.get(path, "../" + path)
        return f'{attr}={q}{new}{"?" + query if query else ""}{"#" + frag if frag else ""}{q}'
    s = re.sub(r'\b(href|src|action)=(")([^"]*)"', fix, s)
    return re.sub(r"url\((?!http|\.\./)([^)]+)\)", r"url(../\1)", s)


def facts(text, lang):
    w = WORDS[lang]

    def n(match):
        num, word = match.group(1), match.group(2)
        one = num == "1"
        return f"{num} {w[word][0 if one else 1]}"
    text = re.sub(r"(\d+(?:–\d+)?) (bedroom|bathroom|unit|townhouse)s?\b", n, text)
    return re.sub(r"\bfrom (\d+) m²", lambda x: f"{w['from']} {x.group(1)} m²", text)


def prices(s, lang):
    w = WORDS[lang]
    num = lambda v: town.money(int(v.replace(",", "")), lang)
    s = re.sub(r'<p class="price">from €([\d,]+)</p>', lambda x: f'<p class="price">{w["from"]} {num(x.group(1))}</p>', s)
    s = re.sub(r'<p class="price">€([\d,]+)</p>', lambda x: f'<p class="price">{num(x.group(1))}</p>', s)
    s = re.sub(r'(<option value="\d+">)€([\d,]+)(</option>)', lambda x: x.group(1) + num(x.group(2)) + x.group(3), s)
    s = re.sub(r'<p class="facts">(.*?)</p>', lambda x: f'<p class="facts">{facts(x.group(1), lang)}</p>', s)
    show = {"de": "Immobilie {a} von {b} zeigen", "es": "Mostrar inmueble {a} de {b}"}[lang]
    return re.sub(r'aria-label="Show property (\d+) of (\d+)"', lambda x: f'aria-label="{show.format(a=x.group(1), b=x.group(2))}"', s)


def blog_cards(s, lang, bm):
    def card(match):
        href, rest = match.group(1), match.group(2)
        if href not in bm:  # English-only article: leave it out of the German and Spanish pages
            return ""
        rest = re.sub(r'<p class="tag">(.*?)</p>', lambda t: f'<p class="tag">{TAGS[lang].get(t.group(1), t.group(1))}</p>', rest)
        rest = re.sub(r"<h3>.*?</h3>", f"<h3>{html.escape(bm[href]['h1'][lang], quote=False)}</h3>", rest, count=1)
        return f'<a class="bcard" href="{href}">{rest}</a>'
    return re.sub(r'<a class="bcard" href="([^"]+)">(.*?)</a>', card, s, flags=re.S)


def translate(s, tr):
    missing = []
    for en, xx in sorted(tr["text"].items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r'(>\s*)' + re.escape(en) + r'(\s*<)|(="|\')' + re.escape(en) + r'(")')
        if not pat.search(s):
            missing.append(en)
            continue
        s = pat.sub(lambda m: (m.group(1) or m.group(3)) + xx + (m.group(2) or m.group(4)), s)
    return s, missing


def build(en_file, lang, tr, bm, m):
    s = open(os.path.join(ROOT, en_file), encoding="utf-8").read()
    page = en_file[:-5]
    title, desc = tr["meta"][page]
    s = s.replace('<html lang="en">', f'<html lang="{lang}">', 1)
    s = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title, quote=False)}</title>", s, count=1)
    s = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*"', lambda x: x.group(1) + html.escape(desc) + '"', s)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*"', lambda x: x.group(1) + html.escape(title) + '"', s)
    s = s.replace('"inLanguage": "en"', f'"inLanguage": "{lang}"')
    s = fix_head(s, en_file, lang)
    for a, b in tr["raw"]:
        if a in s:
            s = s.replace(a, b)
    s = blog_cards(s, lang, bm)
    s = prices(s, lang)
    s, missing = translate(s, tr)
    s = relink(s, lang, m)
    s = switcher(s, en_file, lang)
    # page URLs inside the schema
    s = s.replace(f'"{SITE}/{page}"', f'"{url(PAGES[en_file][lang], lang)}"')
    out = os.path.join(ROOT, DIRS[lang] + (PAGES[en_file][lang] or "index") + ".html")
    open(out, "w", encoding="utf-8").write(s)
    return out, missing


def update_index():
    """German and Spanish pages in sitemap.xml (with their language versions) and llms.txt."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "ego"))
    from build_properties import replace_block
    today = __import__("datetime").date.today().isoformat()
    groups = [{l: url(n[l], l) for l in LANGS} for n in PAGES.values()]
    for f in sorted(os.listdir(os.path.join(town.HERE, "i18n", "de"))):
        slug = f[:-5]
        groups.append({l: SITE + "/" + town.DIRS[l] + town.PREFIX[l] + slug for l in LANGS})
    sm = []
    for g in groups:
        alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{u}"/>' for l, u in g.items())
        alts += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{g["en"]}"/>'
        for l in ("de", "es"):
            sm.append(f"  <url>\n    <loc>{g[l]}</loc>\n    <lastmod>{today}</lastmod>{alts}\n  </url>")
    replace_block(os.path.join(ROOT, "sitemap.xml"), "  <!-- i18n-pages -->", "  <!-- /i18n-pages -->", "\n".join(sm) + "\n", "  <!-- towns -->")
    names = {"de": "Deutsch", "es": "Español"}
    lines = []
    for l in ("de", "es"):
        h, ab, co = {"de": ("Startseite", "Über uns", "Kontakt"), "es": ("Inicio", "Sobre nosotros", "Contacto")}[l]
        lines.append(f"- {names[l]}: [{h}]({url('', l)}), [{ab}]({url(PAGES['about-us.html'][l], l)}), [{co}]({url(PAGES['contact-us.html'][l], l)})")
        towns = sorted(os.listdir(os.path.join(town.HERE, "i18n", l)))
        lines.append(f"- {names[l]}, town pages: " + ", ".join(
            f"[{json.load(open(os.path.join(town.HERE, f), encoding='utf-8'))['town']}]({SITE}/{town.DIRS[l]}{town.PREFIX[l]}{f[:-5]})" for f in towns))
    block = "## German and Spanish pages\n\n" + "\n".join(lines) + "\n"
    replace_block(os.path.join(ROOT, "llms.txt"), "<!-- i18n-pages -->", "<!-- /i18n-pages -->", block, "<!-- collections -->")


def main():
    bm = town.blog_map()
    for en_file in PAGES:  # English pages: language switcher and hreflang only
        p = os.path.join(ROOT, en_file)
        s = open(p, encoding="utf-8").read()
        s = fix_head(s, en_file, "en")
        s = switcher(s, en_file, "en")
        open(p, "w", encoding="utf-8").write(s)
    for lang in ("de", "es"):
        tr = json.load(open(os.path.join(ROOT, "tools", "i18n", lang + ".json"), encoding="utf-8"))
        m = link_map(lang, bm)
        unused = set(tr["text"])
        for en_file in PAGES:
            out, missing = build(en_file, lang, tr, bm, m)
            unused &= set(missing)
            print(os.path.relpath(out, ROOT))
        if unused:
            print(f"  {lang}: texts not found on any page: {sorted(unused)}")
    update_index()


if __name__ == "__main__":
    main()
