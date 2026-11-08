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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ego"))
from delivery import badge  # noqa: E402

# German and Spanish versions: tools/towns/i18n/<lang>/<town>.json holds the translated texts
# (same keys as the English file); everything else (listings, photos, town names) comes from
# the English file. Run with a language: python3 tools/towns/build_town.py torrevieja de
LANGS = ("en", "de", "es")
DIRS = {"en": "", "de": "de-de/", "es": "es-es/"}
PREFIX = {"en": "properties-for-sale-in-", "de": "immobilien-zum-verkauf-in-", "es": "inmuebles-en-venta-en-"}
LOCALE = {"en": "en_GB", "de": "de_DE", "es": "es_ES"}
HOME = {"en": "index.html", "de": "de-de/index.html", "es": "es-es/index.html"}
ABOUT = {"en": "about-us.html", "de": "de-de/uber-uns.html", "es": "es-es/acerca-de.html"}
CONTACT = {"en": "contact-us.html", "de": "de-de/kontakt.html", "es": "es-es/contacto.html"}
UI = {
    "en": dict(home="Home", props="Properties", blog="Blog", about="About Us", contact="Contact Us", menu="Open menu",
               see="See the properties", ask="Ask us about {t}", sale_now="For sale now", near_eyebrow="A short drive away",
               near_h="Near {t}: {n}", listings_h="Properties for sale in {t}", show_all="Show all {n} properties",
               city="The city", where="Where to buy", budget="Budget", costs_h="What it costs to buy in {t}",
               howto="How to buy in Spain, step by step", questions="Questions", faq_h="Buying property in {t}: questions and answers",
               from_blog="From our blog", reads_h="Read before you buy", contact_h="Looking for a home in {t}?",
               contact_p="Tell us your budget and what you need. We reply within one working day, in English, German, Spanish or Polish.",
               email="Email us", call="Call 0034 672 519 809", bed=("bedroom", "bedrooms"), bath=("bathroom", "bathrooms"),
               ref="Ref.", on_request="Price on request", legal=("Legal notice", "Privacy policy", "Cookie policy"),
               reg="Registered in the Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) no. 2321.",
               tags={}),
    "de": dict(home="Startseite", props="Immobilien", blog="Blog", about="Über uns", contact="Kontakt", menu="Menü öffnen",
               see="Immobilien ansehen", ask="Fragen zu {t}?", sale_now="Jetzt zu verkaufen", near_eyebrow="Ganz in der Nähe",
               near_h="In der Nähe von {t}: {n}", listings_h="Immobilien zum Verkauf in {t}", show_all="Alle {n} Immobilien zeigen",
               city="Die Stadt", where="Wo kaufen", budget="Budget", costs_h="Was der Kauf in {t} kostet",
               howto="Immobilienkauf in Spanien Schritt für Schritt", questions="Fragen", faq_h="Immobilienkauf in {t}: Fragen und Antworten",
               from_blog="Aus unserem Blog", reads_h="Lesen Sie vor dem Kauf", contact_h="Sie suchen ein Zuhause in {t}?",
               contact_p="Nennen Sie uns Ihr Budget und Ihre Wünsche. Wir antworten innerhalb eines Werktags, auf Deutsch, Englisch, Spanisch oder Polnisch.",
               email="E-Mail schreiben", call="Anrufen: 0034 672 519 809", bed=("Schlafzimmer", "Schlafzimmer"), bath=("Bad", "Bäder"),
               ref="Ref.", on_request="Preis auf Anfrage", legal=("Impressum", "Datenschutz", "Cookies"),
               reg="Eingetragen im Register der Immobilienvermittler der Region Valencia (RAICV) unter Nr. 2321.",
               tags={"Places": "Orte", "Buying in Spain": "Kaufen in Spanien", "Renting": "Vermieten", "Living in Spain": "Leben in Spanien"}),
    "es": dict(home="Inicio", props="Inmuebles", blog="Blog", about="Sobre nosotros", contact="Contacto", menu="Abrir menú",
               see="Ver los inmuebles", ask="Pregúntenos por {t}", sale_now="En venta ahora", near_eyebrow="Muy cerca",
               near_h="Cerca de {t}: {n}", listings_h="Inmuebles en venta en {t}", show_all="Ver los {n} inmuebles",
               city="La ciudad", where="Dónde comprar", budget="Presupuesto", costs_h="Cuánto cuesta comprar en {t}",
               howto="Cómo comprar en España, paso a paso", questions="Preguntas", faq_h="Comprar vivienda en {t}: preguntas y respuestas",
               from_blog="De nuestro blog", reads_h="Lea antes de comprar", contact_h="¿Busca casa en {t}?",
               contact_p="Cuéntenos su presupuesto y lo que necesita. Respondemos en un día laborable, en español, inglés, alemán o polaco.",
               email="Escríbanos", call="Llame al 0034 672 519 809", bed=("dormitorio", "dormitorios"), bath=("baño", "baños"),
               ref="Ref.", on_request="Precio a consultar", legal=("Aviso legal", "Privacidad", "Cookies"),
               reg="Inscrita en el Registro de Agentes de Intermediación Inmobiliaria de la Comunitat Valenciana (RAICV) con el n.º 2321.",
               tags={"Places": "Lugares", "Buying in Spain": "Comprar en España", "Renting": "Alquilar", "Living in Spain": "Vivir en España"}),
}
BLOG = {"en": "blog.html", "de": "de-de/blog.html", "es": "es-es/blog.html"}
LEGAL = {"en": ("terms-and-conditions.html", "privacy-policy.html", "cookie-policy.html")}

