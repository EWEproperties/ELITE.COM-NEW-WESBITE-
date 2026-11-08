"""Nearest beach, schools, hospital/health centre, supermarket and airport for each listing,
for the property-page FAQ (Lucy, 2026-11-08). eGO has no such data, so it comes from
OpenStreetMap (Overpass API) and road distances from the public OSRM router.

Usage:
  python3 tools/ego/nearby.py              # every cached listing not yet in nearby.json
  python3 tools/ego/nearby.py EWE3774 ...  # only these references (refreshed)

Writes tools/ego/nearby.json: {ref: {"beach": {...}, "school_public"/"school_private"/"school_intl": {...}, "health": {...},
"shop": {...}, "airport": {...}}}, each place {"name", "km", "min"}. Distances are by road,
from the listing's eGO map pin; pages round them and say "about".
Map data © OpenStreetMap contributors (ODbL).
"""
import glob
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nearby.json")
OVERPASS = "https://overpass-api.de/api/interpreter"  # needs a named user agent (406 for plain curl)
OSRM = "https://router.project-osrm.org/route/v1/driving/"
AIRPORTS = [  # (name, lat, lon)
    ("Alicante-Elche Airport", 38.2822, -0.5582),
    ("Murcia International Airport (Corvera)", 37.8030, -1.1250),
    ("Valencia Airport", 39.4893, -0.4816),
    ("Málaga Airport", 36.6749, -4.4991),
    ("Almería Airport", 36.8439, -2.3701),
    ("Gibraltar Airport", 36.1512, -5.3497),
    ("Granada Airport", 37.1887, -3.7774),
]
QUERIES = [  # one small query each: the combined one times out
    "nwr(around:15000,{lat},{lon})[natural=beach][name];",
    "nwr(around:8000,{lat},{lon})[amenity=school][name];",
    "nwr(around:30000,{lat},{lon})[amenity=hospital][name];",
    "nwr(around:12000,{lat},{lon})[amenity=clinic][name];",
    "nwr(around:6000,{lat},{lon})[shop=supermarket][name];",
]


def curl(url, data=None):
    cmd = ["curl", "-sS", "-m", "90", "--retry", "2", "-A", "EliteWorldEstates-site-builder/1.0", url]
    if data:
        cmd += ["--data-urlencode", "data=" + data]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None
    try:
        return json.loads(r.stdout or b"null")
    except ValueError:
        return None


def km_line(a, b, c, d):
    p = math.pi / 180
    h = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def road(lat, lon, plat, plon):
    r = curl(f"{OSRM}{lon},{lat};{plon},{plat}?overview=false")
    if r and r.get("code") == "Ok":
        leg = r["routes"][0]
        return round(leg["distance"] / 1000, 1), round(leg["duration"] / 60)
    return round(km_line(lat, lon, plat, plon) * 1.3, 1), None


def place(name, lat, lon, plat, plon):
    km, mins = road(lat, lon, plat, plon)
    time.sleep(1)  # be kind to the public router
    return {"name": name, "km": km, "min": mins}


GENERIC = {"British School", "Colegio de Educación Infantil y Primaria", "Colegio Público", "Instituto de Educación Secundaria"}
TOWNS_FILE = os.path.join(HERE, "osm-cache", "towns.json")


