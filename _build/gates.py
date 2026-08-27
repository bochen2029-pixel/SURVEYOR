#!/usr/bin/env python3
"""gates.py - the build's own floor: deterministic gates on the repo itself.

Three-state honesty: every gate reports PASS, FAIL, or CANNOT-EVALUATE.
Exit code 1 if any gate FAILs, or if G-PRIVACY cannot evaluate (fail closed).

Usage:
  python _build/gates.py            # run gates, print table
  python _build/gates.py --record   # also append verdict events to the tape,
                                    # then regenerate the folds

Gates (v0):
  G-FOLD     folds on disk match a fresh deterministic render of the tape
  G-PRIVACY  no denylisted term (from _local/denylist.txt) outside _local/
  G-CATALOG  every SV- check is either honestly UNENCODED or fully encoded
             (check.yml + at least one pass* and one fail* fixture)
Stdlib only.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fold  # noqa: E402

TAPE = ROOT / "_build" / "TAPE.jsonl"
DENYLIST = ROOT / "_local" / "denylist.txt"
CATALOG = ROOT / "floor" / "CATALOG.md"
CHECKS_DIR = ROOT / "floor" / "checks"
FIXTURES_DIR = ROOT / "floor" / "fixtures"

SKIP_DIRS = {"_local", ".git", "__pycache__", "node_modules", ".chunks"}
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".html", ".json", ".txt", ".js", ".css", ".csv"}


def gate_fold():
    events = fold.read_tape()
    want_state, want_board = fold.render(events)
    have_state = fold.STATE.read_text(encoding="utf-8") if fold.STATE.exists() else ""
    have_board = fold.BOARD.read_text(encoding="utf-8") if fold.BOARD.exists() else ""
    if want_state == have_state and want_board == have_board:
        return "PASS", "folds match tape"
    return "FAIL", "STATE.md/BOARD.md stale or hand-edited - run: python _build/fold.py"


def load_denylist():
    """Lines: term per line. '!' prefix = warn-only. '#' = comment.
    ALL-CAPS terms match case-sensitively at word boundaries; others case-insensitive."""
    hard, warn = [], []
    for line in DENYLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        (warn if line.startswith("!") else hard).append(line.lstrip("!").strip())
    return hard, warn


def term_regex(term):
    esc = re.escape(term)
    if term.isupper():
        return re.compile(rf"\b{esc}\b")
    return re.compile(rf"\b{esc}\b", re.IGNORECASE)


def gate_privacy():
    if not DENYLIST.exists():
        return "CANNOT-EVALUATE", "no _local/denylist.txt - privacy gate fails closed"
    hard, warn = load_denylist()
    hard_rx = [(t, term_regex(t)) for t in hard]
    warn_rx = [(t, term_regex(t)) for t in warn]
    hard_hits, warn_hits = [], []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = p.relative_to(ROOT).as_posix()
        for i, line in enumerate(text.splitlines(), 1):
            for t, rx in hard_rx:
                if rx.search(line):
                    hard_hits.append(f"{rel}:{i} [{t}]")
            for t, rx in warn_rx:
                if rx.search(line):
                    warn_hits.append(f"{rel}:{i} [{t}]")
    if hard_hits:
        # Redact the matched terms themselves: verdict details land on the tape and
        # in the public folds, and must never echo a denylisted name (law C1).
        locs = "; ".join(h.split(" [")[0] for h in hard_hits[:6])
        return "FAIL", f"{len(hard_hits)} hard hit(s) [terms redacted]: {locs}"
    note = f"clean ({len(warn_hits)} warn-tier hits)" if warn_hits else "clean"
    if warn_hits:
        note += ": " + "; ".join(warn_hits[:4])
    return "PASS", note


def gate_catalog():
    if not CATALOG.exists():
        return "CANNOT-EVALUATE", "floor/CATALOG.md missing"
    ids = sorted(set(re.findall(r"\bSV-\d{3}\b", CATALOG.read_text(encoding="utf-8"))))
    if not ids:
        return "CANNOT-EVALUATE", "no SV- ids found in catalog"
    encoded, broken = [], []
    for cid in ids:
        yml = CHECKS_DIR / f"{cid}.check.yml"
        fdir = FIXTURES_DIR / cid
        has_pass = fdir.exists() and any(fdir.glob("pass*"))
        has_fail = fdir.exists() and any(fdir.glob("fail*"))
        if yml.exists():
            if has_pass and has_fail:
                encoded.append(cid)
            else:
                broken.append(cid)
    if broken:
        return "FAIL", (f"{len(broken)} check(s) without pass+fail fixtures "
                        f"(a check without fixtures is a sentence): {', '.join(broken[:8])}")
    return "PASS", f"{len(encoded)}/{len(ids)} encoded; {len(ids)-len(encoded)} honestly UNENCODED"


def gate_fixture():
    """Rung 01's executioner: the floor engine's full fixture battery + the ledger
    selftest + the no-model scan. ImportError degrades to CANNOT-EVALUATE (the
    estate's pattern), everything else is graded."""
    try:
        sys.path.insert(0, str(ROOT / "floor"))
        import engine
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"floor engine unavailable: {e}"
    r = engine.run_battery()
    try:
        sys.path.insert(0, str(ROOT / "ledger"))
        import tape as product_tape
        ledger_fails = product_tape.selftest()
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"ledger unavailable: {e}"
    problems = list(r["broken"]) + r["no_model_violations"] + ledger_fails
    if problems:
        return "FAIL", "; ".join(problems[:4])
    return "PASS", (f"{r['encoded']} check(s) fully encoded, {r['fixtures_run']} fixtures "
                    f"green, ledger selftest green (append/verify/tamper/torn-tail), no-model clean")


def gate_catalog_complete():
    """Rung 02's executioner: PASS only when every catalog check is encoded."""
    status, detail = gate_catalog()
    if status != "PASS":
        return status, detail
    m = re.match(r"(\d+)/(\d+) encoded", detail)
    if m and m.group(1) == m.group(2):
        return "PASS", detail
    return "CANNOT-EVALUATE", f"in progress - {detail}"


def main():
    record = "--record" in sys.argv
    results = [
        ("G-FOLD",) + gate_fold(),
        ("G-PRIVACY",) + gate_privacy(),
        ("G-CATALOG",) + gate_catalog(),
        ("F-FIXTURE",) + gate_fixture(),
        ("G-CATALOG-COMPLETE",) + gate_catalog_complete(),
    ]
    width = max(len(r[0]) for r in results)
    fail = False
    for name, status, detail in results:
        print(f"{name:<{width}}  {status:<16}  {detail}")
        if status == "FAIL":
            fail = True
        if status == "CANNOT-EVALUATE" and name == "G-PRIVACY":
            fail = True  # privacy fails closed
    if record:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with TAPE.open("a", encoding="utf-8") as f:
            for name, status, detail in results:
                f.write(json.dumps({"ts": ts, "session": "gates", "type": "verdict",
                                    "gate": name, "status": status,
                                    "detail": detail}) + "\n")
        fold.write_folds()
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
