"""Build static property pages from the eGO listings in tools/ego/cache/.

Usage:
  python3 tools/ego/build_properties.py                  # every cached listing
  python3 tools/ego/build_properties.py --local-photos   # also copy photos into assets/listings/<id>/

Run fetch_ego.py first. For each listing this writes properties/<slug>.html in the
same layout as the hand-made Mutxamel page, with the eGO description kept as written.
It also refreshes:
  - the properties block of sitemap.xml and llms.txt
  - feeds/properties.json and feeds/properties.xml (all listings, for Letaido and others)
  - tools/ego/redirects.csv (old eGO addresses -> new pages, for launch)

Hand-made pages are never overwritten: a page is only replaced if it carries the
generator marker below. Generated pages whose listing has left eGO are removed.
Photos stay on eGO's image server by default (13,000+ photos are too many for the repo).
"""
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request
from datetime import date
from xml.sax.saxutils import escape as xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(ROOT, "properties")
SITE = "https://www.eliteworldestates.com"
MARKER = '<meta name="generator" content="ego-build">'
TODAY = date.today().isoformat()

TEAM = {
    "Anita Orlowska": {"name": "Anita Orłowska", "photo": "anita-orlowska.jpg", "phone": "+34 672 519 809",
                       "tel": "+34672519809", "email": "anita@eliteworldestates.com"},
    "Lucyna Gacek": {"name": "Lucyna Gacek", "photo": "lucyna-gacek.jpg", "phone": "+34 604 335 323",
                     "tel": "+34604335323", "email": "lucy@eliteworldestates.com"},
    "Aleksandra Kobus": {"name": "Aleksandra Kobus", "photo": "aleksandra-kobus.jpg", "phone": "+34 672 519 809",
                         "tel": "+34672519809", "email": "info@eliteworldestates.com"},
}
DEFAULT_AGENT = "Anita Orlowska"

# Province (eGO "District") -> coast and buying taxes.
# new: AJD stamp duty on a new build (plus 10% IVA). resale: ITP transfer tax, (rate, over 1M rate).
REGIONS = {
    "Valencian Community": {"provinces": ("Alicante", "Valencia", "Castellón"), "ajd": 1.4, "itp": (9, 11)},
    "Andalusia": {"provinces": ("Málaga", "Cádiz", "Almería", "Granada"), "ajd": 1.2, "itp": (7, 7)},
    "Region of Murcia": {"provinces": ("Murcia",), "ajd": 1.5, "itp": (7.75, 7.75)},
}
COASTS = {"Alicante": ("Costa Blanca", "costa-blanca"), "Valencia": ("Costa Blanca", "costa-blanca"),
          "Murcia": ("Costa Cálida", "costa-blanca"), "Almería": ("Costa de Almería", "costa-del-sol"),
          "Málaga": ("Costa del Sol", "costa-del-sol"), "Cádiz": ("Costa del Sol", "costa-del-sol"),
          "Granada": ("Costa Tropical", "costa-del-sol")}
APARTMENT_TYPES = ("Apartment", "Penthouse", "Ground floor", "Duplex", "Studio", "Flat")
PLURAL_TITLE = re.compile(r"\b(apartments|villas|townhouses|town houses|homes|houses|penthouses|bungalows|duplexes|"
                          r"properties|residences|chalets)\b", re.I)
# The closing "arrange a viewing / disclaimer" text is replaced by the page's own
VIEWING_TAIL = re.compile(r"^(arrange your viewing|a (personal )?(visit|viewing) (says|speaks|will tell))", re.I)
ICON_PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>'
ICON_MAIL = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18v14H3z" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M3 6l9 7 9-7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
ICON_WA = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.2A9.8 9.8 0 0 0 3.6 17l-1.4 4.8 4.9-1.3A9.8 9.8 0 1 0 12 2.2zm0 17.8a8 8 0 0 1-4.1-1.1l-.3-.2-2.9.8.8-2.8-.2-.3A8 8 0 1 1 12 20zm4.4-6c-.2-.1-1.4-.7-1.7-.8s-.4-.1-.5.1-.6.8-.8 1-.3.2-.5.1a6.5 6.5 0 0 1-3.2-2.8c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5a.9.9 0 0 0-.7.3 2.8 2.8 0 0 0-.9 2.1 4.9 4.9 0 0 0 1 2.6 11.2 11.2 0 0 0 4.3 3.8c1.6.7 2.2.7 3 .6a2.6 2.6 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .1-1.2c0-.1-.2-.2-.4-.3z"/></svg>'

e = lambda s: html.escape(str(s), quote=True)


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def euro(n):
    return "€{:,.0f}".format(n)


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0
    return int(f) if f == int(f) else f


# ---------- eGO listing -> plain listing ----------

