#!/usr/bin/env python3
"""Copy Lucy's edits from the property text editor into tools/ego/fixes.json.

The editor (a private claude.ai page) keeps one document per property in its
"edits" collection, id = eGO reference, with only the fields she changed:
  h1 -> fixes "title" (page heading)      text -> fixes "description" (page text)
  seo_title / seo_desc -> Google title and description
Claude saves that collection as JSON files (one <REF>.json each) and runs:
  python3 tools/ego/sync_editor.py <folder with the JSON files>
then build_properties.py. A field Lucy restored to the original is absent from her
document, so it goes back to its value before her edit (kept under "_editor"). Fixes made by Claude for
properties she never edited are kept. eGO is never changed.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXES_PATH = os.path.join(HERE, "fixes.json")
MAP = {"h1": "title", "text": "description", "seo_title": "seo_title", "seo_desc": "seo_desc"}


def main(folder):
    fixes = json.load(open(FIXES_PATH, encoding="utf-8"))
    edited = {}
    for f in sorted(os.listdir(folder)):
        if f.endswith(".json"):
            doc = json.load(open(os.path.join(folder, f), encoding="utf-8"))
            doc = doc.get("data", doc)  # tolerate a {"data": {...}} wrapper
            edited[f[:-5]] = doc
    changed = 0
    val = lambda doc, k: doc.get(k).strip() if isinstance(doc.get(k), str) else ""
    # _editor: {ref: {fixes field: value it had before Lucy's edit, or null}}
    log = fixes.setdefault("_editor", {})
    # 1. fields Lucy restored (no longer in her document) go back to what they were
    for ref, fields in list(log.items()):
        for dst, prev in list(fields.items()):
            src = next(k for k, d in MAP.items() if d == dst)
            if not val(edited.get(ref, {}), src):
                fix = fixes.setdefault(ref, {})
                if prev is None:
                    fix.pop(dst, None)
                else:
                    fix[dst] = prev
                del fields[dst]
                changed += 1
                if not fix:
                    del fixes[ref]
        if not fields:
            del log[ref]
    # 2. her current edits
    for ref, doc in edited.items():
        if not ref.startswith("EWE"):
            continue
        for src, dst in MAP.items():
            v = val(doc, src)
            if not v:
                continue
            fix = fixes.setdefault(ref, {})
            entry = log.setdefault(ref, {})
            if dst not in entry:
                entry[dst] = fix.get(dst)
            if fix.get(dst) != v:
                fix[dst] = v
                changed += 1
    with open(FIXES_PATH, "w", encoding="utf-8") as f:
        json.dump(fixes, f, ensure_ascii=False, indent=1)
    print(f"{len(edited)} edited properties, {changed} field changes written to fixes.json")


if __name__ == "__main__":
    main(sys.argv[1])