# The cost table rows are the same wording on every town page, so they are translated here once
COSTS = {
    "de": {"New build": "Neubau", "Resale home": "Bestandsimmobilie", "Notary, registry, lawyer": "Notar, Grundbuch, Anwalt",
           "Every year": "Jedes Jahr", "about 1.5–2.5% of the price": "ca. 1,5–2,5 % des Preises",
           "IBI property tax and community fees, which depend on the home": "Grundsteuer IBI und Gemeinschaftskosten, je nach Immobilie",
           "10% VAT (IVA) + 1.2% stamp duty (AJD)": "10 % Mehrwertsteuer (IVA) + 1,2 % Stempelsteuer (AJD)",
           "10% VAT (IVA) + 1.4% stamp duty (AJD)": "10 % Mehrwertsteuer (IVA) + 1,4 % Stempelsteuer (AJD)",
           "10% VAT (IVA) + 1.5% stamp duty (AJD)": "10 % Mehrwertsteuer (IVA) + 1,5 % Stempelsteuer (AJD)",
           "7% transfer tax (ITP)": "7 % Grunderwerbsteuer (ITP)", "7.75% transfer tax (ITP)": "7,75 % Grunderwerbsteuer (ITP)",
           "9% transfer tax (ITP), 11% above €1 million": "9 % Grunderwerbsteuer (ITP), 11 % über 1 Mio. €"},
    "es": {"New build": "Obra nueva", "Resale home": "Segunda mano", "Notary, registry, lawyer": "Notaría, registro, abogado",
           "Every year": "Cada año", "about 1.5–2.5% of the price": "aprox. 1,5–2,5 % del precio",
           "IBI property tax and community fees, which depend on the home": "IBI y gastos de comunidad, según la vivienda",
           "10% VAT (IVA) + 1.2% stamp duty (AJD)": "10 % IVA + 1,2 % AJD",
           "10% VAT (IVA) + 1.4% stamp duty (AJD)": "10 % IVA + 1,4 % AJD",
           "10% VAT (IVA) + 1.5% stamp duty (AJD)": "10 % IVA + 1,5 % AJD",
           "7% transfer tax (ITP)": "7 % ITP", "7.75% transfer tax (ITP)": "7,75 % ITP",
           "9% transfer tax (ITP), 11% above €1 million": "9 % ITP, 11 % por encima de 1 millón de €"},
}