def features(raw):
    """eGO feature tree -> {"features": [...], "views": [...], "nearby": [...], "extras": {...}}."""
    out = {"features": [], "views": [], "nearby": [], "extras": {}}

    def walk(items, group):
        for x in items or []:
            if x.get("Childs"):
                walk(x["Childs"], x["Title"])
                continue
            t, v = x["Title"].strip(), (x.get("Value") or "").strip()
            if group in ("Rooms", "Areas") and v:
                continue  # bedrooms, bathrooms and areas come from their own fields
            if group == "Extras":
                if v:
                    out["extras"][t] = v
            elif t.startswith("View to "):
                out["views"].append(t[8:].capitalize())
            elif group == "Surroundings":
                out["nearby"].append(t)
            else:
                out["features"].append(t if not v or v in ("1", "0") else f"{t}: {v}")
    walk(raw, "")
    return out


def listing(p, pl_links):
    title = (p.get("Title") or "").strip() or f"{p['Type']} for sale in {p['Municipality']}"
    price = p["PropertyBusiness"][0]["Prices"][0]["PriceValue"] if p.get("PropertyBusiness") else 0
    agents = [a["AgentName"] for a in p.get("PropertyAgents") or [] if a.get("AgentName") in TEAM]
    photos = [{"big": im.get("Thumbnail_1280X1024") or im["Thumbnail"], "small": im.get("Thumbnail_640X480") or im["Thumbnail"],
               "alt": (im.get("AlternativeText") or im.get("Description") or "").strip()} for im in p.get("Images") or []]
    region = next((r for r, d in REGIONS.items() if p.get("District") in d["provinces"]), None)
    return {
        "id": p["ID"], "ref": p.get("Reference") or "", "title": title, "slug": slugify(title),
        "old_slug": slugify(p.get("Title") or ""),
        "type": p.get("Type") or "Property", "new": p.get("Condition") != "Used",
        "from": bool(PLURAL_TITLE.search(title)),
        "town": p.get("Municipality") or "", "area": (p.get("Parish") or "").strip(), "province": p.get("District") or "",
        "region": region, "coast": COASTS.get(p.get("District"), ("Spain", ""))[0],
        "coast_path": COASTS.get(p.get("District"), ("", ""))[1],
        "lat": p.get("GPSLat") or None, "lon": p.get("GPSLon") or None,
        "price": price, "beds": p.get("Rooms") or 0, "baths": p.get("Bathrooms") or 0,
        "built": num(p.get("GrossArea")), "usable": num(p.get("NetArea")), "plot": num(p.get("LandArea")),
        "floor": p["Floor"] if p.get("Floor", -1) >= 0 and p.get("Type") in APARTMENT_TYPES else None,
        "year": p.get("Year") or None,
        "energy": (p.get("EnergyCertification") or "").strip(),
        "feat": features(p.get("Features")),
        "description": (p.get("Description") or "").replace("\r", ""),
        "photos": photos, "agent": agents[0] if agents else DEFAULT_AGENT,
        "created": (p.get("CreatedDate") or TODAY)[:10], "modified": (p.get("LastModified") or TODAY)[:10],
        "pl": pl_links.get(str(p["ID"])),
    }


# ---------- description text -> HTML ----------

def is_heading(line, nxt):
    if line.endswith(":") and len(line) <= 60:
        return True
    if "|" in line and len(line) <= 110:
        return True
    return (len(line) <= 70 and not re.search(r"[.!?,;:]$", line) and ":" not in line
            and nxt is not None and len(nxt) > 90)


def is_title(line):
    words = [w for w in line.split() if len(w) > 3]
    return len(line) <= 40 and bool(words) and all(w[0].isupper() for w in words) and not re.search(r"\d", line)


def description_html(text):
    """Keep eGO's wording; only add structure: headings, lists and paragraphs."""
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    lead = lines.pop(0) if lines and len(lines[0]) <= 120 else None
    for i, l in enumerate(lines):
        if VIEWING_TAIL.match(l):
            lines = lines[:i]
            break
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        # three or more short lines in a row read as a list (e.g. "Key Features")
        run = 0
        while i + run < len(lines) and len(lines[i + run]) <= 90 and not lines[i + run].endswith((".", ":")):
            run += 1
        # a title-like line just before or after the list is its heading ("Key Features", "Location")
        if run >= 3 and is_title(l):
            out.append(f"<h3>{e(l)}</h3>")
            i += 1
            continue
        if run >= 4 and is_title(lines[i + run - 1]):
            run -= 1
        if run >= 3:
            out.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in lines[i:i + run]) + "</ul>")
            i += run
        elif is_heading(l, nxt):
            out.append(f"<h3>{e(re.sub(r'\s*:$', '', l))}</h3>")
            i += 1
        else:
            out.append(f"<p>{e(l)}</p>")
            i += 1
    return lead, "\n        ".join(out)


