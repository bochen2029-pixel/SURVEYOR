#!/usr/bin/env python3
"""fold.py - deterministic renders of build state from the tape.

LAW: state is folded, never authored. STATE.md and BOARD.md are GENERATED
files - editing them by hand is a build error (gates.py G-FOLD catches it).

Usage:  python _build/fold.py          # render STATE.md + BOARD.md from TAPE.jsonl
Stdlib only. Deterministic: output depends only on tape content (no wall clock).
"""
import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAPE = ROOT / "_build" / "TAPE.jsonl"
STATE = ROOT / "_build" / "STATE.md"
BOARD = ROOT / "_build" / "BOARD.md"

# The rung ladder (from SPEC.md section 13). Executioner = the gate/falsifier
# whose latest tape verdict determines the rung's status.
RUNGS = [
    ("00", "Repo skeleton, spec, catalog, prereg, build discipline", "G-COLDSTART"),
    ("01", "Tape + floor engine + fixtures runner",                  "F-FIXTURE"),
    ("02", "Catalog encoded (~45 checks, pass+fail fixtures each)",  "G-CATALOG-COMPLETE"),
    ("03", "Clocks engine (STN port, anchor declarations)",          "G-ANCHOR-PLANTS"),
    ("04", "F-RETRO on historical charts (on site, local)",          "F-RETRO"),
    ("05", "Crosswalk MVP (pinning, mappings, one edition diff)",    "F-CROSSWALK"),
    ("06", "Ledger + CAPA lifecycle + the three folds",              "G-FOLD-DETERMINISM"),
    ("07", "Morning Board rendered real from the tape",              "G-EVIDENCE-LINKS"),
    ("08", "Watch tier in shadow",                                   "F-WATCH-GATE"),
    ("09", "Kit hardening (elicit/, examples, foreign harness)",     "G-FOREIGN-HARNESS"),
]


def read_tape():
    events = []
    if not TAPE.exists():
        return events
    for i, line in enumerate(TAPE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"TAPE CORRUPT at line {i}: {e}")
            sys.exit(2)
    return events


def tape_sha():
    """Content identity of the tape: line endings are stripped before hashing, so the
    sha is the same whether a checkout gave the file LF or CRLF (S2: a mixed-ending
    tape made the fold hash checkout-dependent, a cold-start defect)."""
    if not TAPE.exists():
        return "EMPTY"
    lines = [ln.rstrip(b"\r") for ln in TAPE.read_bytes().split(b"\n")]
    return hashlib.sha256(b"\n".join(lines)).hexdigest()[:16]


def latest_verdicts(events):
    v = {}
    for e in events:
        if e.get("type") == "verdict":
            v[e.get("gate", "?")] = e
    return v


def render(events):
    """Pure render: (state_md, board_md) from events. No wall clock anywhere."""
    sha = tape_sha()
    as_of = events[-1]["ts"] if events else "never"

    sessions = [e for e in events if e.get("type") == "session_start"]
    ends = [e for e in events if e.get("type") == "session_end"]
    mounts = [e for e in events if e.get("type") == "mount"]
    decisions = [e for e in events if e.get("type") == "decision"]
    questions = [e for e in events if e.get("type") == "question"]
    blockers = [e for e in events if e.get("type") == "blocker"]
    signatures = [e for e in events if e.get("type") == "signature"]
    verdicts = latest_verdicts(events)

    last_sig_ts = signatures[-1]["ts"] if signatures else ""
    review_queue = [d for d in decisions if d["ts"] > last_sig_ts]

    open_sessions = [s for s in sessions
                     if s.get("session") not in {e.get("session") for e in ends}]
    next_action = ends[-1].get("next", "(none recorded)") if ends else "(no session closed yet)"

    def rung_status(gate):
        e = verdicts.get(gate)
        return e["status"] if e else "NOT-RUN"

    # ---- STATE.md ----
    s = []
    s.append("# STATE - generated fold. DO NOT EDIT. (gates.py G-FOLD enforces)")
    s.append(f"tape: {sha} | as-of: {as_of} | events: {len(events)} | "
             f"sessions: {len(sessions)} (open: {len(open_sessions)})")
    s.append("")
    s.append(f"**NEXT ACTION:** {next_action}")
    if open_sessions:
        cur = open_sessions[-1]
        s.append(f"**OPEN SESSION:** {cur.get('session')} - {cur.get('goal', '?')} "
                 f"(started {cur.get('ts')})")
    s.append("")
    s.append("## Rung ladder (status = latest tape verdict of each executioner)")
    s.append("| Rung | Deliverable | Executioner | Status |")
    s.append("|---|---|---|---|")
    for rid, desc, gate in RUNGS:
        s.append(f"| {rid} | {desc} | {gate} | {rung_status(gate)} |")
    s.append("")
    s.append(f"## Open questions ({len(questions)})")
    for q in questions[-10:]:
        s.append(f"- [{q['ts']}] {q.get('what', '?')}")
    s.append("")
    s.append(f"## Open blockers ({len(blockers)})")
    for b in blockers[-10:]:
        s.append(f"- [{b['ts']}] {b.get('what', '?')} | unblocked by: {b.get('unblock', '?')}")
    s.append("")
    s.append(f"## Review queue - decisions since last signature ({len(review_queue)})")
    for d in review_queue[-15:]:
        s.append(f"- [{d['ts']}] {d.get('what', '?')} | why: {d.get('why', '?')} "
                 f"| revert: {d.get('revert', 'n/a')}")
    s.append("")
    s.append("## Last 8 mounts")
    for m in mounts[-8:]:
        s.append(f"- [{m['ts']}] {m.get('path', '?')} - {m.get('desc', '')}")
    s.append("")

    # ---- BOARD.md ----
    passed = sum(1 for e in verdicts.values() if e["status"] == "PASS")
    failed = sum(1 for e in verdicts.values() if e["status"] == "FAIL")
    cannot = sum(1 for e in verdicts.values() if e["status"] == "CANNOT-EVALUATE")
    b = []
    b.append("# BOARD - the build's Morning Board. Generated fold. DO NOT EDIT.")
    b.append(f"tape: {sha} | as-of: {as_of}")
    b.append("")
    b.append(f"| mounts | decisions | review queue | questions | blockers | signatures |")
    b.append(f"|---|---|---|---|---|---|")
    b.append(f"| {len(mounts)} | {len(decisions)} | {len(review_queue)} | "
             f"{len(questions)} | {len(blockers)} | {len(signatures)} |")
    b.append("")
    b.append(f"**Gates:** {passed} PASS / {failed} FAIL / {cannot} CANNOT-EVALUATE "
             f"({len(verdicts)} distinct gates ever run)")
    for g, e in sorted(verdicts.items()):
        b.append(f"- {g}: **{e['status']}** [{e['ts']}] {e.get('detail', '')}")
    b.append("")
    b.append(f"**NEXT ACTION:** {next_action}")
    b.append("")
    return "\n".join(s) + "\n", "\n".join(b) + "\n"


def write_folds():
    state_md, board_md = render(read_tape())
    STATE.write_text(state_md, encoding="utf-8", newline="\n")
    BOARD.write_text(board_md, encoding="utf-8", newline="\n")
    print(f"folded: {STATE.name}, {BOARD.name} (tape {tape_sha()})")


if __name__ == "__main__":
    write_folds()
