"""Point every link to an old eGO property page at the new static property page.

Town, golf, blog and home pages were made while only the old eGO site had property
pages, so their cards link to https://www.eliteworldestates.com/<lang>/property-details/<slug>/<id>.
This rewrites those links to the new properties/<slug>.html page (relative link),
using the website id at the end of the old address and tools/ego/redirects.csv.
Links to listings that are no longer in eGO are left alone and listed.

Run it after build_properties.py and after any page generator:
  python3 tools/link_properties.py
"""
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = re.compile(r'https://www\.eliteworldestates\.com/(?:[a-z]{2}-[a-z]{2}/)?property-details/(?:[^"\'\s<>]*/)?(\d+)/?(?=["\'\s<>])')
LD = re.compile(r'<script type="application/ld\+json">.*?</script>', re.S)
SITE = "https://www.eliteworldestates.com"
SKIP_DIRS ={".git", "tools", "node_modules", "feeds"}


def new_pages():
    pages = {}
    with open(os.path.join(ROOT, "tools", "ego", "redirects.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m = re.search(r"/(\d+)$", row["from"])
            if m:
                pages[m.group(1)] = row["to"].lstrip("/")
    return pages


def main():
    pages = new_pages()
    changed, links, missing = 0, 0, {}
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(folder, name)
            text = open(path, encoding="utf-8").read()
            here = os.path.relpath(folder, ROOT)

            def repl(m):
                nonlocal links
                target = pages.get(m.group(1))
                if not target:
                    missing.setdefault(m.group(1), set()).add(os.path.relpath(path, ROOT))
                    return m.group(0)
                links += 1
                return os.path.relpath(target, here).replace(os.sep, "/")

            def repl_abs(m):
                nonlocal links
                target = pages.get(m.group(1))
                if not target:
                    missing.setdefault(m.group(1), set()).add(os.path.relpath(path, ROOT))
                    return m.group(0)
                links += 1
                return SITE + "/" + target

            # structured data needs full addresses, page links can be relative
            new = LD.sub(lambda b: OLD.sub(repl_abs, b.group(0)), text)
            new = OLD.sub(repl, new)
            if new != text:
                open(path, "w", encoding="utf-8").write(new)
                changed += 1
    print(f"{links} links in {changed} pages now point to the new property pages")
    if missing:
        print(f"{len(missing)} listings not in eGO any more (links left as they are):")
        for i, where in sorted(missing.items()):
            print(f"  {i}: {', '.join(sorted(where)[:3])}{' …' if len(where) > 3 else ''}")


if __name__ == "__main__":
    sys.exit(main())