def plain_text(text):
    lead, body = description_html(text)
    body = re.sub(r"<[^>]+>", "\n", body)
    return "\n".join([lead or ""] + [html.unescape(x) for x in body.split("\n") if x.strip()]).strip()


# ---------- page parts ----------

def price_text(L):
    return ("From " if L["from"] else "") + euro(L["price"])


def type_label(L):
    return L["type"].lower().replace("chalet", "villa")


def summary(L):
    """Short factual sentence for meta description, schema and feeds."""
    bits = []
    if L["beds"]:
        bits.append(f"{L['beds']} bedroom{'s' if L['beds'] != 1 else ''}")
    if L["baths"]:
        bits.append(f"{L['baths']} bathroom{'s' if L['baths'] != 1 else ''}")
    if L["built"]:
        bits.append(f"{L['built']} m² built")
    if L["plot"]:
        bits.append(f"{L['plot']:,} m² plot")
    f = [x.lower() for x in L["feat"]["features"]]
    if "swimming pool" in f:
        bits.append("pool")
    elif "shared swimming pool" in f:
        bits.append("communal pool")
    if "Sea" in L["feat"]["views"]:
        bits.append("sea views")
    kind = ("New build " if L["new"] else "") + type_label(L)
    s = f"{kind[0].upper() + kind[1:]} for sale in {L['town']}, {L['province']}: {', '.join(bits)}. {price_text(L)}."
    return s if len(s) <= 160 else s[:157].rsplit(" ", 1)[0] + "…"


def costs(L):
    """Rows of the buying-cost table and a note, or None where we have no regional rates."""
    r = REGIONS.get(L["region"])
    if not r or not L["price"]:
        return None
    p = L["price"]
    if L["new"]:
        rows = [(f"IVA (VAT) on a new build from the developer: 10%", p * 0.10),
                (f"AJD stamp duty ({L['region']}): {r['ajd']:g}%", p * r["ajd"] / 100)]
        note = ("When you buy new from a developer you pay IVA and AJD, not the ITP transfer tax that applies to resale homes.")
    else:
        rate = r["itp"][1] if p > 1_000_000 else r["itp"][0]
        rows = [(f"ITP transfer tax on a resale home ({L['region']}): {rate:g}%", p * rate / 100)]
        note = "A resale home is taxed with ITP transfer tax instead of IVA."
        if r["itp"][0] != r["itp"][1]:
            note += f" In the {L['region']} ITP is {r['itp'][0]:g}%, or {r['itp'][1]:g}% for homes over €1,000,000."
    return rows, p + sum(v for _, v in rows), note


def faq(L, agent):
    c = costs(L)
    q = []
    if c:
        rows, total, _ = c
        taxes = " and ".join(t.split(" (")[0].split(":")[0] for t, _ in rows)
        q.append(("What does it cost to buy, including taxes?",
                  f"The price is {price_text(L)}. With {taxes} the total is about {euro(total)}, "
                  f"plus notary, land registry and lawyer, usually 1.5–2.5% of the price."))
    q.append(("Do I pay an agency fee?", "No. The buyer pays no agency commission when buying through Elite World Estates."))
    where = f"{L['town']}, in the province of {L['province']}"
    if L["coast"] != "Spain":
        where += f" on the {L['coast']}"
    q.append(("Where is the property?", f"In {where}, Spain."))
    size = [f"{L['beds']} bedrooms" if L["beds"] else "", f"{L['baths']} bathrooms" if L["baths"] else "",
            f"{L['built']} m² built area" if L["built"] else "", f"{L['usable']} m² usable area" if L["usable"] else "",
            f"a {L['plot']:,} m² plot" if L["plot"] else ""]
    size = [s for s in size if s]
    if size:
        q.append(("How big is it?", "It has " + ", ".join(size[:-1]) + (" and " if len(size) > 1 else "") + size[-1] + "."))
    q.append(("Can I see it or have a video call?",
              f"Yes. Call or WhatsApp {agent['name']} on {agent['phone']} and we will arrange a viewing or a video call "
              f"at a time that suits you. Please quote reference {L['ref']}."))
    return q


