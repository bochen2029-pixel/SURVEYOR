#!/usr/bin/env python3
"""crosswalk/pins.py - the pin store: a quote that does not byte-match does not exist.

Law B6, made mechanical. Ported from REGISTRAR tools/cite.py @ 2026-08-26 (same author,
MIT, attributed) per law D7; SPEC section 7 names it as the crosswalk's pin store.
SURVEYOR changes: a sources REGISTRY (crosswalk/sources.yml) instead of a bare manifest;
MAPPING objects (crosswalk/mappings/*.map.yml) that bind an encoded check to the clause
it claims, typed and expiring like every other patch row; a coverage fold that prints
what CANNOT be verified today; and an edition-diff engine.

THE PROBLEM. A fabricated citation and a correct one read identically: both name a
plausible authority, a plausible section, and a plausible claim. So do not read them,
check them. A model can invent a policy section number; it cannot invent a verbatim
quote that matches a hash-pinned file on this disk. Acceptance becomes a string
comparison rather than an act of trust.

WHAT THIS DOES NOT DO. It verifies the quote EXISTS in the source. It does not verify
the quote ESTABLISHES the claim - that is a judgment, it belongs to the quality director
at the R1 gate, and this tool deliberately does not pretend to make it. Passing here
means "not fabricated". It does not mean "correct".

THE CORPUS IS NOT IN THIS REPOSITORY. Regulatory documents belong to their publishers;
only the registry (ids, urls, sha256, byte counts) and short attributed quotes are
committed. The loader finds a local corpus via, in order: $SURVEYOR_CORPUS, the path in
_local/corpus-path.txt, or crosswalk/corpus/. With no corpus present the gate reports
CANNOT-EVALUATE and says so - it never reports PASS for quotes it could not read.

CLI:
  python crosswalk/pins.py --check              verify every mapping, byte-exact
  python crosswalk/pins.py --sources            the registry and whether each source is present
  python crosswalk/pins.py --coverage           which checks are pinned, and which cannot be
  python crosswalk/pins.py --find "text" [--source ID] [--window N]   locate a passage to quote
  python crosswalk/pins.py --diff OLD NEW       which mappings an edition change disturbs
Stdlib only. No model (the clocks battery's no-model scan covers this directory too).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "crosswalk"
SOURCES_YML = HERE / "sources.yml"
MAPPINGS_DIR = HERE / "mappings"
EDITIONS_DIR = HERE / "editions"
CHECKS_DIR = ROOT / "floor" / "checks"
CATALOG = ROOT / "floor" / "CATALOG.md"

OK, MISSING, MISMATCH, UNPINNED, CHANGED, WARN = (
    "OK", "SOURCE-MISSING", "QUOTE-NOT-FOUND", "SOURCE-UNPINNED", "SOURCE-CHANGED", "CHECK-CURRENCY")
MAPPING_TYPES = {"implements", "constrains", "reports-under", "silent"}
REQUIRED_MAPPING_KEYS = ("id", "check", "source", "locator", "type", "quote", "establishes", "expires", "inverse")
MIN_QUOTE = 24

# A quote may elide intervening text with [...] - the way a legal citation always has.
# Both halves must still be verbatim, and the elided span must be shorter than
# ELISION_MAX and is PRINTED in the verdict, so a reader can see exactly what was cut.
# This exists because extraction inserts running headers mid-sentence at page breaks
# ("...the potential deceased [OPTN Policies / Policy 2 / Page 34] donor."), and the
# alternative - quoting up to the page break - produces citations that stop mid-phrase.
# It cannot launder a fabrication: an invented bridge between two real fragments would
# have to appear, verbatim and in order, within the window.
ELISION = "[...]"
ELISION_MAX = 200

# Language meaning a passage may be real and no longer in force. Inherited from the
# donor tool, which found it the hard way: 42 CFR 486.318 still carries an expired
# three-measure regime in the codified text, and the byte-match gate PASSES a citation
# to it - the passage exists, it is merely superseded. So the gate warns, because it
# genuinely cannot decide.
SUNSET = (r"effective until", r"expire[sd]?\s+(?:on|at)", r"no longer (?:in effect|applicable)",
          r"until\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d",
          r"superseded by")


# ---------------------------------------------------------------- normalisation
def normalise(s: str) -> str:
    """Fold the differences PDF extraction introduces and nobody means: unicode form,
    curly quotes, dashes, soft hyphens, runs of whitespace. Deliberately NOT case-folded
    and NOT punctuation-stripped: a quote that only matches after aggressive mangling is
    not a quote."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("­", "")
    s = re.sub(r"[‘’‛]", "'", s)
    s = re.sub(r"[“”‟]", '"', s)
    s = re.sub(r"[‐-―−]", "-", s)
    s = re.sub(r"\[\[PAGE \d+\]\]", " ", s)          # extraction page markers
    return re.sub(r"\s+", " ", s).strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- the registry
