#!/usr/bin/env python3
"""Build the folder that Cloudflare Pages publishes (dist/).

Cloudflare Pages settings:  Build command  python3 tools/build_cloudflare.py
                            Output folder  dist

What it does
1. Copies the public website into dist/ (never tools/, README, git files).
2. Turns internal links into clean URLs: about-us.html -> about-us, index.html -> ./
   Cloudflare already serves /about-us for about-us.html; without this step every
   internal link, canonical and sitemap entry would go through an extra redirect.
   The source files keep .html so they still open straight from the folder.
3. Writes dist/_redirects (301s from old eGO URLs) from every redirect list.
4. Writes dist/_headers (security headers and browser caching).
5. Adds the newsletter sign-up to the footer of every page (tools/newsletter/add_newsletter.py).
6. Writes dist/404.html. Without a 404 page Cloudflare would answer every unknown
   URL with the home page and status 200, which Google treats as duplicate pages.

Run it locally the same way to check the output: python3 tools/build_cloudflare.py
"""
import csv
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsletter"))
from add_newsletter import inject as add_newsletter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
SITE = "https://www.eliteworldestates.com"

# Not published.
SKIP_TOP = {"tools", "functions", "dist", "README.md", "node_modules", "__pycache__"}  # functions/ = Pages Functions, run by Cloudflare, not served as files
SKIP_EXT = {".py", ".pyc", ".csv", ".md"}

# Redirect lists: (file, from-column, to-column). Later lists win on a clash.
REDIRECT_LISTS = [
    ("tools/redirects.csv", "from", "to"),
    ("tools/towns/redirects.csv", "from", "to"),
    ("tools/ego/redirects.csv", "from", "to"),
    ("tools/old-site/redirects.csv", "from", "to"),  # every address in the old site's sitemap
]
# Covered by the dynamic rule /property-details/:slug/:id -> /property-details/:id (see
# tools/old-site/build_old_site_redirects.py), so one static line per listing id is enough.
PROPERTY_SLUG_RE = re.compile(r"^/property-details/[^/]+/\d+$")
MAX_STATIC, MAX_DYNAMIC = 2000, 100  # Cloudflare Pages Free limits

HEADERS = """\
/*
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-src https://www.google.com https://www.youtube.com https://www.youtube-nocookie.com; frame-ancestors 'self'; form-action 'self'; base-uri 'self'; object-src 'none'; upgrade-insecure-requests

/assets/*
  Cache-Control: public, max-age=2592000

/css/*
  Cache-Control: public, max-age=86400

/js/*
  Cache-Control: public, max-age=86400

/feeds/*
  Cache-Control: public, max-age=3600
  Access-Control-Allow-Origin: *

https://:project.pages.dev/*
  X-Robots-Tag: noindex
"""

# href/src/content/action attributes and sitemap <loc> values.
ATTR_RE = re.compile(r'((?:href|src|action|content)=")([^"]*)(")')
LOC_RE = re.compile(r"(<loc>|<xhtml:link[^>]*href=\")([^<\"]*)")
JSON_URL_RE = re.compile(r'("(?:@id|url|item|mainEntityOfPage)"\s*:\s*")([^"]*)(")')


def clean_url(url):
    """Drop .html / index.html from an internal URL; leave everything else alone."""
    if url.startswith(SITE):
        rest = url[len(SITE):]
    elif re.match(r"^[a-z][a-z0-9+.-]*:|^//|^#", url, re.I):
        return url  # other sites, mailto:, tel:, data:, #anchors
    elif " " in url:
        return url  # text, not a link
    else:
        rest = None
    path = url if rest is None else rest
    m = re.match(r"^([^?#]*)(.*)$", path)
    p, tail = m.group(1), m.group(2)
    if not p.endswith(".html"):
        return url
    if p == "index.html" or p.endswith("/index.html"):
        p = p[: -len("index.html")] or "./"
    else:
        p = p[: -len(".html")]
    return (SITE + p if rest is not None else p) + tail


def rewrite_html(text):
    text = ATTR_RE.sub(lambda m: m.group(1) + clean_url(m.group(2)) + m.group(3), text)
    text = JSON_URL_RE.sub(lambda m: m.group(1) + clean_url(m.group(2)) + m.group(3), text)
    return text


