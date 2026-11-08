#!/usr/bin/env python3
"""301s for every address in the OLD eGO website's sitemap (all four languages).

Input:  tools/old-site/sitemap-<lang>.txt  - the live sitemap of 2026-11-08, one path per line.
        The four files are in the same order, so line N is the same page in every language.
Output: tools/old-site/redirects.csv       - read by tools/build_cloudflare.py.

Run after the property, town and blog generators, before tools/build_cloudflare.py:
    python3 tools/old-site/build_old_site_redirects.py

How the old addresses are covered
- Property pages, any language, any title slug:
      /property-details/<slug>/<id>  (and /de-de/details-der-immobilie/..., /es-es/detalles-del-inmueble/...,
      /pl-pl/szczegoly-oferty/...)  ->  /property-details/<id>  ->  new property page.
  These are 4 "dynamic" rules, so a title edited in eGO (which changes the old slug) is still caught,
  exactly like the old site, which ignores the slug and reads only the id.
  /property-details/<id> -> new page comes from tools/ego/redirects.csv (one line per listing).
  A listing that is in the old sitemap but no longer on the new site goes to its town page or the search page.
- Old town/type lists /<lang>/immobilien/<x> etc.: dynamic rule to the English /properties/<x>
  (already redirected), plus static lines where the language slug differs from the English one.
- Every other old page: the English page at the same line, or its German/Spanish version when the
  new site has one (taken from the page's hreflang links). MANUAL below covers old pages with no new twin.
"""
import csv
import json
import os
import re
import unicodedata
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LANGS = ["en-gb", "de-de", "es-es", "pl-pl"]
HREFLANG = {"de-de": "de", "es-es": "es", "pl-pl": "pl"}
SEARCH = "/properties-for-sale-in-spain"


def town_search(town):
    return SEARCH + "?town=" + urllib.parse.quote_plus(town)


# Old English pages that have no page or redirect on the new site yet.
MANUAL = {
    "/properties-for-sale-in-gran-alacant": town_search("Gran Alacant"),
    "/properties-for-sale-in-moraira": town_search("Moraira"),
    "/gran-alacant": town_search("Gran Alacant"),
    "/moraira": town_search("Moraira"),
    "/benahavis": town_search("Benahavís"),
    "/benalmadena": town_search("Benalmádena"),
    "/manilva": town_search("Manilva"),
    "/torremolinos": "/properties-for-sale-in-costa-del-sol",
    "/puerto-banus": "/properties-for-sale-in-marbella",
    "/blog-page-2": "/blog",
    "/blog-page-3": "/blog",
    "/blog-page-4": "/blog",
    "/blog-page-5": "/blog",
    "/blog-page-6": "/blog",
    "/articles": "/blog",
    "/blogs": "/blog",  # old blog category list (/blogs?catids=...)
    "/winner-luxury-lifestyle-awards-2024": "/about-us",
    "/test-la-mata": "/properties-for-sale-in-torrevieja",
    "/apartments-for-sale-las-higuericas-torre-de-la-horadada": town_search("Pilar de la Horadada"),
    "/apartments-private-pool-for-sale-pilar-de-la-horadada": town_search("Pilar de la Horadada"),
    "/tourist-apartments-for-sale-mil-palmeras": town_search("Mil Palmeras"),
    "/apartments-for-sale-santa-pola-near-beach": "/properties-for-sale-in-santa-pola",
    "/new-apartments-for-sale-in-el-raso-guardamar-del-segura": "/properties-for-sale-in-guardamar-del-segura",
    "/apartments-for-sale-guardamar-del-segura": "/properties-for-sale-in-guardamar-del-segura",
    "/apartments-for-sale-pool-spa-guardamar-del-segura": "/properties-for-sale-in-guardamar-del-segura",
    "/modern-apartment-for-sale-700m-from-the-beach-in-la-mata-torrevieja": "/properties-for-sale-in-torrevieja",
    # Polish-language article about when to visit Alicante.
    "/news-detail/chciabys-odwiedzic-alicante-ale-cay-czas-szukasz-najbardziej-dogodnego-momentu--nie-czekaj-duzej/20416": "/weather-in-alicante",
}
# Old pages per language whose best target is not the English twin.
MANUAL_LANG = {
    "/pl-pl": "/pl-pl/blog",
}