def _scalar(val: str):
    val = val.strip()
    if val.count('"') % 2 == 0 and val.count("'") % 2 == 0 and " #" in val:
        val = val.split(" #", 1)[0].rstrip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    return val


def load_sources() -> dict[str, dict]:
    """crosswalk/sources.yml: flat `key: value` lines; a line starting `id:` at column 0
    opens a new source block. Same dialect as the checks - flatness is a feature."""
    out: dict[str, dict] = {}
    cur: dict | None = None
    if not SOURCES_YML.exists():
        return out
    for raw in SOURCES_YML.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            raise ValueError(f"sources.yml: not key:value - {raw!r}")
        key, val = raw.split(":", 1)
        key = key.strip()
        if key == "id" and not raw.startswith((" ", "\t")):
            cur = {"id": _scalar(val)}
            out[cur["id"]] = cur
        elif cur is None:
            raise ValueError("sources.yml: a key appears before the first `id:` block")
        else:
            cur[key] = _scalar(val)
    return out


def corpus_roots() -> tuple[list[Path], str]:
    """The local corpora, found without ever committing a machine path to this repo.
    Several roots, searched in order: $SURVEYOR_CORPUS (may be os.pathsep-separated),
    each line of _local/corpus-path.txt, then crosswalk/corpus/. Plural because a site
    keeps its own pinned sources beside, not inside, whatever it inherited."""
    roots, how = [], []
    for part in (os.environ.get("SURVEYOR_CORPUS") or "").split(os.pathsep):
        if part and Path(part).is_dir():
            roots.append(Path(part))
            how.append("$SURVEYOR_CORPUS")
    pointer = ROOT / "_local" / "corpus-path.txt"
    if pointer.exists():
        for line in pointer.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and Path(line).is_dir():
                roots.append(Path(line))
                how.append("_local/corpus-path.txt")
    local = HERE / "corpus"
    if local.is_dir():
        roots.append(local)
        how.append("crosswalk/corpus/")
    return roots, (" + ".join(dict.fromkeys(how)) or "not found")


def corpus_root() -> tuple[Path | None, str]:
    roots, how = corpus_roots()
    return (roots[0] if roots else None), how


def find_source_file(name: str) -> Path | None:
    for r in corpus_roots()[0]:
        if (r / name).exists():
            return r / name
    return None


_TEXT_CACHE: dict[str, tuple[str | None, str]] = {}


def source_text(sid: str, sources: dict[str, dict]) -> tuple[str | None, str]:
    """(normalised text, status). Verifies the file still matches its pin before use."""
    if sid in _TEXT_CACHE:
        return _TEXT_CACHE[sid]
    src = sources.get(sid)
    if not src:
        res = (None, UNPINNED)
    else:
        path = find_source_file(src["file"])
        if path is None:
            res = (None, MISSING)
        elif sha256_file(path) != src.get("sha256"):
            res = (None, CHANGED)
        else:
            res = (normalise(path.read_text(encoding="utf-8", errors="replace")), OK)
    _TEXT_CACHE[sid] = res
    return res


