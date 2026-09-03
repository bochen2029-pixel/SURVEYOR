#!/usr/bin/env python3
"""ledger/make_tape.py - build a quality tape by running the floor over the synthetic world.

The ledger's input is PRODUCED, not hand-written: every `check_result` and `hold` on this
tape came from the actual encoded checks evaluating actual generated records. Hand-writing
a tape to fold would test the fold against a document written to make it look good.

What the tape carries, in the SPEC section 4 vocabulary:
  check_result  one check, one record, one verdict, with the evidence fields the check names
  hold          a non-PASS verdict on a `hold` check - open work attached to the CASE
  release       a hold cleared before close-attempt (law B4: a hold is not a finding)
  finding       HUMAN-AUTHORED. A hold that survived to close-attempt and a person then
                recorded under their own name. The generator marks these as authored by a
                role, never by a machine, because no machine writes the quality record (A5)
  variance      an intake item for triage
  capa          a corrective action as a patch row with a falsifiable expectation
  capa_check    the effectiveness grade computed at the horizon
  signature     the human crossing - the only way an Act happens

Deterministic in (seed, cases): the same arguments produce byte-identical events, which is
what makes G-FOLD-DETERMINISM meaningful.

CLI: python ledger/make_tape.py [--seed S] [--cases N] [--json OUT] [--chain DIR]
     --chain writes the events through the real hash-chained product tape and verifies it,
     which is how we find out whether the ported ledger actually carries this vocabulary.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in ("floor", "experiments/f-fixture", "ledger"):
    sys.path.insert(0, str(ROOT / p))
import engine  # noqa: E402
import generate  # noqa: E402
from lifecycle import grade, ts as parse_ts  # noqa: E402

HOLD_ACTIONS = {"HOLD", "ALARM"}

_PLACEHOLDER = re.compile(r"\{([A-Za-z_][\w.\[\]]*)\}")


def resolve_message(msg: str, rec: dict) -> str:
    """A check's message names its evidence fields in braces. Resolve them against the
    record so the tape carries what a person would read, not a template - an unresolved
    {or_timeline.prep_complete_ts} on a morning board is a defect the reader has to
    decode, and the evidence path stays in the check where it belongs."""
    def sub(m):
        cur = rec
        for part in m.group(1).split("."):
            if not isinstance(cur, dict) or part not in cur:
                return "(not recorded)"
            cur = cur[part]
        if isinstance(cur, (list, dict)):
            return f"{len(cur)} item(s)"
        return "(blank)" if cur in (None, "") else str(cur)
    return _PLACEHOLDER.sub(sub, msg)




def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def build(seed: int = 20260903, cases: int = 60) -> list[dict]:
    checks = {p.name.split(".")[0]: engine.load_check_yml(p)
              for p in sorted((ROOT / "floor" / "checks").glob("SV-*.check.yml"))}
    rows = [r for r in generate.corpus(seed, cases, 1) if r["clean"] or r["kind"] == "donor"]
    events: list[dict] = []

    def add(kind: str, ts: str, body: dict) -> None:
        events.append({"kind": kind, "ts": ts, "body": body})

    # -- the floor runs, and everything it says lands on the tape, including its silences
    for row in rows:
        rec = row["record"]
        case = rec.get("case_id") or rec.get("register_id") or row["corpus_id"]
        at = rec.get("as_of") or "2026-06-15T12:00:00Z"
        for cid in sorted(checks):
            chk = checks[cid]
            verdict = engine.evaluate(chk, rec)
            ev = {"case": case, "check": cid, "verdict": verdict,
                  "layer": chk.get("layer"), "family": chk.get("family"),
                  "trigger": chk.get("trigger"), "anchor": chk.get("anchor"),
                  "evidence_fields": list(chk.get("evidence") or []),
                  "source_system": "adapter-synthetic"}
            add("check_result", at, ev)
            if verdict in HOLD_ACTIONS:
                add("hold", at, {"case": case, "check": cid, "verdict": verdict,
                                 "reason": resolve_message(str(chk.get("message", "")), rec),
                                 "source_system": "adapter-synthetic",
                                 # law B3: a hold attaches to the CASE. There is no field here
                                 # for a person, and no notify-person primitive to put one in.
                                 "attached_to": "case"})

    # -- the human layer. Deterministic, and explicitly role-authored (law A5).
    holds = [e for e in events if e["kind"] == "hold"]
    holds.sort(key=lambda e: (e["ts"], e["body"]["case"], e["body"]["check"]))
    for n, h in enumerate(holds):
        b, t = h["body"], parse_ts(h["ts"])
        if n % 3 == 0:                       # two in three are cleared before close-attempt
            continue
        if n % 3 == 1:
            add("release", _ts(t + timedelta(hours=6)),
                {"case": b["case"], "check": b["check"], "released_by_role": "quality_specialist",
                 "why": "corrected in the record before close-attempt"})
        else:                                 # survived to close-attempt -> a person writes it up
            add("finding", _ts(t + timedelta(days=2)),
                {"case": b["case"], "check": b["check"], "authored_by_role": "quality_specialist",
                 "severity": "minor" if n % 2 else "major", "source_system": "adapter-synthetic"})
            add("variance", _ts(t + timedelta(days=3)),
                {"id": f"VAR-{n:04d}", "variance_class": str(b["check"])[:6],
                 "check": b["check"], "occurred_ts": h["ts"],
                 "source_system": "adapter-synthetic" if n % 4 else "adapter-legacy",
                 "filed_by_role": "quality_specialist"})

    # -- two CAPAs: one that will grade met, one that will not. Both are patch rows.
    capas = [
        {"id": "CAPA-2026-021", "variance_class": "documentation", "owner_role": "quality_manager",
         "expectation": {"metric": "holds_per_100_cases_family_signatures", "baseline": 18, "target": 9,
                         "horizon_ts": "2026-06-20T00:00:00Z"},
         "expires": "2027-06-20T00:00:00Z", "inverse": "retire_training_module_and_restore_prior_form",
         "status": "mounted", "plan": "second-signature prompt at close-attempt"},
        {"id": "CAPA-2026-022", "variance_class": "clocks", "owner_role": "director_of_operations",
         "expectation": {"metric": "alarms_per_100_cases_family_clocks", "baseline": 12, "target": 4,
                         "horizon_ts": "2026-06-25T00:00:00Z"},
         "expires": "2027-06-25T00:00:00Z", "inverse": "retire_dispatch_change",
         "status": "mounted", "plan": "earlier dispatch on referral receipt"},
    ]
    for c in capas:
        add("capa", "2026-05-02T09:00:00Z", c)
        add("signature", "2026-05-02T09:05:00Z",
            {"capa_id": c["id"], "by_role": "quality_director", "scope": f"mount {c['id']}"})

    # -- the horizon arrives and the effectiveness check runs BY ITSELF (SPEC section 8)
    add("capa_check", "2026-06-21T08:00:00Z",
        grade(capas[0], observed=7, data_ref="FOLD-2026-06-LINE-OF-SIGHT", at="2026-06-21T08:00:00Z"))
    add("capa_check", "2026-06-26T08:00:00Z",
        grade(capas[1], observed=11, data_ref="FOLD-2026-06-LINE-OF-SIGHT", at="2026-06-26T08:00:00Z"))

    # -- stable order, then number. Sorting by (ts, kind, canonical body) rather than by
    #    arrival is what lets the fold be invariant to the order simultaneous events landed in.
    events.sort(key=lambda e: (e["ts"], e["kind"], json.dumps(e["body"], sort_keys=True)))
    for i, e in enumerate(events, 1):
        e["i"] = i
    return events


def write_chain(events: list[dict], data_root: Path) -> str:
    """Push the events through the real hash-chained product tape and verify it. This is
    the ported ledger being asked to carry the quality vocabulary for the first time."""
    sys.path.insert(0, str(ROOT / "ledger"))
    import tape as product_tape
    t = product_tape.Tape.open(data_root)
    try:
        t.append_many([(e["kind"], e["body"]) for e in events])
    finally:
        t.close()
    rep = product_tape.verify_tape(data_root)
    return rep.summary()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--cases", type=int, default=60)
    ap.add_argument("--json", default=None)
    ap.add_argument("--chain", default=None)
    a = ap.parse_args()
    evs = build(a.seed, a.cases)
    kinds: dict[str, int] = {}
    for e in evs:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"{len(evs)} events: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        with open(a.json, "w", encoding="utf-8", newline="\n") as fh:
            for e in evs:
                fh.write(json.dumps(e, sort_keys=True) + "\n")
        print("wrote", a.json)
    if a.chain:
        print(write_chain(evs, Path(a.chain)))