def copy_site():
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        top = rel.split(os.sep)[0]
        if rel != "." and (top in SKIP_TOP or top.startswith(".")):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_TOP]
        for name in filenames:
            if name.startswith(".") or (rel == "." and name in SKIP_TOP):
                continue
            if os.path.splitext(name)[1] in SKIP_EXT:
                continue
            src = os.path.join(dirpath, name)
            dst = os.path.join(DIST, rel, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if name.endswith(".html"):
                with open(src, encoding="utf-8") as f:
                    text = rewrite_html(add_newsletter(f.read()))
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(text)
            elif name.endswith(".xml") or name in ("llms.txt", "robots.txt"):
                with open(src, encoding="utf-8") as f:
                    text = f.read()
                text = re.sub(re.escape(SITE) + r"[^\s<\"')]*\.html", lambda m: clean_url(m.group(0)), text)
                with open(dst, "w", encoding="utf-8") as f:
                    f.write(text)
            else:
                shutil.copy2(src, dst)
            count += 1
    return count


def norm_path(url):
    if url.startswith(SITE):
        url = url[len(SITE):]
    elif url.startswith("https://eliteworldestates.com"):
        url = url[len("https://eliteworldestates.com"):]
    if not url.startswith("/"):
        url = "/" + url
    return url


def build_redirects():
    rules = {}
    for path, col_from, col_to in REDIRECT_LISTS:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            print(f"  note: {path} not found, skipped")
            continue
        with open(full, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                src, dst = (row.get(col_from) or "").strip(), (row.get(col_to) or "").strip()
                if not src or not dst:
                    continue
                src = norm_path(src).rstrip("/") or "/"
                if PROPERTY_SLUG_RE.match(src):
                    continue
                dst = clean_url(norm_path(dst))
                if src == dst.split("?")[0] or src + ".html" == dst:
                    continue
                if os.path.exists(os.path.join(DIST, src.lstrip("/") + ".html")) or os.path.exists(
                    os.path.join(DIST, src.lstrip("/"), "index.html")
                ):
                    print(f"  skipped {src}: a live page has this address")
                    continue
                rules[src] = dst
    # A redirect whose target is itself redirected: point straight at the end.
    # A target with a placeholder (:id) is filled in per request, so it is never flattened.
    for src in list(rules):
        if ":" in rules[src].split("?")[0]:
            continue
        seen, dst = {src}, rules[src]
        while dst.split("?")[0] in rules and dst not in seen:
            seen.add(dst)
            dst = rules[dst.split("?")[0]]
        rules[src] = dst
    static = [s for s in rules if "*" not in s and ":" not in s]
    dynamic = [s for s in rules if s not in static]
    lines = ["# Generated by tools/build_cloudflare.py - edit the CSV lists, not this file."]
    lines += [f"{s} {rules[s]} 301" for s in sorted(static)]
    lines += [f"{s} {rules[s]} 301" for s in sorted(dynamic)]
    with open(os.path.join(DIST, "_redirects"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  _redirects: {len(static)} static (limit {MAX_STATIC}), {len(dynamic)} dynamic (limit {MAX_DYNAMIC})")
    if len(static) > MAX_STATIC or len(dynamic) > MAX_DYNAMIC:
        sys.exit("ERROR: too many redirects for Cloudflare Pages; move the extra ones to Bulk Redirects")


def build_404():
    with open(os.path.join(ROOT, "terms-and-conditions.html"), encoding="utf-8") as f:
        page = add_newsletter(f.read())
    main = """<main class="legal-page">
  <div class="container legal">
    <h1>Page not found</h1>
    <p class="lead">Sorry, this page does not exist or has moved.</p>
    <p><a href="/properties-for-sale-in-spain">See all properties for sale in Spain</a></p>
    <p><a href="/">Go to the home page</a> · <a href="/contact-us">Contact us</a></p>
  </div>
</main>"""
    page = re.sub(r"<main.*?</main>", main, page, flags=re.S)
    page = re.sub(r"<title>.*?</title>", "<title>Page not found | Elite World Estates</title>", page)
    page = re.sub(r'\s*<meta name="description"[^>]*>', "", page)
    page = page.replace('content="index, follow"', 'content="noindex"')
    page = re.sub(r'\s*<link rel="canonical"[^>]*>', "", page)
    # Served at any depth, so every local link must start at the site root.
    page = ATTR_RE.sub(
        lambda m: m.group(1)
        + (m.group(2) if re.match(r"^([a-z]+:|/|#)", m.group(2)) else "/" + clean_url(m.group(2)).lstrip("./"))
        + m.group(3),
        page,
    )
    with open(os.path.join(DIST, "404.html"), "w", encoding="utf-8") as f:
        f.write(page)


def hide_from_search():
    """Keep every Cloudflare build out of Google unless it is the real live site.

    Cloudflare sets CF_PAGES=1 on its builds. Preview links (*.pages.dev) must never be
    indexed, or Google sees a duplicate of the whole site. The live site's production
    environment gets LIVE_SITE=1 (Pages > Settings > Variables) on launch day.
    Local builds (no CF_PAGES) are left as they are.
    """
    if os.environ.get("CF_PAGES") != "1" or os.environ.get("LIVE_SITE") == "1":
        return False
    with open(os.path.join(DIST, "_headers"), "a", encoding="utf-8") as f:
        f.write("\n/*\n  X-Robots-Tag: noindex, nofollow\n")
    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("# Preview copy of the new site: not for search engines.\nUser-agent: *\nDisallow: /\n")
    return True


def main():
    print("Building dist/ for Cloudflare Pages")
    n = copy_site()
    print(f"  copied {n} files")
    # Refresh the old-site 301 list first, so it always matches the current listings and pages.
    import subprocess
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "old-site", "build_old_site_redirects.py")], check=True)
    build_redirects()
    with open(os.path.join(DIST, "_headers"), "w", encoding="utf-8") as f:
        f.write(HEADERS)
    build_404()
    if hide_from_search():
        print("  PREVIEW build: noindex header + robots.txt Disallow (set LIVE_SITE=1 on the live site)")
    total = sum(len(fs) for _, _, fs in os.walk(DIST))
    print(f"  dist/ has {total} files (Cloudflare Free limit 20,000)")
    if total > 20000:
        sys.exit("ERROR: more than 20,000 files")


if __name__ == "__main__":
    main()