# ---------------------------------------------------------------- the mappings
def locate_elided(needle: str, text: str) -> tuple[int, int | str, str]:
    """A quote with [...] in it: every fragment verbatim, in order, each gap under
    ELISION_MAX. Returns (start, span, elided-text) or (-1, why, '')."""
    parts = [p.strip() for p in needle.split(ELISION)]
    if any(not p for p in parts):
        return -1, "an elision must have text on both sides", ""
    start = text.find(parts[0])
    if start < 0:
        return -1, "the passage before the elision does not occur in the source", ""
    pos, gaps = start + len(parts[0]), []
    for part in parts[1:]:
        nxt = text.find(part, pos)
        if nxt < 0:
            return -1, f"the passage after an elision does not occur later in the source: {part[:40]!r}", ""
        gap = text[pos:nxt]
        if len(gap) > ELISION_MAX:
            return -1, (f"the elision would swallow {len(gap)} characters (limit {ELISION_MAX}) - "
                        f"quote the passage or cite two clauses, do not bridge them"), ""
        gaps.append(gap.strip())
        pos = nxt + len(part)
    return start, pos - start, " | ".join(gaps)


def load_mappings() -> list[dict]:
    sys.path.insert(0, str(ROOT / "floor"))
    import engine                                    # the same flat-YAML reader the checks use
    out = []
    for p in sorted(MAPPINGS_DIR.glob("*.map.yml")) if MAPPINGS_DIR.exists() else []:
        m = engine.load_check_yml(p)
        m["_file"] = p.name
        out.append(m)
    return out


def mapping_schema_problems(m: dict) -> list[str]:
    probs = []
    silent = m.get("type") == "silent"
    for k in REQUIRED_MAPPING_KEYS:
        if silent and k == "quote":
            continue                    # a mapping that asserts silence has nothing to quote
        if k not in m or m[k] in ("", None):
            probs.append(f"missing {k}")
    if m.get("type") not in MAPPING_TYPES:
        probs.append(f"type {m.get('type')!r} not in {sorted(MAPPING_TYPES)}")
    cid = str(m.get("check", ""))
    if cid and not (CHECKS_DIR / f"{cid}.check.yml").exists():
        probs.append(f"check {cid} does not exist")
    if m.get("type") == "silent":
        if str(m.get("quote", "")).strip():
            probs.append("a `silent` mapping asserts the sources say nothing - it must carry no quote")
    elif len(normalise(str(m.get("quote", "")))) < MIN_QUOTE:
        probs.append(f"quote is under {MIN_QUOTE} characters - too short to be evidence of anything")
    return probs


def verify(m: dict, sources: dict[str, dict]) -> tuple[str, str]:
    """One mapping. (status, detail)."""
    probs = mapping_schema_problems(m)
    if probs:
        return MISMATCH, "; ".join(probs)
    if m["type"] == "silent":
        # A claim that the regulation is SILENT is checkable after all, and it MUST be
        # checked. S6 found this the hard way: an S5 silent mapping asserted that 21 CFR
        # 1271 contained no seven-day specimen window and listed five search terms in its
        # `searched:` field - of which exactly one had actually been run. The regulation
        # says "up to 7 days before or after recovery" at 1271.80(b), and the mapping had
        # recorded a search that was never performed. A field a human types is a claim;
        # a field the tool executes is evidence. So every term is now run, and one hit
        # rejects the mapping.
        terms = [t.strip() for t in str(m.get("searched", "")).split("|") if t.strip()]
        if not terms:
            return MISMATCH, "a `silent` mapping must record what was searched (`searched:`, terms separated by |)"
        # A single generic word is not a search for a rule. "annual" occurs in any CFR
        # part; "30 minutes" occurs in any clinical policy; finding them proves nothing
        # and NOT finding them would have proved nothing either. A term must be a phrase
        # specific enough that a hit would actually mean the rule exists.
        vague = [t for t in terms if " " not in t.strip() or len(t.strip()) < 10]
        if vague:
            return MISMATCH, (f"search terms too generic to be evidence of absence: {vague} - "
                              f"a silent mapping must search PHRASES (>= 2 words, >= 10 chars) that "
                              f"would only appear if the rule were there")
        text, status = source_text(m["source"], sources)
        if text is None:
            return status, f"source {m['source']!r} not available - silence cannot be asserted unchecked"
        hits = []
        for t in terms:
            i = text.lower().find(normalise(t).lower())
            if i >= 0:
                hits.append((t, text[max(0, i - 60): i + 140]))
        if hits:
            t, ctx = hits[0]
            return MISMATCH, (f"NOT SILENT: searching {m['source']} for {t!r} finds it "
                              f"({len(hits)} of {len(terms)} terms hit) - ...{ctx.strip()}...")
        return OK, (f"silent: {len(terms)} search term(s) run against {m['source']}, "
                    f"none occurs (mechanically checked, not asserted)")
    text, status = source_text(m["source"], sources)
    if text is None:
        return status, f"source {m['source']!r} not available to check against"
    needle = normalise(str(m["quote"]))
    elided = None
    if ELISION in needle:
        i, span, elided = locate_elided(needle, text)
        if i < 0:
            return MISMATCH, span
    else:
        i, span = text.find(needle), len(needle)
    if i >= 0:
        window = text[max(0, i - 2500): i + span + 2500]
        for pat in SUNSET:
            hit = re.search(pat, window, re.I)
            if not hit:
                continue
            conf = m.get("currency_confirmed")
            if conf:
                return OK, f"verbatim; sunset language nearby, confirmed in force - {conf}"
            return WARN, (f"verbatim in {m['source']}, but nearby text reads {hit.group(0)!r} "
                          f"- CONFIRM IT IS STILL IN FORCE")
        if elided is not None:
            return OK, f"verbatim in {m['source']} across an elision of {len(elided)} chars: {elided!r}"
        return OK, f"verbatim in {m['source']} ({len(needle)} chars)"
    head = needle[:40]
    if head in text:
        return MISMATCH, f"first 40 chars occur in {m['source']}, the full quote does not - truncated or altered"
    return MISMATCH, f"not present in {m['source']} - the passage does not exist as quoted"