# Older property address forms seen in Search Console; all end in the listing id.
OLD_FORMS = ["/property/:slug/:id", "/Property/:id", "/Property-details/:id", "/Propertydetails/:id",
             "/propertydetails/:slug/:id", "/en-gb/propertydetails/:slug/:id", "/Inmueble/:id",
             "/pl-pl/szczegoy-oferty/:slug/:id", "/de-de/details-der-immobilie/:id",
             "/es-es/detalles-del-inmueble/:id", "/pl-pl/szczegoly-oferty/:id"]
# Other old addresses from the Search Console export. Broken fragments (/en-, /pl-pl/sz) stay 404.
GSC_PAGES = {
    "/de-de/golfimmobilien-zum-verkauf-in-costa-blanca": "/golf-properties-for-sale-in-costa-blanca",
    "/es-es/propiedades-de-golf-en-venta-en-costa-blanca": "/golf-properties-for-sale-in-costa-blanca",
    "/pl-pl/apartamenty-na-sprzedarz-w-la-mata-torrevieja": "/properties-for-sale-in-torrevieja",
    "/pl-pl/nieruchomoci-na-sprzeda-w-costa-blanca": "/properties-for-sale-in-costa-blanca",
    "/pl-pl/numer-nie-w-hiszpanii-co-to-jest-i-jak-go-wyrobi-w-polsce":
        "/pl-pl/numer-nie-w-hiszpanii-co-to-jest-i-jak-go-wyrobic-w-polsce",
    "/pl-pl/polityka-plik%C3%B3w-cookie": "/cookie-policy",
    "/pl-pl/polityka-plików-cookie": "/cookie-policy",
    "/it-it/immobili/javeaxabia": "/properties-for-sale-in-javea",
}

PROPERTY_PREFIX = {"en-gb": "/property-details", "de-de": "/de-de/details-der-immobilie",
                   "es-es": "/es-es/detalles-del-inmueble", "pl-pl": "/pl-pl/szczegoly-oferty"}
LIST_PREFIX = {"de-de": "/de-de/immobilien", "es-es": "/es-es/inmuebles", "pl-pl": "/pl-pl/nieruchomosci"}


def page_file(path):
    p = urllib.parse.unquote(path.split("?")[0]).strip("/")
    for cand in ([p + ".html", os.path.join(p, "index.html")] if p else ["index.html"]):
        full = os.path.join(ROOT, cand)
        if os.path.isfile(full):
            return full
    return None


