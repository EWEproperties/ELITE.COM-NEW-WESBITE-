"""Refresh the town pages' listings from eGO (tools/ego/cache, made by fetch_ego.py).

Writes tools/towns/data/<town>-listings.json in the same shape scrape_list.js +
prepare_listings.py made from the live site, so build_town.py needs no changes:
new listings appear, sold or withdrawn ones drop out, prices and titles follow eGO.

Which eGO municipalities belong to a town page is taken from the page's current
listings file (so Benidorm keeps Finestrat as "nearby", Alicante keeps Mutxamel...).
A municipality that has its own town page is only kept on another page when it
gave that page 3 or more listings (so a stray Orihuela flat no longer shows on
the Torrevieja page). Card photos are downloaded at 800 px like before.

Usage:
  python3 tools/towns/from_ego.py            # every town page with a listings file
  python3 tools/towns/from_ego.py torrevieja # only these
Then run build_town.py for each town and tools/link_properties.py.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools", "ego"))
from build_properties import apply_fixes, ego_photo  # noqa: E402

CACHE = os.path.join(ROOT, "tools", "ego", "cache")


def load_cache():
    out = []
    for f in glob.glob(os.path.join(CACHE, "[0-9]*.json")):
        p = apply_fixes(json.load(open(f, encoding="utf-8")))
        if (p.get("Description") or "").strip() and p.get("Reference"):
            out.append(p)
    return out


def price(p):
    try:
        v = p["PropertyBusiness"][0]["Prices"][0]["PriceValue"]
    except (KeyError, IndexError, TypeError):
        v = 0
    return f"{int(v):,} €".replace(",", " ") if v else ""


def num(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        return ""
    return f"{v:g}" if v > 0 else ""


def item(p, old_ids):
    img = p["Images"][0] if p.get("Images") else {}
    det = {"ROOMS": num(p.get("Rooms")), "BATHS": num(p.get("Bathrooms")),
           "AREA": num(p.get("NetArea")) or num(p.get("GrossArea"))}
    return {"id": str(p["ID"]), "slug": "", "img": ego_photo(img.get("Thumbnail") or "", "Z800x600"),
            "alt": (img.get("AlternativeText") or img.get("Description") or p["Title"]).strip(),
            "ref": p["Reference"], "title": p["Title"], "price": price(p),
            "loc": [p.get("District") or "", p.get("Municipality") or ""],
            "det": {k: v for k, v in det.items() if v}}


def main(args):
    configs = {os.path.basename(f)[:-5]: json.load(open(f, encoding="utf-8"))
               for f in glob.glob(os.path.join(HERE, "*.json"))}
    data = {s: json.load(open(os.path.join(HERE, "data", f"{s}-listings.json"), encoding="utf-8"))
            for s in configs if os.path.exists(os.path.join(HERE, "data", f"{s}-listings.json"))}
    listings = load_cache()
    by_id = {str(p["ID"]): p for p in listings}

    # eGO municipality name for each old listing (live site names can differ from eGO's)
    def muni(i):
        p = by_id.get(i["id"])
        return p["Municipality"] if p else i["loc"][-1]

    counts = {s: collections.Counter(muni(i) for i in d) for s, d in data.items()}
    own = {}  # municipality -> the town page that is about it
    for s, c in counts.items():
        main_name = next((m for m, n in configs[s]["town_names"].items() if n == configs[s]["town"]), None)
        main_muni = next((m for m in c if m == main_name or m.startswith(str(main_name))), None) or c.most_common(1)[0][0]
        own[main_muni] = s

    for s in (args or sorted(data)):
        keep = {m for m, n in counts[s].items() if own.get(m) in (None, s) or n >= 3}
        old_ids = {i["id"] for i in data[s]}
        new = [item(p, old_ids) for p in listings if p.get("Municipality") in keep]
        new.sort(key=lambda i: i["ref"])
        folder = os.path.join(ROOT, "assets", "towns", s, "listings")
        os.makedirs(folder, exist_ok=True)
        for i in new:
            path = os.path.join(folder, i["id"] + ".jpg")
            if os.path.exists(path) or not i["img"]:
                continue
            if subprocess.run(["curl", "-sSfo", path, i["img"]]).returncode:
                print("photo failed", i["ref"]); continue
            im = Image.open(path).convert("RGB")
            if im.width > 800:
                im = im.resize((800, round(im.height * 800 / im.width)), Image.LANCZOS)
            im.save(path, quality=78, optimize=True, progressive=True)
        ids = {i["id"] for i in new}
        for f in os.listdir(folder):  # photos of listings that left the page
            if f.endswith(".jpg") and f[:-4] not in ids:
                os.remove(os.path.join(folder, f))
        json.dump(new, open(os.path.join(HERE, "data", f"{s}-listings.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        added, gone = len(ids - old_ids), len(old_ids - ids)
        print(f"{s}: {len(new)} listings ({len(data[s])} before, +{added} new, -{gone} gone) from {sorted(keep)}")


if __name__ == "__main__":
    main(sys.argv[1:])