def check_all() -> dict:
    sources = load_sources()
    maps = load_mappings()
    rows, bad, warned, unavailable = [], 0, 0, 0
    for m in maps:
        status, detail = verify(m, sources)
        rows.append({"id": m.get("id"), "check": m.get("check"), "type": m.get("type"),
                     "locator": m.get("locator"), "status": status, "detail": detail})
        if status in (OK,):
            pass
        elif status == WARN:
            warned += 1
        elif status in (MISSING, UNPINNED, CHANGED):
            unavailable += 1
        else:
            bad += 1
    return {"rows": rows, "mappings": len(maps), "bad": bad, "warned": warned,
            "unavailable": unavailable, "corpus": corpus_root()[1]}


# ---------------------------------------------------------------- coverage
def catalog_ids() -> list[str]:
    return sorted(set(re.findall(r"\bSV-\d{3}\b", CATALOG.read_text(encoding="utf-8"))))


def coverage() -> dict:
    """The honest half: which encoded checks have a byte-checkable authority today, and
    which name a source this corpus does not contain. The crosswalk's first job is to say
    what it cannot verify."""
    sys.path.insert(0, str(ROOT / "floor"))
    import engine
    maps = load_mappings()
    by_check: dict[str, list[dict]] = {}
    for m in maps:
        by_check.setdefault(str(m.get("check")), []).append(m)
    sources = load_sources()
    known = set(sources)
    rows = []
    for cid in catalog_ids():
        yml = CHECKS_DIR / f"{cid}.check.yml"
        if not yml.exists():
            continue
        auth = str(engine.load_check_yml(yml).get("authority", ""))
        cited = sorted({sid for sid, s in sources.items() if any(t and t.lower() in auth.lower()
                                                                for t in str(s.get("names", "")).split("|"))})
        unpinnable = sorted({t.strip() for t in re.findall(r"(FDA 21 CFR 1271[\w.()]*|AATB[\w \-]*)", auth)})
        rows.append({"check": cid, "mapped": len(by_check.get(cid, [])), "sources_named": cited,
                     "not_in_corpus": unpinnable, "layer_authority": auth[:90]})
    mapped = sum(1 for r in rows if r["mapped"])
    named_only = sum(1 for r in rows if not r["mapped"] and r["sources_named"])
    outside = sum(1 for r in rows if not r["mapped"] and not r["sources_named"] and r["not_in_corpus"])
    return {"rows": rows, "checks": len(rows), "mapped": mapped, "named_but_unmapped": named_only,
            "authority_outside_corpus": outside, "known_sources": sorted(known)}