# FAQ answers that are the same on many town pages ({t} = town), translated once
NIE = '<a href="nie-number-in-spain-what-is-it-and-how-to-get-it.html">'
FAQ_TR = {
    "de": {
        ("Can foreigners buy property in {t}?", "Yes. Anyone can buy property in Spain. You need a Spanish NIE tax number and usually a Spanish bank account, and we help you with both. See our guide to the " + NIE + "NIE number</a>."):
        ("Können Ausländer in {t} eine Immobilie kaufen?", "Ja. Jeder kann in Spanien eine Immobilie kaufen. Sie brauchen eine spanische Steuernummer (NIE) und meist ein spanisches Bankkonto, und wir helfen Ihnen bei beidem. Mehr dazu in unserem Ratgeber zur " + NIE + "NIE-Nummer</a>."),
        ("What costs are there on top of the price?", "For a new build you pay 10% VAT and 1.4% stamp duty. For a resale home you pay 9% transfer tax (11% above €1 million). Notary, land registry and legal fees add about 1.5–2.5%."):
        ("Welche Kosten kommen zum Kaufpreis hinzu?", "Bei einem Neubau zahlen Sie 10 % Mehrwertsteuer und 1,4 % Stempelsteuer. Bei einer Bestandsimmobilie zahlen Sie 9 % Grunderwerbsteuer (11 % über 1 Mio. €). Notar, Grundbuch und Anwalt kosten zusammen etwa 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In the Valencian Community you pay 10% VAT and 1.4% stamp duty on a new build, and 9% transfer tax (11% above €1 million) on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("Welche Kosten kommen zum Kaufpreis hinzu?", "In der Region Valencia zahlen Sie bei einem Neubau 10 % Mehrwertsteuer und 1,4 % Stempelsteuer, bei einer Bestandsimmobilie 9 % Grunderwerbsteuer (11 % über 1 Mio. €). Notar, Grundbuch und Anwalt kosten zusammen etwa 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In Andalusia you pay 10% VAT and 1.2% stamp duty on a new build, and 7% transfer tax on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("Welche Kosten kommen zum Kaufpreis hinzu?", "In Andalusien zahlen Sie bei einem Neubau 10 % Mehrwertsteuer und 1,2 % Stempelsteuer, bei einer Bestandsimmobilie 7 % Grunderwerbsteuer. Notar, Grundbuch und Anwalt kosten zusammen etwa 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In the Region of Murcia you pay 10% VAT and 1.5% stamp duty on a new build, and 7.75% transfer tax on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("Welche Kosten kommen zum Kaufpreis hinzu?", "In der Region Murcia zahlen Sie bei einem Neubau 10 % Mehrwertsteuer und 1,5 % Stempelsteuer, bei einer Bestandsimmobilie 7,75 % Grunderwerbsteuer. Notar, Grundbuch und Anwalt kosten zusammen etwa 1,5–2,5 %."),
    },
    "es": {
        ("Can foreigners buy property in {t}?", "Yes. Anyone can buy property in Spain. You need a Spanish NIE tax number and usually a Spanish bank account, and we help you with both. See our guide to the " + NIE + "NIE number</a>."):
        ("¿Pueden comprar vivienda los extranjeros en {t}?", "Sí. Cualquier persona puede comprar una vivienda en España. Necesita un NIE y normalmente una cuenta bancaria española, y le ayudamos con las dos cosas. Consulte nuestra guía del " + NIE + "NIE</a>."),
        ("What costs are there on top of the price?", "For a new build you pay 10% VAT and 1.4% stamp duty. For a resale home you pay 9% transfer tax (11% above €1 million). Notary, land registry and legal fees add about 1.5–2.5%."):
        ("¿Qué gastos hay además del precio?", "En obra nueva se paga un 10 % de IVA y un 1,4 % de AJD. En segunda mano se paga un 9 % de ITP (11 % por encima de 1 millón de €). Notaría, registro y abogado suman alrededor de un 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In the Valencian Community you pay 10% VAT and 1.4% stamp duty on a new build, and 9% transfer tax (11% above €1 million) on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("¿Qué gastos hay además del precio?", "En la Comunitat Valenciana se paga un 10 % de IVA y un 1,4 % de AJD en obra nueva, y un 9 % de ITP (11 % por encima de 1 millón de €) en segunda mano. Notaría, registro y abogado suman alrededor de un 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In Andalusia you pay 10% VAT and 1.2% stamp duty on a new build, and 7% transfer tax on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("¿Qué gastos hay además del precio?", "En Andalucía se paga un 10 % de IVA y un 1,2 % de AJD en obra nueva, y un 7 % de ITP en segunda mano. Notaría, registro y abogado suman alrededor de un 1,5–2,5 %."),
        ("What costs are there on top of the price?", "In the Region of Murcia you pay 10% VAT and 1.5% stamp duty on a new build, and 7.75% transfer tax on a resale home. Notary, land registry and legal fees add about 1.5–2.5%."):
        ("¿Qué gastos hay además del precio?", "En la Región de Murcia se paga un 10 % de IVA y un 1,5 % de AJD en obra nueva, y un 7,75 % de ITP en segunda mano. Notaría, registro y abogado suman alrededor de un 1,5–2,5 %."),
    },
}

COSTS_INTRO_EN = (r"On top of the price you pay tax and fees\. For a new (\w+) at €([\d,]+), for example, that is €([\d,]+) VAT "
                  r"and €([\d,]+) stamp duty, plus notary, land registry and legal fees\. Taxes on resale homes are different, "
                  r"so always ask us for the exact figure for the home you like\.")
COSTS_INTRO = {
    "de": ("Zum Kaufpreis kommen Steuern und Gebühren. Für {kind} zu {p} sind das zum Beispiel {vat} Mehrwertsteuer und {ajd} "
           "Stempelsteuer, dazu Notar, Grundbuch und Anwalt. Für Bestandsimmobilien gelten andere Steuern, fragen Sie uns also "
           "immer nach der genauen Summe für die Immobilie, die Ihnen gefällt.",
           {"apartment": "eine neue Wohnung", "villa": "eine neue Villa", "home": "eine neue Immobilie"}),
    "es": ("Al precio se suman impuestos y gastos. Para {kind} de {p}, por ejemplo, son {vat} de IVA y {ajd} de AJD, más notaría, "
           "registro y abogado. En la segunda mano los impuestos son otros, así que pídanos siempre la cifra exacta de la vivienda "
           "que le guste.",
           {"apartment": "un piso nuevo", "villa": "una villa nueva", "home": "una vivienda nueva"}),
}


def money(v, lang):
    return f"€{v:,}" if lang == "en" else f"{v:,} €".replace(",", ".")


def blog_map():
    """English article file -> German / Spanish article file, from the blog sources."""
    out = {}
    folder = os.path.join(ROOT, "tools", "blog")
    for f in os.listdir(folder):
        if f.endswith(".json"):
            a = json.load(open(os.path.join(folder, f), encoding="utf-8"))
            out[a["en"]["slug"] + ".html"] = {"de": a["de"]["slug"] + ".html", "es": a["es"]["slug"] + ".html",
                                               "h1": {l: a[l]["h1"] for l in LANGS}}
    return out


def langs_of(slug):
    return [l for l in LANGS if l == "en" or os.path.exists(os.path.join(HERE, "i18n", l, slug + ".json"))]


def page_path(c, slug, lang):
    return c["page"] if lang == "en" else DIRS[lang] + PREFIX[lang] + slug

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


def fmt_price(p, lang="en"):
    v = price_value(p)
    return money(v, lang) if v else UI[lang]["on_request"]


def clean_title(t):
    t = re.sub(r"\bapartament\b", "apartment", t, flags=re.I)
    t = re.sub(r"\bappartment\b", "apartment", t, flags=re.I)
    t = re.sub(r"\bapartmens\b", "apartments", t, flags=re.I)
    return t.strip()


def facts(d, lang="en"):
    parts = []
    beds, baths, area = d.get("ROOMS"), d.get("BATHS"), d.get("AREA")
    u = UI[lang]
    if beds and beds != "0":
        parts.append(f"{beds} {u['bed'][beds != '1']}")
    if baths and baths != "0":
        parts.append(f"{baths} {u['bath'][baths != '1']}")
    if area:
        parts.append(f"{float(area):g} m²")
    return " · ".join(parts)


def card(i, pages, lang="en"):
    up = "../" if lang != "en" else ""
    href = (up + pages[i["ref"]]) if i["ref"] in pages else f"{SITE}/property-details/{i['slug']}/{i['id']}"
    ext = "" if not href.startswith("http") else ' target="_blank" rel="noopener"'
    town = i["town"]
    return f"""        <a class="tcard" href="{href}"{ext}>
          <div class="tcard-photo"><img src="{up}{i['photo']}" alt="{e(i['alt'] or clean_title(i['title']))}" width="800" height="600" loading="lazy" decoding="async"></div>
          <div class="tcard-body">
            <p class="tcard-town">{e(town)}</p>
            <h3>{e(clean_title(i['title']))}</h3>
            <p class="tcard-price">{fmt_price(i['price'], lang)}</p>
            <p class="tcard-facts"><span>{facts(i['det'], lang)}</span><span class="tcard-refno">{UI[lang]['ref']} {i['ref']}</span></p>{badge(i['ref'], lang)}
          </div>
        </a>"""


def main(slug, lang="en"):
    c = json.load(open(os.path.join(HERE, slug + ".json"), encoding="utf-8"))
    en = dict(c)
    if lang != "en":
        c.update(json.load(open(os.path.join(HERE, "i18n", lang, slug + ".json"), encoding="utf-8")))
        if "costs" not in c or c["costs"] is en["costs"]:
            c["costs"] = [[COSTS[lang][x] for x in r] for r in en["costs"]]
        if "costs_intro" not in c or c["costs_intro"] is en["costs_intro"]:
            k, p, vat, ajd = re.fullmatch(COSTS_INTRO_EN, en["costs_intro"]).groups()
            num = lambda x: money(int(x.replace(",", "")), lang)
            tpl, kinds = COSTS_INTRO[lang]
            c["costs_intro"] = tpl.format(kind=kinds[k], p=num(p), vat=num(vat), ajd=num(ajd))
        if len(c["faq"]) < len(en["faq"]):  # the shared questions come from FAQ_TR, the town's own from the file
            own, t, faq = iter(c["faq"]), en["town"], []
            for q, a in en["faq"]:
                k = (q.replace(t, "{t}"), a.replace(t, "{t}"))
                faq.append([x.replace("{t}", t) for x in FAQ_TR[lang][k]] if k in FAQ_TR[lang] else next(own))
            c["faq"] = faq
    u, up, bm = UI[lang], ("../" if lang != "en" else ""), blog_map()
    versions = {l: SITE + "/" + page_path(en, slug, l) for l in langs_of(slug)}

    def links(text):
        """Links in the texts point to the article in the page's own language."""
        if lang == "en":
            return text
        return re.sub(r'href="([a-z0-9-]+\.html)"', lambda m: f'href="{bm[m.group(1)][lang]}"' if m.group(1) in bm
                      else f'href="../{m.group(1)}"', text)
    listings = json.load(open(os.path.join(HERE, "data", slug + "-listings.json"), encoding="utf-8"))
    pages = local_pages()
    missing = [i["id"] for i in listings if not re.fullmatch(r"EWE\d+", i.get("ref", ""))]
    if missing:  # every card must show its reference number
        sys.exit(f"Listings without an EWE reference: {missing}")
    town_names = c["town_names"]  # eGO municipality -> display name
    for i in listings:
        i["town"] = town_names.get(i["loc"][-1], i["loc"][-1])
        # eGO titles that were written in another language, until they are fixed in eGO
        i["title"] = c.get("title_fixes", {}).get(i["ref"], i["title"])
        for word, name in c.get("title_towns", {}).items():  # e.g. inland golf resorts inside a coastal municipality
            if word in i["title"]:
                i["town"] = name
        i["photo"] = f"assets/towns/{slug}/listings/{i['id']}.jpg"
    key = lambda i: (price_value(i["price"]) is None, price_value(i["price"]) or 0)
    city = sorted([i for i in listings if i["town"] == c["town"]], key=key)
    near = sorted([i for i in listings if i["town"] != c["town"]], key=key)
    prices = [price_value(i["price"]) for i in city if price_value(i["price"])]
    low = min(prices)
    url = versions[lang]
    coast = c.get("coast", "Costa Blanca")  # breadcrumb level 2
    coast_url = SITE + "/" + c.get("coast_slug", "properties-for-sale-in-costa-blanca")
    # "coast": "" leaves out the middle breadcrumb (no hub page yet, e.g. Costa Cálida)
    crumbs = [(u["home"], SITE + "/" + ("" if lang == "en" else DIRS[lang]))] + ([(coast, coast_url)] if coast else []) + [(c["town"], url)]
    coast_crumb = f'<a href="{up}{coast_url.replace(SITE + "/", "")}.html">{e(coast)}</a> <span>/</span> ' if coast else ""
    page_file = page_path(en, slug, lang) + ".html"

    def fill(s):
        return links(s.replace("{count}", str(len(city))).replace("{count_all}", str(len(listings)))
                     .replace("{from}", money(low, lang)).replace("{near_count}", str(len(near))))

    # Schema: breadcrumb, the page with its listings, FAQ
    item_list = [{"@type": "ListItem", "position": n + 1,
                  "url": (SITE + "/" + pages[i["ref"]]) if i["ref"] in pages else f"{SITE}/property-details/{i['slug']}/{i['id']}",
                  "name": clean_title(i["title"])} for n, i in enumerate(city + near)]
    schema = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": n + 1, "name": name, "item": link}
            for n, (name, link) in enumerate(crumbs)]},
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": fill(c["h1"]), "url": url,
         "description": fill(c["description"]), "inLanguage": lang,
         "about": {"@type": "City", "name": c["town"], "containedInPlace": {"@type": "AdministrativeArea", "name": c.get("province", "Province of Alicante")}},
         "publisher": {"@type": "RealEstateAgent", "name": "Elite World Estates", "url": SITE},
         "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", fill(a))}}
            for q, a in c["faq"]]},
    ]

    areas = "\n".join(f"""        <div class="t-area">
          <h3>{e(a['name'])}</h3>
          <p>{links(a['text'])}</p>
        </div>""" for a in c["areas"])
    # photos under a Creative Commons licence must name the author and the licence
    credit = "".join(f'\n        <figcaption class="t-credit">{cr}</figcaption>' for cr in c.get("photo_credits", []))
    from PIL import Image
    gw, gh = Image.open(os.path.join(ROOT, "assets", "towns", slug, c["guide_photo"])).size
    guide = "\n".join(f"        <p>{fill(p)}</p>" for p in c["guide"])
    costs = "\n".join(f"          <tr><th scope=\"row\">{r[0]}</th><td>{r[1]}</td></tr>" for r in c["costs"])

    def read(r):
        href, title = r["href"], r["title"]
        if lang != "en" and href in bm:
            href, title = bm[href][lang], bm[href]["h1"][lang]
        elif lang != "en":
            href = "../" + href
        return href, title
    faq = "\n".join(f"""      <details>
        <summary>{e(q)}</summary>
        <p>{fill(a)}</p>
      </details>""" for q, a in c["faq"])
    reads = "\n".join(f"""      <a class="t-read" href="{read(r)[0]}">
        <img src="{up}{r['img']}" alt="" width="960" height="540" loading="lazy" decoding="async">
        <span class="tag">{u['tags'].get(r['tag'], r['tag'])}</span>
        <h3>{e(read(r)[1])}</h3>
      </a>""" for r in en["reads"])
    facts_band = "\n".join(f'      <li><strong>{fill(v)}</strong><span>{fill(k)}</span></li>' for v, k in c["facts"])
    near_names = ", ".join(c.get("near_towns", []))
    near_block = f"""
  <section class="t-section t-near">
    <div class="container">
      <div class="section-head">
        <div>
          <p class="eyebrow dark">{u['near_eyebrow']}</p>
          <h2>{e(u['near_h'].format(t=c['town'], n=near_names))}</h2>
          <p class="lead">{fill(c.get('near_intro', ''))}</p>
        </div>
      </div>
      <div class="t-grid" data-limit="12">
{chr(10).join(card(i, pages, lang) for i in near)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline t-more" hidden>{u['show_all'].format(n=len(near))}</button></div>
    </div>
  </section>
""" if near else ""

    alternates = "\n".join(f'  <link rel="alternate" hreflang="{l}" href="{v}">' for l, v in versions.items())
    alternates += f'\n  <link rel="alternate" hreflang="x-default" href="{versions["en"]}">'
    switcher = "\n".join(f'        <a href="{up}{page_path(en, slug, l)}.html"{" class=\"active\"" if l == lang else ""} hreflang="{l}">{l.upper()}</a>'
                         for l in versions)
    hb = "how-to-buy-an-apartment-or-house-in-spain.html"
    howto = bm[hb][lang] if lang != "en" and hb in bm else up + hb
    legal = " · ".join(f'<a href="{up}{f}">{t}</a>' for f, t in zip(LEGAL["en"], u["legal"]))
    out = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{e(fill(c['title']))}</title>
  <meta name="description" content="{e(fill(c['description']))}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{url}">
{alternates}
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:locale" content="{LOCALE[lang]}">
  <meta property="og:title" content="{e(fill(c['title']))}">
  <meta property="og:description" content="{e(fill(c['description']))}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE}/assets/towns/{slug}/hero.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{up}assets/logo.png" type="image/png">
  <link rel="stylesheet" href="{up}css/style.css">
  <script type="application/ld+json">
{json.dumps(schema, ensure_ascii=False, indent=1)}
  </script>
