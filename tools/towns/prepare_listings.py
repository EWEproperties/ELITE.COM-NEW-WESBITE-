"""Merge scraped listing files into tools/towns/data/<town>-listings.json and download card photos.

Usage:
  python3 tools/towns/prepare_listings.py <town> <scraped.json> [<scraped.json> ...] [--skip "Santa Pola,..."]

The scraped files come from scrape_list.js (the town's search page and its old listings page).
Until the eGO API key arrives this is how town pages get their listings; later the eGO
generator can write the same file.
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def num(s):
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return m.group(0).replace(",", ".") if m else ""


def main(args):
    skip = []
    if "--skip" in args:
        k = args.index("--skip")
        skip = [x.strip() for x in args[k + 1].split(",")]
        args = args[:k] + args[k + 2:]
    town, files = args[0], args[1:]
    items = {}
    for f in files:
        for i in json.load(open(f, encoding="utf-8")):
            if not i.get("loc") or i["loc"][-1] in skip or i["ref"] in items:
                continue
            d = i["det"]
            items[i["ref"]] = {"id": i["id"], "slug": i["slug"], "img": i["img"], "alt": i.get("alt") or "", "ref": i["ref"],
                               "title": re.split(r"\s{3,}", i["title"].strip())[0], "price": i["price"], "loc": i["loc"],
                               "det": {k: num(d.get(k)) for k in ("ROOMS", "BATHS", "AREA") if num(d.get(k))}}
    folder = os.path.join(ROOT, "assets", "towns", town, "listings")
    os.makedirs(folder, exist_ok=True)
    for i in items.values():
        path = os.path.join(folder, i["id"] + ".jpg")
        if os.path.exists(path):
            continue
        url = re.sub(r"\.webp$", "", i["img"].replace("Z512x384", "Z800x600"))
        if subprocess.run(["curl", "-sSfo", path, url]).returncode:
            print("photo failed", i["ref"]); continue
        im = Image.open(path).convert("RGB")
        if im.width > 800:
            im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
        im.save(path, quality=78, optimize=True, progressive=True)
    out = os.path.join(HERE, "data", town + "-listings.json")
    json.dump(list(items.values()), open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{out}: {len(items)} listings")


if __name__ == "__main__":
    main(sys.argv[1:])