# ---------------------------------------------------------------- the edition diff
def load_edits(path: Path) -> list[dict]:
    """An edit list: blocks of `from:` / `to:` (flat, same dialect). This is how a NEXT
    EDITION is represented when we do not have one to download - the edits are committed
    and readable, the regulator's text is not redistributed, and the resulting edition is
    rebuilt deterministically at diff time."""
    edits, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, val = raw.split(":", 1)
        key, val = key.strip(), _scalar(val)
        if key == "from":
            cur = {"from": val}
            edits.append(cur)
        elif cur is not None:
            cur[key] = val
    return edits


def load_edition(name: str, base: str | None = None) -> tuple[str | None, str]:
    """An edition is: a source id in the registry, a text file under crosswalk/editions/
    or in the corpus, or an `.edits.yml` applied to `base`. Always the same normalisation,
    so a diff compares meaning-bearing text rather than line wrapping."""
    sources = load_sources()
    if name in sources:
        text, status = source_text(name, sources)
        return text, f"{name} ({status})"
    if name.endswith(".edits.yml"):
        p = EDITIONS_DIR / name if (EDITIONS_DIR / name).exists() else Path(name)
        if not p.exists() or base is None:
            return None, name
        text, _ = load_edition(base)
        if text is None:
            return None, name
        applied = 0
        for e in load_edits(p):
            src, dst = normalise(str(e["from"])), normalise(str(e.get("to", "")))
            if src not in text:
                return None, f"{p.name}: an edit's `from` is not in {base}: {src[:50]!r}"
            text = text.replace(src, dst)
            applied += 1
        return text, f"{base} + {p.name} ({applied} edits)"
    for p in (EDITIONS_DIR / name, EDITIONS_DIR / f"{name}.txt"):
        if p.exists():
            return normalise(p.read_text(encoding="utf-8", errors="replace")), str(p.relative_to(ROOT).as_posix())
    f = find_source_file(name)
    if f:
        return normalise(f.read_text(encoding="utf-8", errors="replace")), f"corpus/{name}"
    return None, name


def diff_edition(old_name: str, new_name: str) -> dict:
    """Which mappings does an edition change disturb? For every mapping whose source is
    the old edition: does its quote still byte-match the new one? A quote that no longer
    matches is a mapping whose check may now cite a clause that has moved, been reworded,
    or been removed - and it enters the human review queue. Nothing is auto-applied
    (SPEC section 7: draft diffs, review, mount under signature or reject with a reason)."""
    old, old_path = load_edition(old_name)
    new, new_path = load_edition(new_name, base=old_name)
    if old is None or new is None:
        return {"error": f"edition not resolvable: {old_path if old is None else new_path}"}
    maps = load_mappings()
    def present(q: str, text: str) -> bool:
        """The same locator verification uses - an elided quote must be tested the same
        way here, or a mapping whose quote spans a page break is silently reported as
        unrelated to every edition change (found while running the fixture)."""
        if ELISION in q:
            return locate_elided(q, text)[0] >= 0
        return q in text

    intact, disturbed, unrelated = [], [], []
    for m in maps:
        if m.get("type") == "silent":
            continue
        q = normalise(str(m.get("quote", "")))
        in_old, in_new = present(q, old), present(q, new)
        row = {"id": m.get("id"), "check": m.get("check"), "locator": m.get("locator")}
        if not in_old:
            unrelated.append(row)
        elif in_new:
            intact.append(row)
        else:
            head = q.split(ELISION)[0][:40]
            row["how"] = ("reworded or renumbered - the opening survives" if head in new
                          else "the passage is gone from the new edition")
            disturbed.append(row)
    return {"old": old_path, "new": new_path, "intact": intact, "disturbed": disturbed,
            "unrelated": unrelated, "checks_to_review": sorted({r["check"] for r in disturbed})}