def schema(L, url, agent, faqs):
    imgs = [ph["big"] for ph in L["photos"][:10]]
    amen = [{"@type": "LocationFeatureSpecification", "name": f, "value": True} for f in L["feat"]["features"][:15]]
    home = {
        "@type": "Apartment" if L["type"] in APARTMENT_TYPES else "SingleFamilyResidence",
        "name": L["title"],
        "numberOfBedrooms": L["beds"] or None, "numberOfBathroomsTotal": L["baths"] or None,
        "floorSize": {"@type": "QuantitativeValue", "value": L["built"], "unitCode": "MTK"} if L["built"] else None,
        "amenityFeature": amen or None,
        "address": {"@type": "PostalAddress", "addressLocality": L["town"], "addressRegion": L["province"], "addressCountry": "ES"},
        "geo": {"@type": "GeoCoordinates", "latitude": L["lat"], "longitude": L["lon"]} if L["lat"] else None,
    }
    data = [
        {"@context": "https://schema.org", "@type": "RealEstateListing", "@id": url + "#listing", "url": url,
         "name": L["title"], "description": summary(L), "datePosted": L["created"], "dateModified": L["modified"],
         "image": imgs,
         "offers": {"@type": "Offer", "price": L["price"], "priceCurrency": "EUR", "availability": "https://schema.org/InStock",
                    "businessFunction": "https://purl.org/goodrelations/v1#Sell",
                    "seller": {"@id": SITE + "/#organization"},
                    "offeredBy": {"@type": "Person", "name": agent["name"], "jobTitle": "Property Adviser",
                                  "telephone": agent["phone"], "email": agent["email"],
                                  "image": f"{SITE}/assets/about/{agent['photo']}", "worksFor": {"@id": SITE + "/#organization"}}},
         "mainEntity": {k: v for k, v in home.items() if v is not None},
         "identifier": L["ref"]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": f"Properties in {L['coast']}", "item": f"{SITE}/{L['coast_path']}"},
            {"@type": "ListItem", "position": 3, "name": L["title"], "item": url}]},
        {"@context": "https://schema.org", "@type": "RealEstateAgent", "@id": SITE + "/#organization",
         "name": "Elite World Estates", "url": SITE + "/", "logo": SITE + "/assets/logo.png",
         "telephone": "+34 672 519 809", "email": "info@eliteworldestates.com",
         "sameAs": ["https://www.facebook.com/EliteWorldEstates", "https://www.instagram.com/eliteworldestates/",
                    "https://www.youtube.com/@eliteworldestates"]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": qq, "acceptedAnswer": {"@type": "Answer", "text": a}} for qq, a in faqs]},
    ]
    return json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")


def photo_alt(L, i):
    alt = L["photos"][i]["alt"]
    return alt if alt and i == 0 else (f"{alt} – photo {i + 1}" if alt else f"{L['title']} – photo {i + 1}")


def gallery(L, src):
    n = len(L["photos"])
    if not n:
        return ""
    badge = "New build" if L["new"] else "Resale"
    out = [f'<a href="{src(0, "big")}" class="gallery-main photo" data-i="0"><img src="{src(0, "big")}" alt="{e(photo_alt(L, 0))}" '
           f'width="1280" height="960" fetchpriority="high"><span class="photo-badge">{badge}</span><span class="photo-count">1 / {n}</span></a>']
    row = []
    for i in (1, 2):
        if i < n:
            row.append(f'<a href="{src(i, "big")}" class="photo" data-i="{i}"><img src="{src(i, "small")}" alt="{e(photo_alt(L, i))}" width="640" height="480"></a>')
    if n > 3:
        row.append(f'<button class="photo gallery-more" type="button" data-all><img src="{src(3, "small")}" alt="" width="640" height="480"><span>View all {n} photos</span></button>')
    if row:
        out.append('<div class="gallery-row">\n        ' + "\n        ".join(row) + "\n      </div>")
    return '<section class="gallery" aria-label="Photos">\n      ' + "\n      ".join(out) + "\n    </section>"


def all_photos(L, src):
    rows, i, n = [], 0, len(L["photos"])
    while i < n:
        size = 1 if (len(rows) % 2 == 0 or i == n - 1) else 2
        cells = "".join(f'<a href="{src(j, "big")}" class="photo" data-i="{j}"><img src="{src(j, "big")}" alt="{e(photo_alt(L, j))}" '
                        f'width="1280" height="960" loading="lazy" decoding="async"></a>' for j in range(i, i + size))
        rows.append(f'<div class="ap-row {"one" if size == 1 else "two"}">{cells}</div>')
        i += size
    return "\n      ".join(rows)


def key_facts(L):
    f = []
    if L["beds"]:
        f.append((L["beds"], "Bedrooms"))
    if L["baths"]:
        f.append((L["baths"], "Bathrooms"))
    if L["built"]:
        f.append((f"{L['built']} m²", "Built area"))
    if L["usable"]:
        f.append((f"{L['usable']} m²", "Usable area"))
    if L["plot"]:
        f.append((f"{L['plot']:,} m²", "Plot"))
    return "\n      ".join(f"<li><strong>{e(v)}</strong><span>{k}</span></li>" for v, k in f)


