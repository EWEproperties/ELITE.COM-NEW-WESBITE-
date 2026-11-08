"""Nearest beach, schools, hospital/health centre, supermarket and airport for each listing,
for the property-page FAQ (Lucy, 2026-11-08). eGO has no such data, so it comes from
OpenStreetMap (Overpass API) and road distances from the public OSRM router.

Usage:
  python3 tools/ego/nearby.py              # every cached listing not yet in nearby.json
  python3 tools/ego/nearby.py EWE3774 ...  # only these references (refreshed)

Writes tools/ego/nearby.json: {ref: {"beach": {...}, "schools": [...], "health": {...},
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


def main(refs):
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for f in sorted(glob.glob(os.path.join(HERE, "cache", "[0-9]*.json"))):
        p = json.load(open(f))
        ref = p.get("Reference")
        if not ref or not p.get("GPSLat") or (refs and ref not in refs) or (not refs and ref in done):
            continue
        try:
            done[ref] = lookup(float(p["GPSLat"]), float(p["GPSLon"]))
            print(ref, ", ".join(k for k in done[ref]))
        except Exception as ex:  # one bad listing must not stop the rest
            print(ref, "failed:", ex)
        with open(OUT, "w") as fh:
            json.dump(done, fh, ensure_ascii=False, indent=1, sort_keys=True)
        time.sleep(2)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