# ---------------------------------------------------------------- find
def find(term: str, sid: str | None, window: int) -> int:
    sources = load_sources()
    ids = [sid] if sid else sorted(sources)
    n = 0
    for s in ids:
        text, status = source_text(s, sources)
        if text is None:
            print(f"[{s}] {status}")
            continue
        for mm in re.finditer(re.escape(normalise(term)), text, re.I):
            a, b = max(0, mm.start() - window), min(len(text), mm.end() + window)
            print(f"\n--- {s} @{mm.start()}\n{text[a:b]}")
            n += 1
            if n >= 12:
                print("\n(stopping at 12 hits)")
                return n
    if not n:
        print(f"no hit for {term!r}")
    return n


# ---------------------------------------------------------------- CLI
def main(argv: list[str]) -> int:
    sources = load_sources()
    root, how = corpus_root()

    if "--sources" in argv:
        print(f"corpus: {how}" + (f" -> {root}" if root else " (absent: quotes cannot be checked here)"))
        for sid, s in sorted(sources.items()):
            text, status = source_text(sid, sources)
            print(f"  {sid:<26} {str(s.get('sha256', ''))[:16]}...  {str(s.get('bytes', '')):>9} B  "
                  f"{status:<14} {s.get('effective', '')}")
        return 0

    if "--find" in argv:
        i = argv.index("--find")
        sid = argv[argv.index("--source") + 1] if "--source" in argv else None
        win = int(argv[argv.index("--window") + 1]) if "--window" in argv else 260
        find(argv[i + 1], sid, win)
        return 0

    if "--diff" in argv:
        i = argv.index("--diff")
        d = diff_edition(argv[i + 1], argv[i + 2])
        if "error" in d:
            print(d["error"])
            return 2
        print(f"edition diff: {d['old']} -> {d['new']}")
        print(f"  intact    {len(d['intact'])}\n  disturbed {len(d['disturbed'])}\n  unrelated {len(d['unrelated'])}")
        for r in d["disturbed"]:
            print(f"  REVIEW  {r['check']}  {r['locator']}  - {r['how']}")
        if d["checks_to_review"]:
            print("\nchecks entering the review queue: " + ", ".join(d["checks_to_review"]))
            print("Nothing is auto-applied: a diff is a draft for a human signature (SPEC section 7).")
        return 0

    if "--coverage" in argv:
        c = coverage()
        print(f"{c['mapped']}/{c['checks']} encoded checks carry a byte-checked mapping")
        print(f"{c['named_but_unmapped']} name a pinned source in their authority but have no mapping yet")
        print(f"{c['authority_outside_corpus']} rest on an authority this corpus does not contain\n")
        print(f"{'check':<8}{'maps':<6}{'sources named':<28}not in corpus")
        for r in c["rows"]:
            print(f"{r['check']:<8}{r['mapped']:<6}{','.join(r['sources_named'])[:26]:<28}{','.join(r['not_in_corpus'])[:40]}")
        return 0

    res = check_all()
    if "--json" in argv:
        print(json.dumps(res, indent=1))
        return 1 if res["bad"] else 0
    print(f"corpus: {res['corpus']}")
    for r in res["rows"]:
        mark = {OK: "ok    ", WARN: "WARN  "}.get(r["status"], "REJECT")
        print(f"  {mark}  {str(r['check']):<8}{str(r['locator']):<42} {r['detail']}")
    ok = res["mappings"] - res["bad"] - res["unavailable"]
    print(f"\n{ok}/{res['mappings']} mappings verify byte-exact against pinned sources")
    if res["warned"]:
        print(f"{res['warned']} carry sunset language nearby: a passage can be REAL AND EXPIRED, and this")
        print("gate cannot tell the difference - so it says so rather than guessing.")
    if res["unavailable"]:
        print(f"{res['unavailable']} could not be checked (source absent on this machine) - NOT a pass.")
    if res["bad"]:
        print(f"{res['bad']} REJECTED. A quote that does not appear in its source is a fabrication,")
        print("however plausible it reads. It does not enter the crosswalk.")
    else:
        print("\nWhat this means: every quote EXISTS in its source. Whether each quote ESTABLISHES")
        print("its check's authority is a separate judgment, and it belongs to the quality director.")
    return 1 if res["bad"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