</head>
<body>

<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="{up}{HOME[lang]}" aria-label="Elite World Estates – {u['home']}">
      <img src="{up}assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="{u['menu']}" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="Main">
      <a href="{up}{HOME[lang]}">{u['home']}</a>
      <a href="{up}properties-for-sale-in-spain.html" class="active">{u['props']}</a>
      <a href="{up}{BLOG[lang]}">{u['blog']}</a>
      <a href="{up}{ABOUT[lang]}">{u['about']}</a>
      <a href="{up}{CONTACT[lang]}">{u['contact']}</a>
      <div class="lang">
{switcher}
        <a href="https://eliteworldestates.pl" hreflang="pl">PL</a>
      </div>
    </nav>
  </div>
</header>

<main class="town-page">
  <section class="t-hero" style="background-image:url({up}assets/towns/{slug}/hero.jpg)">
    <div class="container">
      <nav class="t-crumbs" aria-label="Breadcrumb"><a href="{up}{HOME[lang]}">{u['home']}</a> <span>/</span> {coast_crumb}{e(c['town'])}</nav>
      <p class="t-kicker">{e(c['kicker'])}</p>
      <h1>{e(fill(c['h1']))}</h1>
      <p class="t-lead">{fill(c['lead'])}</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="#listings">{u['see']}</a>
        <a class="btn t-btn-light" href="#contact">{e(u['ask'].format(t=c['town']))}</a>
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
          <p class="eyebrow dark">{u['sale_now']}</p>
          <h2>{e(c.get('listings_title', u['listings_h'].format(t=c['town'])))}</h2>
          <p class="lead">{fill(c['listings_intro'])}</p>
        </div>
      </div>
      <div class="t-grid" data-limit="12">
{chr(10).join(card(i, pages, lang) for i in city)}
      </div>
      <div class="t-more-wrap"><button type="button" class="btn t-btn-outline t-more" hidden>{u['show_all'].format(n=len(city))}</button></div>
    </div>
  </section>
{near_block}
  <section class="t-section t-guide">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">{u['city']}</p>
        <h2>{e(c['guide_title'])}</h2>
{guide}
      </div>
      <figure class="t-figure">
        <img class="t-photo" src="{up}assets/towns/{slug}/{c['guide_photo']}" alt="{e(c['guide_photo_alt'])}" width="{gw}" height="{gh}" loading="lazy" decoding="async">{credit}
      </figure>
    </div>
  </section>

  <section class="t-section">
    <div class="container">
      <p class="eyebrow dark">{u['where']}</p>
      <h2>{e(c['areas_title'])}</h2>
      <div class="t-areas">
{areas}
      </div>
    </div>
  </section>

  <section class="t-section t-costs">
    <div class="container t-split">
      <div class="t-text">
        <p class="eyebrow dark">{u['budget']}</p>
        <h2>{e(u['costs_h'].format(t=c['town']))}</h2>
        <p>{fill(c['costs_intro'])}</p>
        <p><a class="link-more" href="{howto}">{u['howto']} &rarr;</a></p>
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
      <p class="eyebrow dark">{u['questions']}</p>
      <h2>{e(u['faq_h'].format(t=c['town']))}</h2>
{faq}
    </div>
  </section>

  <section class="t-section">
    <div class="container">
      <p class="eyebrow dark">{u['from_blog']}</p>
      <h2>{u['reads_h']}</h2>
      <div class="t-reads">
{reads}
      </div>
    </div>
  </section>

  <section class="t-contact" id="contact">
    <div class="container">
      <h2>{e(u['contact_h'].format(t=c['town']))}</h2>
      <p>{u['contact_p']}</p>
      <div class="t-actions">
        <a class="btn btn-gold" href="mailto:info@eliteworldestates.com?subject={e(c['town'])}%20property">{u['email']}</a>
        <a class="btn t-btn-outline" href="tel:+34672519809">{u['call']}</a>
        <a class="btn t-btn-outline" href="https://wa.me/34672519809" target="_blank" rel="noopener">WhatsApp</a>
      </div>
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="{up}{HOME[lang]}">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>{u['reg']}</p>
    <p class="footer-legal">{legal}</p>
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="{up}js/main.js"></script>
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
    print(f"{page_file}: {len(city)} in {c['town']}, {len(near)} nearby, from {money(low, lang)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "alicante", sys.argv[2] if len(sys.argv) > 2 else "en")
