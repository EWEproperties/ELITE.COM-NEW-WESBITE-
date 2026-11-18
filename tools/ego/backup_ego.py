"""Our own copy of everything in eGO, so the website does not depend on eGO's API.

Usage:
  python3 tools/ego/backup_ego.py              # data snapshot + new/changed photos and documents
  python3 tools/ego/backup_ego.py --no-files   # data snapshot only (quick)
  python3 tools/ego/backup_ego.py --dir PATH   # store somewhere else (default: $EGO_BACKUP_DIR,
                                               # else /mnt/project-files/ego-backup)

READ-ONLY: it logs in with EGO_USERNAME / EGO_PASSWORD (never printed) and only
calls list/read endpoints. Nothing in eGO is ever edited or deleted.

What it keeps (folder layout):
  snapshots/YYYY-MM-DD/listings.json.gz   every listing exactly as eGO returns it: all fields,
                                          texts in every language, prices, status, internal notes
  snapshots/YYYY-MM-DD/media.json.gz      every photo / floor plan / brochure / video record
                                          (order, captions in every language, original links)
  snapshots/YYYY-MM-DD/lookups.json.gz    names for the ids in the listings (types, conditions,
                                          features, locations, agent names only)
  snapshots/YYYY-MM-DD/summary.json       counts + what changed since the previous snapshot
  snapshots/YYYY-MM-DD/changes.md         the same in plain words
  files/<CRM id>.zip                      the original photo, floor plan and brochure files of one
                                          listing (full size); files removed in eGO stay in the zip
  files/index.json                        which files each zip holds
  latest.json                             date of the newest snapshot

Old snapshots: the newest 60 are kept, plus the first one of every month (forever).
The internal fields (notes, owners, commissions) make this PRIVATE data: it must never
go into the public website repository. The website build only reads public fields from it:
  python3 tools/ego/fetch_ego.py --from-backup
"""
import datetime
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_ego import APP_ID, Global  # noqa: E402

DEFAULT_DIR = "/mnt/project-files/ego-backup"
KEEP_DAILY = 60
WORKERS = 8  # parallel photo downloads
# Refuse to store a snapshot that lost more than this share of listings (an eGO hiccup,
# not real sales); the previous snapshot then stays the newest.
MAX_DROP = 0.2


def put(local, path, tries=4):
    """Copy a finished local file to the backup folder and check it arrived.
    The project-files folder is a network drive where rename-into-place sometimes
    loses the file, so: plain copy to the final name, then compare sizes."""
    size = os.path.getsize(local)
    for _ in range(tries):
        shutil.copyfile(local, path)
        if os.path.exists(path) and os.path.getsize(path) == size:
            return
        time.sleep(3)
    raise RuntimeError(f"could not store {path}")


def write_json(path, data, gz=False):
    fd, tmp = tempfile.mkstemp(suffix=".gz" if gz else ".json")
    os.close(fd)
    opener = gzip.open if gz else open
    with opener(tmp, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None if gz else 1)
    try:
        put(tmp, path)
    finally:
        os.remove(tmp)


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


# ---------- read everything from eGO ----------

def all_media(g, ids):
    out = []
    for i in range(0, len(ids), 20):
        for attempt in range(4):  # big answers are sometimes cut off on the way: ask again
            try:
                out += g.call("GET", "/media/Media/ListMedia", objectIds=ids[i:i + 20],
                              objectName="Realestate", applicationId=APP_ID) or []
                break
            except RuntimeError:
                if attempt == 3:
                    raise
    return out


def lookups(g, rows):
    lk = {
        "nature": g.get("/realestate/Nature/ListNatureType"),
        "condition": g.get("/realestate/ConditionType/ListConditionType"),
        "feature": g.get("/realestate/Feature/ListFeature"),
    }
    # ListEmployees also returns login data: keep the names only
    agents = {}
    for x in g.get("/authentication/Authentication/ListEmployees"):
        name = f"{x.get('firstName') or ''} {x.get('lastName') or ''}".strip()
        for k in ("securityUserID", "securityUserId", "id"):
            if x.get(k):
                agents[str(x[k])] = name
    lk["agents"] = agents
    locs, todo = {}, {r.get("locationId") for r in rows if r.get("locationId")}
    while todo:
        batch = list(todo)[:50]  # eGO allows at most 50 per call
        for x in g.get("/metadata/Location/ListLocationById", locationIds=batch):
            locs[x["id"]] = x
        todo -= set(batch)
        todo |= {x.get("parentId") for x in locs.values() if x.get("parentId") and x["parentId"] not in locs}
    lk["locations"] = list(locs.values())
    return lk