def info_list(L):
    loc = ", ".join(x for x in (L["area"] if L["area"] not in ("", "Centro", L["town"]) else "", L["town"]) if x)
    rows = [("Price", price_text(L) + " (no agency fee for the buyer)"),
            ("Type", type_label(L).capitalize() + (", new build" if L["new"] else ", resale")),
            ("Location", f"{loc} ({L['province']})" + (f", {L['coast']}" if L["coast"] != "Spain" else ""))]
    if L["beds"]:
        rows.append(("Bedrooms", L["beds"]))
    if L["baths"]:
        rows.append(("Bathrooms", L["baths"]))
    if L["built"]:
        rows.append(("Built area", f"{L['built']} m²"))
    if L["usable"]:
        rows.append(("Usable area", f"{L['usable']} m²"))
    if L["plot"]:
        rows.append(("Plot", f"{L['plot']:,} m²"))
    if L["floor"] is not None:
        rows.append(("Floor", "Ground floor" if L["floor"] == 0 else L["floor"]))
    if L["year"]:
        rows.append(("Year built", L["year"]))
    if L["feat"]["views"]:
        rows.append(("Views", ", ".join(L["feat"]["views"])))
    if L["energy"]:
        rows.append(("Energy rating", L["energy"]))
    rows.append(("Reference", L["ref"]))
    return "\n          ".join(f"<div><dt>{k}</dt><dd>{e(v)}</dd></div>" for k, v in rows)


def similar(L, everyone, url_of):
    def score(o):
        same_type = (o["type"] in APARTMENT_TYPES) == (L["type"] in APARTMENT_TYPES)
        return (o["coast"] != L["coast"], not same_type, abs(o["price"] - L["price"]) / max(L["price"], 1))
    pool = sorted((o for o in everyone if o["id"] != L["id"] and o["photos"]), key=score)[:4]
    cards = []
    for o in pool:
        cards.append(f'''      <a class="card" href="{url_of(o, rel=True)}">
        <div class="card-photo"><img src="{o['photos'][0]['small']}" alt="{e(type_label(o).capitalize())} for sale in {e(o['town'])}" width="640" height="480" loading="lazy" decoding="async"><span class="badge">{e(o['type'])}</span></div>
        <div class="card-body">
          <p class="price">{price_text(o)}</p>
          <h3>{e(o['town'])}</h3>
          <span class="card-link">View property &rarr;</span>
        </div>
      </a>''')
    if not cards:
        return ""
    return ('    <section class="similar" aria-label="Similar properties">\n      <h2>Similar properties</h2>\n      <div class="grid">\n'
            + "\n".join(cards) + "\n      </div>\n    </section>\n")


def page(L, everyone, url_of, src):
    url = url_of(L)
    agent = TEAM[L["agent"]]
    faqs = faq(L, agent)
    lead, body = description_html(L["description"])
    desc = summary(L)
    c = costs(L)
    wa = urllib.request.quote(f"Hello {agent['name'].split()[0]}, I am interested in {L['title']} (ref. {L['ref']}).")
    hreflang = f'  <link rel="alternate" hreflang="en" href="{url}">\n'
    langs = f'        <a href="{url}" class="active" hreflang="en">EN</a>\n'
    if L["pl"]:
        hreflang += f'  <link rel="alternate" hreflang="pl" href="{L["pl"]}">\n'
        langs += f'        <a href="{L["pl"]}" hreflang="pl">PL</a>\n'
    hreflang += f'  <link rel="alternate" hreflang="x-default" href="{url}">\n'
    og_img = L["photos"][0]["big"] if L["photos"] else f"{SITE}/assets/hero.jpg"
    eyebrow = " · ".join(x for x in ("New build" if L["new"] else "Resale", f"{L['town']}, {L['province']}") if x)
    features = ""
    if L["feat"]["features"]:
        features += "<h3>Features</h3>\n        <ul class=\"feature-list\">" + "".join(f"<li>{e(f)}</li>" for f in L["feat"]["features"]) + "</ul>\n        "
    if L["feat"]["nearby"]:
        features += "<h3>Nearby</h3>\n        <ul class=\"feature-list\">" + "".join(f"<li>{e(f)}</li>" for f in L["feat"]["nearby"]) + "</ul>\n        "
    cost_html = ""
    if c:
        rows, total, note = c
        trs = "".join(f"\n            <tr><th scope=\"row\">{e(t)}</th><td>{euro(v)}</td></tr>" for t, v in rows)
        cost_html = f'''
        <h2>What does it cost to buy?</h2>
        <table class="cost-table">
          <tbody>
            <tr><th scope="row">Property price</th><td>{euro(L['price'])}</td></tr>{trs}
            <tr class="total"><th scope="row">Price including taxes</th><td>{euro(total)}</td></tr>
          </tbody>
        </table>
        <p>On top of this come the notary, the land registry and a lawyer, usually about 1.5–2.5% of the price. {e(note)} These are the general rates for the {e(L['region'])}; reduced rates exist for some buyers.</p>
'''
    map_link = (f'<p class="map-link"><a href="https://www.google.com/maps?q={L["lat"]},{L["lon"]}" target="_blank" rel="noopener">'
                f'Open the location in Google Maps &rarr;</a></p>') if L["lat"] else ""
    faq_html = "\n          ".join(f"<details><summary>{e(qq)}</summary><p>{e(a)}</p></details>" for qq, a in faqs)
    preload = f'  <link rel="preload" as="image" href="{src(0, "big")}" fetchpriority="high">\n' if L["photos"] else ""
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {MARKER}
  <title>{e(L['title'])} | Elite World Estates</title>
  <meta name="description" content="{e(desc)}">
  <meta name="robots" content="index, follow, max-image-preview:large">
  <link rel="canonical" href="{url}">
{hreflang}  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Elite World Estates">
  <meta property="og:title" content="{e(L['title'])}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{og_img}">
  <meta property="og:locale" content="en_GB">
  <meta name="twitter:card" content="summary_large_image">
{preload}  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,400&family=Prata&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/style.css">
  <script type="application/ld+json">
{schema(L, url, agent, faqs)}
  </script>
