"""Write tools/golf/data/<page>-listings.json for each golf page and download the card photos.

Usage:
  python3 tools/golf/prepare_golf.py [<scraped.json> ...]

Listings are picked by EWE reference (the "refs" and "near_refs" lists in tools/golf/golf.json)
from tools/towns/data/all-live-listings.json and any extra scraped files (scrape_list.js output).
Until the eGO API key arrives this is how the golf pages get their listings.
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "towns"))
from prepare_listings import num  # noqa: E402


def load_all(extra):
    items = {}
    for f in [os.path.join(ROOT, "tools", "towns", "data", "all-live-listings.json")] + extra:
        for i in json.load(open(f, encoding="utf-8")):
            if i.get("href") and i["ref"] not in items:
                m = re.search(r"property-details/([^/]+)/(\d+)", i["href"])
                d = i["det"]
                items[i["ref"]] = {"id": m.group(2), "slug": m.group(1), "img": i["img"], "alt": i.get("alt") or "", "ref": i["ref"],
                                   "title": re.split(r"\s{3,}", i["title"].strip())[0], "price": i["price"], "loc": i["loc"],
                                   "det": {k: num(d.get(k)) for k in ("ROOMS", "BATHS", "AREA") if num(d.get(k))}}
    return items


def photo(i):
    """Return the card photo's path, reusing a town page's copy when there is one."""
    for town in sorted(os.listdir(os.path.join(ROOT, "assets", "towns"))):
        rel = f"assets/towns/{town}/listings/{i['id']}.jpg"
        if os.path.exists(os.path.join(ROOT, rel)):
            return rel
    rel = f"assets/golf/listings/{i['id']}.jpg"
    path = os.path.join(ROOT, rel)
    if os.path.exists(path):
        return rel
    url = re.sub(r"\.webp$", "", i["img"].replace("Z512x384", "Z800x600"))
    if subprocess.run(["curl", "-sSfo", path, url]).returncode:
        sys.exit(f"photo failed {i['ref']}")
    im = Image.open(path).convert("RGB")
    if im.width > 800:
        im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
    im.save(path, quality=78, optimize=True, progressive=True)
    return rel


def main(extra):
    items = load_all(extra)
    os.makedirs(os.path.join(ROOT, "assets", "golf", "listings"), exist_ok=True)
    c = json.load(open(os.path.join(HERE, "golf.json"), encoding="utf-8"))
    for p in c["courses"] + [c["costa_del_sol"]]:
        refs = p.get("refs", []) + p.get("near_refs", [])
        missing = [r for r in refs if r not in items]
        if missing:
            sys.exit(f"{p['page']}: not found {missing}")
        out = []
        for r in refs:
            i = dict(items[r], near=r in p.get("near_refs", []))
            i["photo"] = photo(i)
            out.append(i)
        json.dump(out, open(os.path.join(HERE, "data", p["page"] + "-listings.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(p["page"], len(out))


if __name__ == "__main__":
    main(sys.argv[1:])