def town_of(lat, lon):
    """Town name for a map point (OSM Nominatim), cached: used to tell apart places with a generic name."""
    towns = json.load(open(TOWNS_FILE)) if os.path.exists(TOWNS_FILE) else {}
    key = f"{lat:.4f},{lon:.4f}"
    if key not in towns:
        r = curl(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=14")
        a = (r or {}).get("address", {})
        towns[key] = a.get("village") or a.get("town") or a.get("city") or a.get("hamlet") or ""
        time.sleep(1)
        os.makedirs(os.path.dirname(TOWNS_FILE), exist_ok=True)
        json.dump(towns, open(TOWNS_FILE, "w"), ensure_ascii=False)
    return towns[key]


def nearest(elems, test, lat, lon, n=1):
    out = []
    for x in elems:
        t = x.get("tags", {})
        if not test(t):
            continue
        c = x.get("center") or x
        if "lat" not in c:
            continue
        out.append((km_line(lat, lon, c["lat"], c["lon"]), t.get("short_name") or t.get("name"), c["lat"], c["lon"]))
    out.sort()
    seen, res = set(), []
    for d, nm, a, b in out:
        if nm in seen:
            continue
        seen.add(nm)
        if nm in GENERIC and town_of(a, b):
            nm = f"{nm} ({town_of(a, b)})"
        res.append((nm, a, b))
        if len(res) == n:
            break
    return res


def lookup(lat, lon):
    el = []
    for q in QUERIES:
        for attempt in range(4):  # the public server refuses bursts: wait and retry
            data = curl(OVERPASS, "[out:json][timeout:60];" + q.format(lat=lat, lon=lon) + "out center tags;")
            if data and "elements" in data:
                el += data["elements"]
                break
            time.sleep(10 * (attempt + 1))
        time.sleep(2)
    res = {}
    b = nearest(el, lambda t: t.get("natural") == "beach", lat, lon)
    if b:
        res["beach"] = place(b[0][0], lat, lon, b[0][1], b[0][2])
    sch = nearest(el, lambda t: t.get("amenity") == "school", lat, lon, n=2)
    if sch:
        res["schools"] = [place(nm, lat, lon, a, c) for nm, a, c in sch]
    h = nearest(el, lambda t: t.get("amenity") == "hospital", lat, lon)
    if h:
        res["hospital"] = place(h[0][0], lat, lon, h[0][1], h[0][2])
    # public health centres ("Centro de Salud", "Consultorio"), not private or military clinics
    hc = nearest(el, lambda t: t.get("amenity") == "clinic" and re.search(r"salud|consultori|health", t.get("name", ""), re.I), lat, lon)
    if hc:
        res["health"] = place(hc[0][0], lat, lon, hc[0][1], hc[0][2])
    s = nearest(el, lambda t: t.get("shop") == "supermarket", lat, lon)
    if s:
        res["shop"] = place(s[0][0], lat, lon, s[0][1], s[0][2])
    # the two nearest airports (on the south Costa Blanca buyers fly into Murcia or Alicante)
    aps = sorted(AIRPORTS, key=lambda x: km_line(lat, lon, x[1], x[2]))[:2]
    res["airports"] = sorted((place(x[0], lat, lon, x[1], x[2]) for x in aps), key=lambda x: x["km"])
    return res


CATS = {  # category -> Overpass filter (run once per region box, not per listing)
    "beach": "nwr[natural=beach][name]",
    "school": "nwr[amenity=school][name]",
    "hospital": "nwr[amenity=hospital][name]",
    "clinic": "nwr[amenity=clinic][name]",
    "shop": "nwr[shop=supermarket][name]",
}
HEALTH_CENTRE = re.compile(r"centro de salud|centre de salut|consultori|health cent|ambulatorio", re.I)
OSM_CACHE = os.path.join(HERE, "osm-cache")  # raw Overpass answers per province (not committed)
PAD = 0.35  # degrees (~35 km) around the listings of a province
# Schools are split like on elite.pl: public, private, international (Lucy, 2026-11-08).
NOT_SCHOOL = re.compile(r"academ|formaci|guarder|\bE\. ?I\.|\bEPA\b|adult|especial|discapac|ocupacional|"
                        r"granja|conservatori|m[uú]sica|idiomas|autoescuela|n[aá]utica|agrari|danza|dance|in english|"
                        r"think english|stem english|language|centro de d[ií]a", re.I)
INTL_SCHOOL = re.compile(r"international|internacional|internacional|british|english school|american|europe|"
                         r"norueg|norsk|norske|finland|finlandés|suomalai|svensk|scandinav|deutsch|alem[aá]n|"
                         r"liceo franc|fran[cç]ais", re.I)
PUBLIC_SCHOOL = re.compile(r"\bCEIP\b|\bIES\b|\bC\.?E\.?I\.?P|\bI\.?E\.?S\.|\bC\.?P\.?R?\b|\bCRA\b|p[uú]blic|"
                           r"educaci[oó]n (infantil y )?primaria|educaci[oó] infantil i prim|instituto|institut|institudo|"
                           r"colegio rural|aulari", re.I)
PRIVATE_SCHOOL = re.compile(r"privad|concertad|salesian|la salle|sagrad|diocesan|docente privado|jesu[iíï]t|inmaculada|"
                            r"trinitari|escolapi|escola pia|teresian|marist|carmelit|ursulin|esclavas|cooperativa|"
                            r"jes[uú]s mar[ií]a|patronato|nuestra señora|virgen|santa |san |sant |salesian", re.I)
SCHOOL_WORD = re.compile(r"colegio|col·legi|school|college|escuela|escola|centro docente|centre educatiu|centro escolar|"
                         r"skole|skolan|schule|liceo", re.I)


def school_kind(t):
    """'public', 'private', 'intl' or None (not a regular school, or unknown)."""
    if t.get("amenity") != "school":
        return None
    nm = t.get("name", "")
    if NOT_SCHOOL.search(nm) or re.search(r"[\u0600-\u06ff]", nm) or (re.search(r"infantil", nm, re.I) and not re.search(r"prim", nm, re.I)):
        return None
    op = t.get("operator:type")
    if INTL_SCHOOL.search(nm):
        return "intl"
    if op in ("public", "government") or (op not in ("private", "religious") and PUBLIC_SCHOOL.search(nm)):
        return "public"
    if (op in ("private", "religious") or PRIVATE_SCHOOL.search(nm)) and SCHOOL_WORD.search(nm):
        return "private"
    return None


def region_places(pts, prov=""):
    """All places of each category inside the box around these listings, one query per category.
    Saved in osm-cache/ so a rerun (e.g. after changing the picking rules) needs no new queries."""
    cache = os.path.join(OSM_CACHE, re.sub(r"\W+", "-", prov or "x") + ".json")
    if os.path.exists(cache):
        return json.load(open(cache))
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    box = f"{min(la) - PAD},{min(lo) - PAD},{max(la) + PAD},{max(lo) + PAD}"
    el = []
    for cat, flt in CATS.items():
        for attempt in range(5):
            data = curl(OVERPASS, f"[out:json][timeout:180];{flt}({box});out center tags;")
            if data and "elements" in data:
                el += data["elements"]
                print(f"  {cat}: {len(data['elements'])}")
                break
            time.sleep(15 * (attempt + 1))
        else:
            print(f"  {cat}: FAILED")
            return el  # not cached, so the next run tries again
        time.sleep(3)
    os.makedirs(OSM_CACHE, exist_ok=True)
    json.dump(el, open(cache, "w"))
    return el


def pick(el, lat, lon):
    """Nearest places by straight line; road distances come from one OSRM table call."""
    chosen = {}
    b = nearest(el, lambda t: t.get("natural") == "beach", lat, lon)
    if b and km_line(lat, lon, b[0][1], b[0][2]) <= 15:
        chosen["beach"] = b
    for kind, limit in (("public", 8), ("private", 20), ("intl", 40)):
        s = nearest(el, lambda t: school_kind(t) == kind, lat, lon)
        if s and km_line(lat, lon, s[0][1], s[0][2]) <= limit:
            chosen["school_" + kind] = s
    # OSM tags some health centres as hospitals: sort them by name
    h = nearest(el, lambda t: t.get("amenity") == "hospital" and not HEALTH_CENTRE.search(t.get("name", "")), lat, lon)
    if h:
        chosen["hospital"] = h
    hc = nearest(el, lambda t: t.get("amenity") in ("clinic", "hospital") and HEALTH_CENTRE.search(t.get("name", "")), lat, lon)
    if hc and km_line(lat, lon, hc[0][1], hc[0][2]) <= 12:
        chosen["health"] = hc
    sh = nearest(el, lambda t: t.get("shop") == "supermarket", lat, lon)
    if sh and km_line(lat, lon, sh[0][1], sh[0][2]) <= 6:
        chosen["shop"] = sh
    chosen["airports"] = [(x[0], x[1], x[2]) for x in sorted(AIRPORTS, key=lambda x: km_line(lat, lon, x[1], x[2]))[:2]]
    flat = [(k, x) for k, v in chosen.items() for x in v]
    coords = ";".join([f"{lon},{lat}"] + [f"{x[2]},{x[1]}" for _, x in flat])
    r = None
    for attempt in range(3):
        r = curl(f"{OSRM.replace('/route/', '/table/')}{coords}?sources=0&annotations=distance,duration")
        if r and r.get("code") == "Ok":
            break
        time.sleep(5)
    res = {}
    for i, (k, x) in enumerate(flat, start=1):
        if r and r.get("code") == "Ok" and r["distances"][0][i] is not None:
            km, mins = round(r["distances"][0][i] / 1000, 1), round(r["durations"][0][i] / 60)
        else:
            km, mins = round(km_line(lat, lon, x[1], x[2]) * 1.3, 1), None
        item = {"name": x[0], "km": km, "min": mins}
        if k == "airports":
            res.setdefault(k, []).append(item)
        else:
            res[k] = item
    for k in ("airports",):
        if res.get(k):
            res[k].sort(key=lambda x: x["km"])
    return res


def main(refs):
    """Bulk mode: one set of Overpass queries per province, then one OSRM call per listing."""
    done = json.load(open(OUT)) if os.path.exists(OUT) and "--fresh" not in refs else {}
    refs = refs - {"--fresh"}
    todo = {}
    for f in sorted(glob.glob(os.path.join(HERE, "cache", "[0-9]*.json"))):
        p = json.load(open(f))
        ref = p.get("Reference")
        if not ref or not p.get("GPSLat") or (refs and ref not in refs) or (not refs and ref in done):
            continue
        todo.setdefault(p.get("District") or "?", []).append((float(p["GPSLat"]), float(p["GPSLon"]), ref))
    for prov, pts in todo.items():
        print(prov, len(pts), "listings")
        el = region_places(pts, prov)
        for lat, lon, ref in pts:
            try:
                done[ref] = pick(el, lat, lon)
            except Exception as ex:  # one bad listing must not stop the rest
                print(ref, "failed:", ex)
            time.sleep(1)  # be kind to the public router
        with open(OUT, "w") as fh:
            json.dump(done, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(prov, "done")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