</head>
<body>

<header class="site-header" id="top">
  <div class="container header-inner">
    <a class="logo" href="../index.html" aria-label="Elite World Estates – home">
      <img src="../assets/logo.png" alt="Elite World Estates – Home is your castle" width="434" height="176">
    </a>
    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false">&#9776;</button>
    <nav class="main-nav" aria-label="Main">
      <a href="../index.html">Home</a>
      <a href="../index.html#properties" class="active">Properties</a>
      <a href="../blog.html">Blog</a>
      <a href="../about-us.html">About Us</a>
      <a href="#contact">Contact Us</a>
      <div class="lang">
{langs}      </div>
    </nav>
  </div>
</header>

<main class="property">
  <div class="container">
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <a href="../index.html">Home</a> <span>/</span> <a href="{SITE}/{L['coast_path']}">{e(L['coast'])}</a> <span>/</span> <span>{e(L['town'])}</span> <span>/</span> <span aria-current="page">{e(L['ref'])}</span>
    </nav>

    <header class="prop-head">
      <div>
        <p class="eyebrow dark">{e(eyebrow)}</p>
        <h1>{e(L['title'])}</h1>
        <p class="prop-ref">Reference {e(L['ref'])}</p>
      </div>
      <p class="prop-price">{"<span>From</span> " if L["from"] else ""}{euro(L['price'])}</p>
    </header>

    {gallery(L, src)}

    <ul class="key-facts" aria-label="Key facts">
      {key_facts(L)}
    </ul>

    <div class="prop-layout">
      <article class="prop-text">
        <h2>About this property</h2>
        {f'<p class="lead-strong">{e(lead)}</p>' if lead else ""}

        <h3>Key information</h3>
        <dl class="info-list">
          {info_list(L)}
        </dl>

        {body}
        {features}{map_link}
        <p class="small-print">The property description is based wholly or partly on information supplied by the owner or developer. Sizes, layouts, specifications and dates may change; the purchase contract is binding.</p>
{cost_html}
        <h2>Frequently asked questions</h2>
        <div class="faq">
          {faq_html}
        </div>

        <h2>Arrange your viewing</h2>
        <p>A viewing says more than any description. Call, send a WhatsApp or ask a question here, and we will arrange a visit or a video call at a time that suits you.</p>
      </article>

      <aside class="prop-aside" id="contact">
        <div class="agent-card">
          <p class="agent-title">Personal advice</p>
          <img class="agent-photo" src="../assets/about/{agent['photo']}" alt="{e(agent['name'])}, Property Adviser at Elite World Estates" width="600" height="600">
          <h2 class="agent-name">{e(agent['name'])}</h2>
          <p class="agent-role">Property Adviser</p>
          <div class="agent-actions">
            <a class="btn-agent" href="tel:{agent['tel']}">{ICON_PHONE}Call</a>
            <button class="btn-agent" type="button" aria-expanded="false" aria-controls="enquiry">{ICON_MAIL}Ask about this property</button>
            <a class="btn-agent" href="https://wa.me/{agent['tel'][1:]}?text={wa}" target="_blank" rel="noopener">{ICON_WA}WhatsApp</a>
          </div>
          <form class="contact-form enquiry" id="enquiry" hidden onsubmit="return false">
            <input type="text" id="lead-name" name="name" placeholder="Name" aria-label="Name" required>
            <input type="email" id="lead-email" name="email" placeholder="Email" aria-label="Email" required>
            <input type="tel" id="lead-phone" name="phone" placeholder="Phone" aria-label="Phone">
            <textarea id="lead-message" name="message" rows="4" aria-label="Message">I would like more information about {e(L['title'])} (ref. {e(L['ref'])}).</textarea>
            <label class="consent"><input type="checkbox" required> I declare that I have read, understood and accept the Legal Notice and the Privacy Policy</label>
            <button class="btn btn-gold" type="submit">Send</button>
          </form>
        </div>
        <p class="agent-ref">Ref. {e(L['ref'])}</p>
      </aside>
    </div>