# ---------- what changed ----------

def price(r):
    vals = [p.get("value") for b in r.get("businesses") or [] for p in b.get("prices") or [] if p.get("value")]
    return min(vals) if vals else None


def changes(prev, rows):
    old = {r["id"]: r for r in prev or []}
    new = {r["id"]: r for r in rows}
    ref = lambda r: r.get("reference") or str(r["id"])  # noqa: E731
    out = {
        "added": sorted(ref(new[i]) for i in new.keys() - old.keys()),
        "removed": sorted(ref(old[i]) for i in old.keys() - new.keys()),
        "price": [], "status": [], "edited": [],
    }
    for i in new.keys() & old.keys():
        a, b = old[i], new[i]
        if price(a) != price(b):
            out["price"].append(f"{ref(b)}: {price(a)} -> {price(b)}")
        if a.get("realestateStatusId") != b.get("realestateStatusId"):
            out["status"].append(f"{ref(b)}: {a.get('realestateStatusId')} -> {b.get('realestateStatusId')}")
        if a.get("lastUpdate") != b.get("lastUpdate"):
            out["edited"].append(ref(b))
    for k in ("price", "status", "edited"):
        out[k].sort()
    return out


def changes_md(day, rows, media, ch, prev_day):
    lines = [f"# eGO copy {day}", "",
             f"{len(rows)} listings, {sum(1 for m in media if m.get('mediaTypeKey') == 1)} photos.", ""]
    if not prev_day:
        lines.append("First snapshot.")
    else:
        lines.append(f"Compared with {prev_day}:")
        for k, label in (("added", "New listings"), ("removed", "Gone from eGO"), ("price", "Price changes"),
                         ("status", "Status changes"), ("edited", "Edited")):
            lines.append(f"- {label}: {len(ch[k])}" + (f" ({', '.join(ch[k][:40])}{' ...' if len(ch[k]) > 40 else ''})" if ch[k] else ""))
    return "\n".join(lines) + "\n"


# ---------- files (photos, floor plans, brochures) ----------

def original_url(m):
    u = m.get("url") or ""
    if "images.egorealestate.com" not in u:
        return None  # YouTube videos and other links: the record is enough
    return re.sub(r"/Z(\d+x\d+|Original)/", "/ZOriginal/", u, count=1)


def file_name(m):
    fmt = m.get("format") or os.path.splitext(m.get("url") or "")[1] or ".bin"
    return f"{m['mediaTypeKey']:02d}-{(m.get('priority') or 0):03d}-{m['uid']}{fmt.lower()}"


def download(url, path):
    r = subprocess.run(["curl", "-sS", "--fail", "--retry", "3", "--retry-delay", "2", "-m", "300",
                        "-A", "EliteWorldEstates-backup/1.0", "-o", path, url], capture_output=True)
    return r.returncode == 0 and os.path.getsize(path) > 0


def backup_files(base, media, rows):
    fdir = os.path.join(base, "files")
    os.makedirs(fdir, exist_ok=True)
    index = read_json(os.path.join(fdir, "index.json"), {})
    # a zip that went missing on the drive is downloaded again
    for owner in [o for o in index if not os.path.exists(os.path.join(fdir, f"{o}.zip"))]:
        del index[owner]
    refs = {str(r["id"]): r.get("reference") or "" for r in rows}
    by_owner = {}
    for m in media:
        if m.get("isContract") or not original_url(m):
            continue
        by_owner.setdefault(str(m["ownerId"]), []).append(m)
    new_files = failed = 0
    tmp = tempfile.mkdtemp(prefix="ego-files-")
    try:
        for n, (owner, items) in enumerate(sorted(by_owner.items()), 1):
            have = set(index.get(owner, {}).get("uids", []))
            todo = [m for m in items if m["uid"] not in have]
            if not todo:
                continue
            zpath = os.path.join(fdir, f"{owner}.zip")
            local = os.path.join(tmp, f"{owner}.zip")
            if os.path.exists(zpath):
                shutil.copyfile(zpath, local)
            got = []
            paths = {m["uid"]: os.path.join(tmp, m["uid"]) for m in todo}
            with ThreadPoolExecutor(WORKERS) as pool:  # several downloads at once: ~8x faster
                ok = dict(zip(paths, pool.map(lambda m: download(original_url(m), paths[m["uid"]]), todo)))
            with zipfile.ZipFile(local, "a", zipfile.ZIP_STORED) as z:
                names = set(z.namelist())
                for m in todo:
                    f = paths[m["uid"]]
                    if ok[m["uid"]]:
                        if file_name(m) not in names:
                            z.write(f, file_name(m))
                        got.append(m["uid"])
                    else:
                        failed += 1
                    if os.path.exists(f):
                        os.remove(f)
            if got:
                put(local, zpath)
                index[owner] = {"reference": refs.get(owner, index.get(owner, {}).get("reference", "")),
                                "uids": sorted(have | set(got))}
                new_files += len(got)
                write_json(os.path.join(fdir, "index.json"), index)  # progress survives an interruption
            os.remove(local)
            if n % 25 == 0:
                print(f"  files: {n}/{len(by_owner)} listings checked, {new_files} new files")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"files: {new_files} new, {failed} failed (tried again next run)")
    return new_files, failed