def load_rules():
    rules = {}
    for name in ("tools/redirects.csv", "tools/towns/redirects.csv", "tools/ego/redirects.csv"):
        full = os.path.join(ROOT, name)
        if os.path.exists(full):
            with open(full, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if row.get("from") and row.get("to"):
                        rules[row["from"].strip().rstrip("/")] = re.sub(r"\.html(?=$|[?#])", "", row["to"].strip())
    return rules


def resolve_en(path, rules):
    """The new address for an old English path, or None."""
    if page_file(path):
        return path
    return rules.get(path.rstrip("/")) or MANUAL.get(path)


def lang_twin(target, lang):
    """German/Spanish/Polish version of a new English page, taken from its hreflang links."""
    f = page_file(target)
    if not f or "?" in target:
        return target
    html = open(f, encoding="utf-8").read()
    m = re.search(r'<link rel="alternate" hreflang="%s" href="https://www\.eliteworldestates\.com([^"]*)"' % HREFLANG[lang], html)
    return m.group(1) if m else target


def slugify(text):
    text = text.replace("&#x27;", "")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def search_towns():
    """Town names offered by the property search filter, keyed by slug."""
    html = open(os.path.join(ROOT, SEARCH.lstrip("/") + ".html"), encoding="utf-8").read()
    m = re.search(r'id="f-town".*?</select>', html, re.S)
    names = re.findall(r'<option value="([^"]+)"', m.group(0)) if m else []
    return {slugify(n): n.replace("&#x27;", "'") for n in names}


def fallback_for_listing(slug, town_pages, towns):
    """A removed listing goes to its town page, else the search filtered on its town, else the search."""
    slug = "-" + slug.lower() + "-"
    for town in sorted(town_pages, key=len, reverse=True):
        if "-" + town + "-" in slug:
            return "/properties-for-sale-in-" + town
    for key in sorted(towns, key=len, reverse=True):
        if "-" + key + "-" in slug:
            return town_search(towns[key])
    return SEARCH


def main():
    # Redirects can't match a query string, so /blogs?catids=... is handled as /blogs.
    rows = [[p.split("?")[0] for p in open(os.path.join(HERE, f"sitemap-{l}.txt"), encoding="utf-8").read().split()]
            for l in LANGS]
    assert len({len(r) for r in rows}) == 1, "language sitemaps are not the same length"
    rules = load_rules()
    town_pages = [f[len("properties-for-sale-in-"):-5] for f in os.listdir(ROOT)
                  if f.startswith("properties-for-sale-in-") and f.endswith(".html")]
    out, missing = [], []

    # 1. Property pages: dynamic rules (any slug), plus listings that left the site.
    for lang in LANGS:
        out.append((PROPERTY_PREFIX[lang] + "/:slug/:id", "/property-details/:id", "property, any title slug"))
    # Older address forms Google still tries (Search Console "Not found (404)" export of 2026-11-08).
    for src in OLD_FORMS:
        out.append((src, "/property-details/:id", "older property address form"))
    # Listings that left the site: the old sitemap plus the Search Console export give their ids and slugs.
    towns = search_towns()
    gsc = open(os.path.join(HERE, "gsc-not-found-2026-11-08.txt"), encoding="utf-8").read().split()
    removed = {}
    for path in [p for r in rows for p in r] + gsc:
        m = re.match(r"^/(?:[^/]+/)*?([^/]*?)/?(\d{6,})$", path)
        if not m or not re.search(r"propert|immobilie|inmueble|oferty|oferta", path, re.I):
            continue
        pid, slug = m.group(2), m.group(1)
        if "/property-details/" + pid in rules:
            continue
        target = fallback_for_listing(slug, town_pages, towns)
        if pid not in removed or removed[pid] == SEARCH:
            removed[pid] = target
    for pid, target in sorted(removed.items()):
        out.append(("/property-details/" + pid, target, "listing no longer on the site"))
    # New-site property pages of listings removed from eGO later (sold or withdrawn). slugs.json keeps
    # every address ever given out, so a missing page means the listing has gone: send it to its town.
    slugs_path = os.path.join(ROOT, "tools", "ego", "slugs.json")
    if os.path.exists(slugs_path):
        for ref, slug in sorted(json.load(open(slugs_path, encoding="utf-8")).items()):
            if not os.path.isfile(os.path.join(ROOT, "properties", slug + ".html")):
                out.append(("/properties/" + slug, fallback_for_listing(slug, town_pages, towns),
                            f"{ref} removed from eGO"))
    for src, dst in GSC_PAGES.items():
        out.append((src, dst, "old page in Search Console"))

    # 2. Old town/type lists in other languages.
    for lang in LIST_PREFIX:
        out.append((LIST_PREFIX[lang] + "/:name", "/properties/:name", "old town/type list"))

    for i, en in enumerate(rows[0]):
        if en.startswith("/property-details/"):
            continue
        target = resolve_en(en, rules)
        if en.startswith("/properties/"):
            # Static line only where the language slug differs from the English one.
            for li, lang in enumerate(LANGS[1:], 1):
                path = rows[li][i]
                if path.rsplit("/", 1)[1] != en.rsplit("/", 1)[1]:
                    out.append((path, target or SEARCH, "old type list"))
            continue
        if target is None:
            missing.append(en)
            continue
        if target != en:
            out.append((en, target, "old page"))
        for li, lang in enumerate(LANGS[1:], 1):
            path = rows[li][i]
            if page_file(path) or path.rstrip("/") in rules:
                continue
            out.append((path, MANUAL_LANG.get(path) or lang_twin(target, lang), "old page"))

    # Any other old id: the property search (kept last, after every listing's own line).
    out.append(("/property-details/:id", SEARCH, "unknown old listing id"))

    seen, final = set(), []
    for src, dst, why in out:
        if src not in seen and src != dst:
            seen.add(src)
            final.append((src, dst, why))
    with open(os.path.join(HERE, "redirects.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["from", "to", "reason"])
        w.writerows(final)
    print(f"old-site redirects: {len(final)} lines written to tools/old-site/redirects.csv")
    if missing:
        print("NO TARGET for these old pages (add them to MANUAL):")
        for p in missing:
            print("  " + p)


if __name__ == "__main__":
    main()