{similar(L, everyone, url_of)}
    <section class="more-links" aria-label="More properties">
      <h2>Looking for something else?</h2>
      <a href="{SITE}/{L['coast_path']}">All properties on the {e(L['coast'] if L['coast'] != 'Spain' else 'coast')} &rarr;</a>
      <a href="{SITE}/contact-us">Book a free consultation &rarr;</a>
    </section>
  </div>
</main>

<section class="all-photos" id="photos" aria-label="All photos" hidden>
  <header class="ap-bar">
    <button class="ap-close" type="button">&larr; Back to property</button>
    <p class="ap-title">{e(L['title'])} · {len(L['photos'])} photos</p>
    <a class="btn btn-gold ap-cta" href="#contact">Ask about this property</a>
  </header>
  <div class="ap-grid">
      {all_photos(L, src)}
  </div>
</section>

<div class="lightbox" hidden>
  <button class="lb-close" type="button" aria-label="Close">&times;</button>
  <button class="lb-prev" type="button" aria-label="Previous photo">&#8249;</button>
  <img alt="">
  <button class="lb-next" type="button" aria-label="Next photo">&#8250;</button>
  <p class="lb-count"></p>
</div>

<footer class="site-footer">
  <div class="container footer-bottom">
    <p><a href="../index.html">Elite World Estates</a> · <a href="tel:+34672519809">0034 672 519 809</a> · <a href="mailto:info@eliteworldestates.com">info@eliteworldestates.com</a></p>
    <p>The property description is based wholly or partly on information supplied by the owner. We do not accept responsibility for the accuracy or completeness of this information.</p>
    <p>&copy; <span id="year"></span> Elite World Estates</p>
  </div>
</footer>

