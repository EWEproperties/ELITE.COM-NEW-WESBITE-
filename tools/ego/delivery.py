"""Delivery (completion) dates for the property cards.

eGO has no delivery date field: the date is written in the description ("Planned completion
date: June 2028"). This reads it from the English text (Polish/Spanish as fall back) and saves
tools/ego/delivery.json: {ref: {"label": "Q1 2028", "status": ...}}. The card generators
(tools/build_collections.py, tools/towns/build_town.py) show a badge for status "ok" only:
a future date or "Key ready". Dates already passed and "18 months from contract" are not shown.

Run: python3 tools/ego/delivery.py            (reads eGO with EGO_USERNAME / EGO_PASSWORD)
     python3 tools/ego/delivery.py dump.json  (a saved ListRealestateByPage dump)
To add or fix a date: write "Estimated completion: June 2028" in the eGO description, rerun.
"""
import csv
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "delivery.json")
_t = datetime.date.today()
NOW = (_t.year, _t.month)
MON = {m: i+1 for i, m in enumerate("january february march april may june july august september october november december".split())}
MON["dicember"] = 12; MON["dicembere"] = 12
PLM = dict(zip("stycz lut marz kwie maj czerw lip sierp wrze paźdz listop grud".split(), range(1,13)))
ESM = dict(zip("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(), range(1,13)))
ABBR = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
Q = {"first":1,"1st":1,"second":2,"2nd":2,"third":3,"3rd":3,"fourth":4,"4th":4,"last":4}
KEY = re.compile(r"\b(key[- ]?ready|ready to move in(?:to)? now|immediate(?:ly)? (?:delivery|available)|ready for immediate)", re.I)
TRIG = re.compile(r"(completion|acceptance|to be completed|ready for collection|oddani[ea]|entrega prevista|fecha prevista de entrega|deliver(?:y|ies)\b|handover|hand-over|keys? (?:will be )?(?:handed|delivered))", re.I)
NOISE = re.compile(r"delivered (fully|with|turnkey|furnished|equipped|key)|from initial concept to completion", re.I)

def parse(s):
    """Return (sortkey(y,m), label) of the earliest date in s, or None."""
    s = s.replace("–", "-")
    found = []
    for m in re.finditer(r"\b(?:Q([1-4])|(first|1st|second|2nd|third|3rd|fourth|4th|last) quarter(?: of)?)\s*(?:of\s*)?(20\d\d)", s, re.I):
        q = int(m.group(1)) if m.group(1) else Q[m.group(2).lower()]
        found.append(((int(m.group(3)), q*3-2), f"Q{q} {m.group(3)}", m.span()))
    for m in re.finditer(r"\b(first|1st|second|2nd) half(?: of)?\s*(20\d\d)", s, re.I):
        h = 1 if m.group(1).lower() in ("first","1st") else 2
        found.append(((int(m.group(2)), 1 if h==1 else 7), f"{'1st' if h==1 else '2nd'} half {m.group(2)}", m.span()))
    for m in re.finditer(r"\b(?:(\d{1,2})\s+)?(" + "|".join(MON) + r")(?:\s*(?:/|,|and|or|-)\s*(?:" + "|".join(MON) + r"))*\s*(?:\d{1,2}(?:st|nd|rd|th)?)?\s*,?\s*(?:de\s+)?(20\d\d)", s, re.I):
        mo = MON[m.group(2).lower()]
        found.append(((int(m.group(3)), mo), f"{ABBR[mo-1]} {m.group(3)}", m.span()))
    for m in re.finditer(r"\b(end|late|mid|middle|early|beginning|start|spring|summer|autumn|fall|winter)(?:[- ]of)?[- ]?(?:the year )?(20\d\d)", s, re.I):
        w = m.group(1).lower()
        mo, lab = {"end":(12,"End"),"late":(12,"End"),"mid":(6,"Mid"),"middle":(6,"Mid"),"early":(1,"Early"),"beginning":(1,"Early"),"start":(1,"Early"),
                   "spring":(4,"Spring"),"summer":(7,"Summer"),"autumn":(10,"Autumn"),"fall":(10,"Autumn"),"winter":(12,"Winter")}[w]
        found.append(((int(m.group(2)), mo), f"{lab} {m.group(2)}", m.span()))
    for m in re.finditer(r"\b(" + "|".join(PLM) + r")\w*\s+(20\d\d)", s, re.I):
        mo = PLM[m.group(1).lower()]; found.append(((int(m.group(2)), mo), f"{ABBR[mo-1]} {m.group(2)}", m.span()))
    for m in re.finditer(r"\b(" + "|".join(ESM) + r")\s+(?:de\s+)?(20\d\d)", s, re.I):
        mo = ESM[m.group(1).lower()]; found.append(((int(m.group(2)), mo), f"{ABBR[mo-1]} {m.group(2)}", m.span()))
    taken = [f[2] for f in found]
    for m in re.finditer(r"\b(20[2-3]\d)\b", s):
        if not any(a <= m.start() < b for a, b in taken):
            found.append(((int(m.group(1)), 12), m.group(1), m.span()))
    if not found:
        rel = re.search(r"(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*months", s, re.I)
        if rel:
            return None, f"{rel.group(0)}"
        if re.search(r"\bready\b", s, re.I):
            return (0, 0), "Key ready"
        return None
    found.sort(key=lambda f: f[0])
    k, lab, _ = found[0]
    many = len({f[1] for f in found}) > 1
    return k, ("From " + lab if many else lab)



def extract(rows):
    out = {}
    for r in rows:
        ref = r["reference"]
        t = (r.get("description") or {}).get("EN-GB") or ""
        lines = [l.strip() for l in t.replace("\r", "").split("\n")]
        label = key = src = None; note = ""
        for i, l in enumerate(lines):
            if not TRIG.search(l) or NOISE.search(l):
                continue
            seg = l
            p = parse(l)
            if p is None and i + 1 < len(lines):  # heading line, the date is on the next line(s)
                nxt = " ".join(x for x in lines[i+1:i+4] if x)[:200]
                p = parse(nxt); seg = l + " / " + nxt
            if p:
                key, label = p; src = seg[:220]; break
        if not label:
            for L in ("PL-PL", "ES-ES"):
                lines = [l.strip() for l in ((r.get("description") or {}).get(L) or "").replace("\r", "").split("\n")]
                for i, l in enumerate(lines):
                    if TRIG.search(l):
                        p = parse(l) or (parse(" ".join(lines[i+1:i+3])) if i + 1 < len(lines) else None)
                        if p and p[1] != "Key ready":
                            key, label = p; src = f"[{L[:2]}] " + l[:200]; break
                if label: break
        if not label and KEY.search(t[:600]):
            key, label, src = (0, 0), "Key ready", KEY.search(t).group(0)
        if not label:
            continue
        status = "ok"
        if key is None:
            status = "relative (needs a real date)"
        elif key != (0, 0) and key[0] < 2020:
            status = "check"
        elif key != (0, 0) and key <= NOW:
            status = "date passed: key ready now?"
        out[ref] = {"label": label, "status": status, "text": src}

    return out


# ---------- card badge ----------

WORDS = {
    "de": {"Delivery": "Fertigstellung", "Key ready": "Bezugsfertig", "from": "ab", "End": "Ende", "Mid": "Mitte",
           "Early": "Anfang", "Spring": "Frühjahr", "Summer": "Sommer", "Autumn": "Herbst", "Winter": "Winter",
           "1st half": "1. Halbjahr", "2nd half": "2. Halbjahr", "Mar": "März", "May": "Mai", "Oct": "Okt", "Dec": "Dez"},
    "es": {"Delivery": "Entrega", "Key ready": "Llave en mano", "from": "desde", "End": "fin", "Mid": "mediados",
           "Early": "inicio", "Spring": "primavera", "Summer": "verano", "Autumn": "otoño", "Winter": "invierno",
           "1st half": "1er semestre", "2nd half": "2º semestre", "Q1": "T1", "Q2": "T2", "Q3": "T3", "Q4": "T4",
           "Jan": "ene", "Apr": "abr", "Aug": "ago", "Dec": "dic", "Sep": "sept"},
}
_cache = None


def label(ref, lang="en"):
    global _cache
    if _cache is None:
        _cache = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    d = _cache.get(ref)
    if not d or d["status"] != "ok":
        return ""
    lab = d["label"]
    if lab == "Key ready":
        text = "Key ready"
    else:
        frm = lab.startswith("From ")
        text = "Delivery " + ("from " if frm else "") + lab[5:] if frm else "Delivery " + lab
    w = WORDS.get(lang)
    if w:
        keys = sorted(w, key=len, reverse=True)
        text = re.sub(r"\b(" + "|".join(map(re.escape, keys)) + r")\b", lambda m: w[m.group(1)], text)
    return text


def badge(ref, lang="en"):
    t = label(ref, lang)
    return f'<span class="tcard-due">{html.escape(t)}</span>' if t else ""


def main(argv):
    if len(argv) > 1:
        rows = json.load(open(argv[1], encoding="utf-8"))
    else:
        sys.path.insert(0, HERE)
        from fetch_ego import Global
        g = Global(os.environ["EGO_USERNAME"], os.environ["EGO_PASSWORD"])
        rows = list(g.pages())
    out = extract(rows)
    json.dump(dict(sorted(out.items())), open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(rows), "listings,", len(out), "with a date in the text:", dict(Counter(v["status"] for v in out.values())))


if __name__ == "__main__":
    main(sys.argv)
