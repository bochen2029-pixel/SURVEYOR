#!/usr/bin/env python3
"""tools/pin_ledger_head.py - compute and pin the ledger's expected chain head.

The product tape is hash-chained, so replaying the same events must reproduce the same
head. Until the S10 cold-start audit it did not: every record was stamped `datetime.now()`
and the hash covers the record, so the head was different on every run — and the build
published it in its verdict as though it were a tamper-evidence receipt. A receipt that
changes when nothing changed identifies nothing.

`ledger/tape.py` now takes each event's own timestamp, so the head is an identity. This
writes that identity into `_build/gates.py` as `LEDGER_EXPECTED_HEAD`, and the gate fails
when a replay stops matching it.

    python tools/pin_ledger_head.py [--check]

Re-pinning is a deliberate act: if the head moves, either the synthetic events changed or
the ledger's format did, and both need a tape `decision` saying which.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for d in ("ledger", "floor", "experiments/f-fixture"):
    sys.path.insert(0, str(ROOT / d))
import make_tape  # noqa: E402

GATES = ROOT / "_build" / "gates.py"


def compute() -> tuple[str, int, int, int]:
    seed = int(re.search(r"LEDGER_HEAD_SEED, LEDGER_HEAD_CASES = (\d+), (\d+)",
                         GATES.read_text(encoding="utf-8")).group(1))
    cases = int(re.search(r"LEDGER_HEAD_SEED, LEDGER_HEAD_CASES = (\d+), (\d+)",
                          GATES.read_text(encoding="utf-8")).group(2))
    events = make_tape.build(seed=seed, cases=cases)
    with tempfile.TemporaryDirectory() as d:
        summary = make_tape.write_chain(events, Path(d))
    return summary.rsplit("head ", 1)[-1].strip(), seed, cases, len(events)


def current() -> str:
    m = re.search(r'LEDGER_EXPECTED_HEAD = "([^"]*)"', GATES.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def main() -> int:
    head, seed, cases, n = compute()
    have = current()
    print(f"seed {seed}, {cases} cases, {n:,} events -> head {head}")
    if "--check" in sys.argv:
        if head == have:
            print("matches the pin")
            return 0
        print(f"DOES NOT MATCH the pin {have or '(none)'}")
        return 1
    s = GATES.read_text(encoding="utf-8")
    s = re.sub(r'LEDGER_EXPECTED_HEAD = "[^"]*"', f'LEDGER_EXPECTED_HEAD = "{head}"', s, count=1)
    GATES.write_text(s, encoding="utf-8", newline="\n")
    print(f"pinned in _build/gates.py (was {have or 'unpinned'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
