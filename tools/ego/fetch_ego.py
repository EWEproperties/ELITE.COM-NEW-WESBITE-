"""Download property listings from eGO into tools/ego/cache/<id>.json.

Usage:
  EGO_API_KEY=... python3 tools/ego/fetch_ego.py            # every listing
  EGO_API_KEY=... python3 tools/ego/fetch_ego.py 26809066   # only these IDs
  python3 tools/ego/fetch_ego.py 26809066 ...               # no key: testing mode

With EGO_API_KEY set (the key from eGO support) listings come straight from the
eGO API. Without a key, fetch_public.js reads the given listings from the live
eGO website instead; that only works while the old site is online, so it is for
testing. If eGO's key works differently from the website API (another address
or header), only api() below needs to change.

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
    key = os.environ.get("EGO_API_KEY", "").strip()
    if key and ids:
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
