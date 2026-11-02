"""Download property listings from eGO into tools/ego/cache/<id>.json.

Usage:
  python3 tools/ego/fetch_ego.py                            # EGO_USERNAME + EGO_PASSWORD: eGO Global API
  python3 tools/ego/fetch_ego.py --check                    # log in, show permissions, read 1 page only
  EGO_API_KEY=... python3 tools/ego/fetch_ego.py            # every listing (old website API)
  EGO_API_KEY=... python3 tools/ego/fetch_ego.py 26809066   # only these IDs
  python3 tools/ego/fetch_ego.py 26809066 ...               # no key: testing mode

With EGO_API_KEY set (the key from eGO support) listings come straight from the
eGO API. Without a key, fetch_public.js reads the given listings from the live
eGO website instead; that only works while the old site is online, so it is for
testing. If eGO's key works differently from the website API (another address
or header), only api() below needs to change.

With EGO_USERNAME and EGO_PASSWORD set (the eGO integration user), listings come
from the eGO Global API (api.egocrm.com): login -> JWT, then ListRealestateByPage.
Its records hold ids (type, condition, location, features, agent) that are looked
up once and turned into the same shape as the website API, so build_properties.py
needs no changes. It only reads: no write or delete call is ever made. The Global
API gives the main photo only (a Media endpoint is coming); photos already in the
cache from the website API are kept.

Each cache file is the listing exactly as eGO returns it (English texts).
build_properties.py turns the cache into static pages; nothing is loaded in the browser.
Also saves cache/_pl_links.json: listing ID -> matching page on eliteworldestates.pl.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
API = "https://websiteapi.egorealestate.com/v1"
PL_SITEMAP = "https://eliteworldestates.pl/sitemap-oferty.xml"
LANG = "en-gb"
PAGE_SIZE = 200


def get(url, headers=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EliteWorldEstates-build/1.0", **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            if i == tries - 1:
                raise
            print("  retry", url, e)
            time.sleep(2 ** (i + 1))


def api(path, key, **params):
    q = urllib.parse.urlencode({"lng": LANG, **params})
    return json.loads(get(f"{API}{path}?{q}", {"Accept": "application/json", "AuthorizationToken": key}))


# ---------- eGO Global API (api.egocrm.com) ----------

GAPI = "https://api.egocrm.com"
APP_ID = 6878


class Global:
    """Read-only client for the eGO Global API."""

    def __init__(self, user, password):
        self.token = None
        d = self.call("POST", "/authentication/Authentication/Login",
                      {"username": user, "password": password, "applicationId": APP_ID})
        self.token = d["token"]

    def call(self, method, path, body=None, **params):
        q = ("?" + urllib.parse.urlencode(params, doseq=True)) if params else ""
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        data = json.dumps(body).encode() if body is not None else None
        # urllib's default user agent is blocked by eGO's Cloudflare, curl's is not
        cmd = ["curl", "-sS", "--fail-with-body", "--retry", "3", "-X", method, GAPI + path + q]
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        if data is not None:
            cmd += ["--data-binary", "@-"]
        r = subprocess.run(cmd, input=data, capture_output=True, timeout=180)
        if r.returncode:
            raise RuntimeError(f"eGO {method} {path} failed: {r.stdout.decode()[:300]} {r.stderr.decode()[:200]}")
        return json.loads(r.stdout or b"null")

    def get(self, path, **params):
        return self.call("GET", path, applicationId=APP_ID, **params)

    def permissions(self):
        return self.call("GET", "/authentication/Authentication/ListSecurityFeatures")

    def pages(self, size=PAGE_SIZE, limit=None, **filters):
        page, got = 0, 0
        while True:
            d = self.call("POST", "/realestate/Realestate/ListRealestateByPage",
                          {"applicationIds": [APP_ID], "pageIndex": page, "numberOfRecords": size, **filters})
            rows = d.get("realestatesByPageDto") or []
            got += len(rows)
            print(f"page {page}: {got} of {d.get('totalRows')}")
            yield from rows
            if not rows or got >= (d.get("totalRows") or 0) or (limit and got >= limit):
                return
            page += 1


def lang(v, code=LANG):
    """Multi-language field {"en-gb": "..."} -> text in our language (fallback: any English, then any)."""
    if not isinstance(v, dict):
        return v or ""
    return v.get(code) or next((t for k, t in v.items() if k.lower().startswith("en") and t), "") or next(iter(v.values()), "")


class Lookups:
    """Names for the ids in a Global API listing, loaded once per run."""

    PROVINCES = ("Alicante", "Málaga", "Murcia", "Almería", "Valencia", "Granada", "Cádiz")

    def __init__(self, g):
        self.g = g
        self.nature = {x["id"]: lang(x["name"]) for x in g.get("/realestate/Nature/ListNatureType")}
        self.condition = {x["id"]: lang(x["name"]) for x in g.get("/realestate/ConditionType/ListConditionType")}
        self.feature = {x["id"]: x for x in g.get("/realestate/Feature/ListFeature")}
        self.employee = {}
        for x in g.get("/authentication/Authentication/ListEmployees"):
            name = f"{x.get('firstName') or ''} {x.get('lastName') or ''}".strip()
            for k in ("securityUserID", "securityUserId", "id"):
                if x.get(k):
                    self.employee[x[k]] = name
        self.locations = {}

    def load_locations(self, ids):
        """Fetch the given location ids and all their parents."""
        todo = {i for i in ids if i and i not in self.locations}
        while todo:
            batch = list(todo)[:100]
            for x in self.g.get("/metadata/Location/ListLocationById", locationIds=batch):
                self.locations[x["id"]] = x
            todo -= set(batch)
            todo |= {x.get("parentId") for x in self.locations.values()
                     if x.get("parentId") and x["parentId"] not in self.locations}

    def place(self, location_id):
        """location id -> (province, municipality, area) by walking up to the province."""
        chain, i = [], location_id
        while i in self.locations:
            chain.append(lang(self.locations[i]["name"]))
            i = self.locations[i].get("parentId")
        for n, name in enumerate(chain):
            if name in self.PROVINCES:
                below = chain[:n]
                return name, (below[-1] if below else ""), (below[-2] if len(below) > 1 else "")
        return "", (chain[0] if chain else ""), ""


def to_website_shape(r, lk, old=None):
    """Global API listing -> the website-API field names build_properties.listing() reads."""
    province, town, area = lk.place(r.get("locationId"))
    prices = [pr for b in r.get("businesses") or [] for pr in b.get("prices") or [] if pr.get("value")]
    agent = lk.employee.get(r.get("salesmanId")) or lk.employee.get(r.get("assignToSecurityUserId")) \
        or lk.employee.get(r.get("securityUserId"))
    feats = []
    for f in r.get("features") or []:
        meta = lk.feature.get(f.get("featureId")) or {}
        if meta:
            feats.append({"Title": lang(meta.get("name")), "Value": "" if f.get("value") in (None, True, "true") else str(f["value"])})
    m = r.get("firstMedia") or {}
    main = m.get("url") or m.get("webUri")
    images = (old or {}).get("Images") or ([{"Thumbnail": main, "Thumbnail_1280X1024": main,
                                             "Thumbnail_640X480": m.get("urlThumbnail") or m.get("webThumbUri") or main,
                                             "Description": lang(m.get("description"))}] if main else [])
    return {
        "ID": r["id"], "Reference": r.get("reference") or "", "Title": lang(r.get("name")),
        "Type": lk.nature.get(r.get("natureTypeId"), ""), "Condition": lk.condition.get(r.get("conditionTypeId"), ""),
        "Municipality": town, "Parish": area, "District": province,
        "GPSLat": r.get("gpsLat"), "GPSLon": r.get("gpsLon"),
        "PropertyBusiness": [{"Prices": [{"PriceValue": min(pr["value"] for pr in prices)}]}] if prices else [],
        "PropertyAgents": [{"AgentName": agent}] if agent else [],
        "Rooms": r.get("rooms") or 0, "Bathrooms": r.get("bathrooms") or 0,
        "GrossArea": r.get("grossArea"), "NetArea": r.get("nettArea"), "LandArea": r.get("landArea"),
        "Floor": r.get("floor") if r.get("floor") is not None else -1,
        "Year": (old or {}).get("Year"), "EnergyCertification": (old or {}).get("EnergyCertification") or "",
        "Features": (old or {}).get("Features") or feats,
        "Description": lang(r.get("description")),
        "CreatedDate": r.get("createDate") or "", "LastModified": r.get("lastUpdate") or "",
        "Images": images, "_source": "egocrm",
    }


def fetch_global(user, password, ids=None, check=False):
    g = Global(user, password)
    print("logged in to the eGO Global API")
    if check:
        perms = g.permissions()
        risky = [p for p in perms if re.search(r"delet|remov|elimin|apag", str(p.get("securityFeatureReference")), re.I)]
        print(f"{len(perms)} permissions; delete-type: {len(risky)}")
        for p in risky:
            print("  ", p.get("securityFeatureReference"), "flag", p.get("securityAccessFlag"))
    rows = list(g.pages(limit=PAGE_SIZE if check else None, hasWebPage=True))
    if ids:
        rows = [r for r in rows if str(r["id"]) in ids]
    lk = Lookups(g)
    lk.load_locations({r.get("locationId") for r in rows})
    keep = set()
    for r in rows:
        path = os.path.join(CACHE, f"{r['id']}.json")
        old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
        save(to_website_shape(r, lk, old))
        keep.add(f"{r['id']}.json")
    print(f"saved {len(keep)} listings")
    if not ids and not check:
        for f in os.listdir(CACHE):
            if f.endswith(".json") and not f.startswith("_") and f not in keep:
                os.remove(os.path.join(CACHE, f))
                print("removed", f)


def save(p):
    with open(os.path.join(CACHE, f"{p['ID']}.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)


def fetch_all(key):
    page, got, keep = 1, 0, set()
    while True:
        d = api("/Properties", key, pag=page, nre=PAGE_SIZE)
        for p in d["Properties"]:
            save(p)
            keep.add(f"{p['ID']}.json")
        got += len(d["Properties"])
        print(f"page {page}: {got} of {d['TotalRecords']}")
        if not d["Properties"] or got >= d["TotalRecords"]:
            break
        page += 1
    # Listings no longer on eGO (sold, withdrawn) drop out of the cache
    for f in os.listdir(CACHE):
        if f.endswith(".json") and not f.startswith("_") and f not in keep:
            os.remove(os.path.join(CACHE, f))
            print("removed", f)


def pl_links():
    """Map listing ID -> eliteworldestates.pl offer URL (its URLs end in -<id>)."""
    try:
        xml = get(PL_SITEMAP)
    except Exception as e:
        print("  could not read the PL sitemap:", e)
        return {}
    return {m.group(1): m.group(0) for m in re.finditer(r"https://eliteworldestates\.pl/nieruchomosc/[a-z0-9-]*?-(\d+)(?=<)", xml)}


def main(ids):
    os.makedirs(CACHE, exist_ok=True)
    check = "--check" in ids
    ids = [i for i in ids if i != "--check"]
    user, password = os.environ.get("EGO_USERNAME", "").strip(), os.environ.get("EGO_PASSWORD", "").strip()
    key = os.environ.get("EGO_API_KEY", "").strip()
    if user and password:
        fetch_global(user, password, set(ids), check)
        if check:
            return
    elif key and ids:
        for i in ids:
            save(api(f"/Properties/{i}", key))
            print("fetched", i)
    elif key:
        fetch_all(key)
    elif ids:
        print("No EGO_API_KEY: reading these listings from the live website (testing only).")
        subprocess.run(["node", os.path.join(HERE, "fetch_public.js"), *ids], check=True)
    else:
        sys.exit("Set EGO_API_KEY to fetch every listing, or give listing IDs to test with.")
    links = pl_links()
    with open(os.path.join(CACHE, "_pl_links.json"), "w", encoding="utf-8") as f:
        json.dump(links, f, indent=1, sort_keys=True)
    print(f"PL links: {len(links)}")


if __name__ == "__main__":
    main(sys.argv[1:])