# ---------- old snapshots ----------

def prune(sdir):
    days = sorted(d for d in os.listdir(sdir) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))
    keep = set(days[-KEEP_DAILY:])
    seen_month = set()
    for d in days:
        if d[:7] not in seen_month:
            seen_month.add(d[:7])
            keep.add(d)
    for d in days:
        if d not in keep:
            shutil.rmtree(os.path.join(sdir, d))
            print("removed old snapshot", d)


def main(args):
    base = os.environ.get("EGO_BACKUP_DIR") or DEFAULT_DIR
    if "--dir" in args:
        base = args[args.index("--dir") + 1]
    user, password = os.environ.get("EGO_USERNAME", "").strip(), os.environ.get("EGO_PASSWORD", "").strip()
    if not (user and password):
        sys.exit("EGO_USERNAME / EGO_PASSWORD are not set")
    sdir = os.path.join(base, "snapshots")
    os.makedirs(sdir, exist_ok=True)
    day = datetime.datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()

    g = Global(user, password)
    print("logged in to eGO (read-only)")
    rows = list(g.pages())
    media = all_media(g, [r["id"] for r in rows])
    lk = lookups(g, rows)
    print(f"read {len(rows)} listings, {len(media)} media records")

    latest = read_json(os.path.join(base, "latest.json"), {})
    prev_day = latest.get("date") if latest.get("date") != day else latest.get("previous")
    complete = sorted(d for d in os.listdir(sdir) if d != day
                      and os.path.exists(os.path.join(sdir, d, "listings.json.gz")))
    prev_day = complete[-1] if complete else None
    prev = read_json(os.path.join(sdir, prev_day, "listings.json.gz")) if prev_day else None
    if prev and len(rows) < (1 - MAX_DROP) * len(prev):
        sys.exit(f"STOPPED: eGO returned {len(rows)} listings, previous copy has {len(prev)}. Nothing overwritten.")

    ch = changes(prev, rows)
    out = os.path.join(sdir, day)
    os.makedirs(out, exist_ok=True)
    write_json(os.path.join(out, "listings.json.gz"), rows, gz=True)
    write_json(os.path.join(out, "media.json.gz"), media, gz=True)
    write_json(os.path.join(out, "lookups.json.gz"), lk, gz=True)
    md = os.path.join(tempfile.gettempdir(), "changes.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(changes_md(day, rows, media, ch, prev_day))
    put(md, os.path.join(out, "changes.md"))
    summary = {"date": day, "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "listings": len(rows), "media": len(media),
               "photos": sum(1 for m in media if m.get("mediaTypeKey") == 1), "changes": ch}

    if "--no-files" not in args:
        summary["new_files"], summary["failed_files"] = backup_files(base, media, rows)
    write_json(os.path.join(out, "summary.json"), summary)
    for n in ("listings.json.gz", "media.json.gz", "lookups.json.gz", "summary.json", "changes.md"):
        if not os.path.exists(os.path.join(out, n)):
            sys.exit(f"STOPPED: {n} missing in snapshot {day} after writing it")
    write_json(os.path.join(base, "latest.json"), {"date": day, "previous": prev_day})
    prune(sdir)
    print(open(os.path.join(out, "changes.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main(sys.argv[1:])