<script src="../js/main.js"></script>
<script src="../js/gallery.js"></script>
</body>
</html>
'''


# ---------- photos ----------

def photo_src(L, local):
    """Return src(i, size) -> photo URL for the page (eGO image server, or local copies)."""
    if not local:
        return lambda i, size: L["photos"][i][size]
    folder = os.path.join(ROOT, "assets", "listings", str(L["id"]))
    os.makedirs(folder, exist_ok=True)
    for i, ph in enumerate(L["photos"]):
        for size, suffix in (("big", ""), ("small", "-s")):
            path = os.path.join(folder, f"{i + 1:02d}{suffix}.jpg")
            if not os.path.exists(path):
                with urllib.request.urlopen(ph[size], timeout=60) as r, open(path, "wb") as f:
                    f.write(r.read())
    return lambda i, size: f"../assets/listings/{L['id']}/{i + 1:02d}{'-s' if size == 'small' else ''}.jpg"


# ---------- site files ----------

def replace_block(path, start, end, block, anchor):
    s = open(path, encoding="utf-8").read()
    s = re.sub(re.escape(start) + r".*?" + re.escape(end) + r"\n", "", s, flags=re.S)
    s = s.replace(anchor, start + "\n" + block + end + "\n" + anchor, 1)
    open(path, "w", encoding="utf-8").write(s)


def write_feeds(items, url_of):
    os.makedirs(os.path.join(ROOT, "feeds"), exist_ok=True)
    feed = []
    for L in items:
        feed.append({
            "id": L["id"], "reference": L["ref"], "title": L["title"], "url": url_of(L),
            "price": L["price"], "currency": "EUR", "price_from": L["from"],
            "type": L["type"], "condition": "new build" if L["new"] else "resale",
            "town": L["town"], "area": L["area"], "province": L["province"], "coast": L["coast"],
            "bedrooms": L["beds"], "bathrooms": L["baths"], "built_m2": L["built"], "usable_m2": L["usable"], "plot_m2": L["plot"],
            "latitude": L["lat"], "longitude": L["lon"], "features": L["feat"]["features"], "views": L["feat"]["views"],
            "summary": summary(L), "description": plain_text(L["description"]),
            "photos": [ph["big"] for ph in L["photos"]], "agent": TEAM[L["agent"]]["name"],
            "created": L["created"], "modified": L["modified"],
        })
    with open(os.path.join(ROOT, "feeds", "properties.json"), "w", encoding="utf-8") as f:
        json.dump({"updated": TODAY, "count": len(feed), "properties": feed}, f, ensure_ascii=False, indent=1)
    x = ['<?xml version="1.0" encoding="UTF-8"?>', f'<properties updated="{TODAY}" count="{len(feed)}">']
    for p in feed:
        x.append("  <property>")
        for k, v in p.items():
            if isinstance(v, list):
                tag = k[:-1] if k.endswith("s") else "item"
                x.append(f"    <{k}>" + "".join(f"<{tag}>{xml_escape(str(i))}</{tag}>" for i in v) + f"</{k}>")
            elif v is not None:
                x.append(f"    <{k}>{xml_escape(str(v))}</{k}>")
        x.append("  </property>")
    x.append("</properties>")
    with open(os.path.join(ROOT, "feeds", "properties.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(x) + "\n")


def main(args):
    local = "--local-photos" in args
    pl_path = os.path.join(CACHE, "_pl_links.json")
    pl_links = json.load(open(pl_path)) if os.path.exists(pl_path) else {}
    raw = [json.load(open(os.path.join(CACHE, f), encoding="utf-8"))
           for f in sorted(os.listdir(CACHE)) if f.endswith(".json") and not f.startswith("_")]
    items = [listing(p, pl_links) for p in raw]
    items.sort(key=lambda L: L["id"])
    # Two listings with the same title get the reference added to the address
    seen = {}
    for L in items:
        seen[L["slug"]] = seen.get(L["slug"], 0) + 1
    for L in items:
        if seen[L["slug"]] > 1 or not L["slug"]:
            L["slug"] = f"{L['slug']}-{L['ref'].lower()}".strip("-")

    os.makedirs(OUT, exist_ok=True)
    hand_made = set()
    for L in items:
        path = os.path.join(OUT, L["slug"] + ".html")
        if os.path.exists(path) and MARKER not in open(path, encoding="utf-8").read():
            hand_made.add(L["id"])

    def url_of(L, rel=False):
        return f"{L['slug']}.html" if rel else f"{SITE}/properties/{L['slug']}.html"

    built = set()
    for L in items:
        if L["id"] in hand_made:
            print("kept hand-made page", L["slug"])
            continue
        html_out = page(L, items, url_of, photo_src(L, local))
        open(os.path.join(OUT, L["slug"] + ".html"), "w", encoding="utf-8").write(html_out)
        built.add(L["slug"] + ".html")
    # Generated pages whose listing is gone from eGO
    for f in os.listdir(OUT):
        p = os.path.join(OUT, f)
        if f.endswith(".html") and f not in built and MARKER in open(p, encoding="utf-8").read():
            os.remove(p)
            print("removed", f)
    print(f"built {len(built)} pages, kept {len(hand_made)} hand-made")

    gen = [L for L in items if L["id"] not in hand_made]
    sm = "".join(f"  <url>\n    <loc>{url_of(L)}</loc>\n    <lastmod>{L['modified']}</lastmod>\n"
                 + (f'    <xhtml:link rel="alternate" hreflang="en" href="{url_of(L)}"/>\n'
                    f'    <xhtml:link rel="alternate" hreflang="pl" href="{L["pl"]}"/>\n' if L["pl"] else "")
                 + "".join(f"    <image:image><image:loc>{xml_escape(ph['big'])}</image:loc></image:image>\n" for ph in L["photos"][:5])
                 + "  </url>\n" for L in gen)
    replace_block(os.path.join(ROOT, "sitemap.xml"), "  <!-- properties -->", "  <!-- /properties -->", sm, "</urlset>")
    llms = "## Properties for sale\n\nAll listings with full details: " + SITE + "/feeds/properties.json\n\n" + "".join(
        f"- [{L['title']}]({url_of(L)}): {summary(L)} Ref. {L['ref']}.\n" for L in gen) + "\n"
    replace_block(os.path.join(ROOT, "llms.txt"), "<!-- properties -->", "<!-- /properties -->", llms, "## Articles")
    write_feeds(items, lambda L: (f"{SITE}/properties/{L['slug']}.html"))
    with open(os.path.join(HERE, "redirects.csv"), "w", encoding="utf-8") as f:
        f.write("from,to\n")
        for L in items:
            new = f"/properties/{L['slug']}.html"
            f.write(f"/property-details/{L['old_slug']}/{L['id']},{new}\n/property-details/{L['id']},{new}\n")
    print(f"sitemap, llms.txt, feeds and redirects updated ({len(items)} listings)")


if __name__ == "__main__":
    main(sys.argv[1:])
