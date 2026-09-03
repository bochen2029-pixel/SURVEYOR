#!/usr/bin/env python3
"""clocks/anchors.py - the anchor registry, the anchor-defect plants, and the
per-case temporal network (law B1: anchors are first-class).

Every clock check in floor/checks declares `anchor` (the record path its clock
runs from) and `anchor_why` (the citation or the harvested reason). This module:

  1. REGISTRY   - reads every check that declares an anchor; verifies the declared
                  anchor is a path the predicate actually reads (verbatim, or
                  item-relative inside every()/every_pair()); extracts each
                  within(anchor, done, bound) and by(deadline, done) clause.
  2. PLANTS     - grades anchor-defect plants. A fixture carrying
                      "anchor_plant": {"wrong_anchor": "<path>", "verdict_if_wrong": "<verdict>"}
                  is re-evaluated with the wrong anchor substituted into the
                  predicate. The verdict MUST change, to verdict_if_wrong. A plant
                  that does not flip is broken: it would not catch the historical
                  error it claims to catch (the feedback clock anchored to
                  cross-clamp instead of organ recovery [H]).
  3. STN        - builds one Simple Temporal Network per record from the registry:
                  every within() becomes  done - anchor <= bound, every by() becomes
                  a window close, every timestamp the record already carries is
                  pinned. The closure (clocks/closure.py) then yields IMPLIED
                  deadlines across checks - e.g. the DDR's latest date from organ
                  recovery, through the feedback form, before the feedback form
                  exists - with the binding path as the explanation.

Three-state honesty throughout. Stdlib only; no model (test_closure.py enforces).

CLI: python clocks/anchors.py                 registry + plants (the gate's view)
     python clocks/anchors.py --selftest       the chained implied-deadline case
     python clocks/anchors.py --case FIXTURE   STN view of one floor fixture's record
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "floor"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
from closure import REFERENCE, STN, hhmm  # noqa: E402

CHECKS_DIR = ROOT / "floor" / "checks"
FIXTURES_DIR = ROOT / "floor" / "fixtures"

_WITHIN = re.compile(r"within\(\s*(month_end_of\()?\s*([A-Za-z_][\w.\[\]]*)\s*\)?\s*,\s*([A-Za-z_][\w.\[\]]*)\s*,\s*(\d+)(bd|m|h|d)?\s*\)")
_BY = re.compile(r"by\(\s*month_end_following\(\s*([A-Za-z_][\w.\[\]]*)\s*\)\s*,\s*([A-Za-z_][\w.\[\]]*)\s*\)")
_UNIT = {"m": 1, "h": 60, "d": 1440, None: 1}


# ---------------------------------------------------------------- registry
def load_registry() -> list[dict[str, Any]]:
    """One entry per check that declares an anchor, with its clock clauses."""
    out = []
    for yml in sorted(CHECKS_DIR.glob("SV-*.check.yml")):
        check = engine.load_check_yml(yml)
        anchor = check.get("anchor")
        if not anchor and check.get("trigger") != "continuous":
            continue
        pred = str(check.get("predicate", ""))
        problems = []
        if not anchor:
            problems.append("continuous check declares no anchor")
        if not check.get("anchor_why"):
            problems.append("no anchor_why")
        if anchor and not _anchor_is_read(anchor, pred):
            problems.append(f"declared anchor {anchor!r} is not a path the predicate reads")
        clauses = []
        for m in _WITHIN.finditer(pred):
            wrapped, a, d, n, unit = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)
            clauses.append({"kind": "within_month_end" if wrapped else "within", "anchor": a, "done": d,
                            "bound": n if unit == "bd" else n * _UNIT[unit], "unit": unit or "m"})
        for m in _BY.finditer(pred):
            clauses.append({"kind": "by_month_end_following", "anchor": m.group(1), "done": m.group(2)})
        out.append({"id": check["id"], "anchor": anchor, "anchor_why": check.get("anchor_why", ""),
                    "trigger": check.get("trigger"), "action": str(check.get("action", "")).upper(),
                    "layer": check.get("layer"), "predicate": pred, "clauses": clauses,
                    "problems": problems, "check": check})
    return out


def _anchor_is_read(anchor: str, pred: str) -> bool:
    if anchor in pred:
        return True
    # item-relative inside a quantifier: anchor = list.field, predicate reads field inside every(list, ...)
    if "." in anchor:
        head, tail = anchor.rsplit(".", 1)
        if re.search(rf"every(?:_pair)?\(\s*{re.escape(head)}\s*,", pred) and re.search(rf"\b{re.escape(tail)}\b", pred):
            return True
    return False


# ---------------------------------------------------------------- plants
def grade_plants() -> dict[str, Any]:
    """Every fixture with an anchor_plant block, re-evaluated on the wrong anchor."""
    reg = {r["id"]: r for r in load_registry()}
    plants, broken = [], []
    for cid, r in reg.items():
        fdir = FIXTURES_DIR / cid
        for fx in sorted(fdir.glob("*.json")) if fdir.exists() else []:
            data = json.loads(fx.read_text(encoding="utf-8"))
            plant = data.get("anchor_plant")
            if not plant:
                continue
            wrong, want_wrong = plant.get("wrong_anchor"), plant.get("verdict_if_wrong")
            rec = data.get("record", {})
            right = engine.evaluate(r["check"], rec)
            entry = {"check": cid, "fixture": fx.name, "anchor": r["anchor"], "wrong_anchor": wrong,
                     "verdict_right": right, "verdict_if_wrong": want_wrong}
            if not r["anchor"] or not wrong or r["anchor"] not in r["predicate"]:
                entry["problem"] = "plant needs a verbatim anchor in the predicate and a wrong_anchor"
            elif right != data.get("expect"):
                entry["problem"] = f"right-anchor verdict {right} disagrees with expect {data.get('expect')}"
            else:
                swapped = {**r["check"], "predicate": r["predicate"].replace(r["anchor"], wrong)}
                try:
                    got_wrong = engine.evaluate(swapped, rec)
                except ValueError as e:
                    got_wrong = f"PARSE-ERROR({e})"
                entry["verdict_wrong"] = got_wrong
                if got_wrong == right:
                    entry["problem"] = "the wrong anchor gives the same verdict - this plant catches nothing"
                elif got_wrong != want_wrong:
                    entry["problem"] = f"wrong-anchor verdict {got_wrong}, plant claimed {want_wrong}"
            plants.append(entry)
            if "problem" in entry:
                broken.append(f"{cid}/{fx.name}: {entry['problem']}")
    reg_problems = [f"{r['id']}: {p}" for r in reg.values() for p in r["problems"]]
    return {"registry": len(reg), "plants": plants, "broken": broken + reg_problems,
            "checks_with_plants": len({p["check"] for p in plants})}


# ---------------------------------------------------------------- the per-case STN
def _resolve_ts(path: str, record: dict) -> datetime | None:
    try:
        node = engine.compile_predicate(f"exists({path})")["a"]
        v = engine._resolve_path(node, [record])
    except (engine.CannotEvaluate, ValueError):
        return None
    if v in (None, ""):
        return None
    try:
        return engine._ts(v)
    except engine.CannotEvaluate:
        return None


def _business_deadline(anchor: datetime, n: int) -> datetime:
    """End of the n-th weekday after the anchor's date (the last lawful moment)."""
    d, k = anchor.date(), 0
    while k < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return datetime(d.year, d.month, d.day, 23, 59, tzinfo=timezone.utc)


def build_stn(record: dict) -> tuple[STN, dict[str, Any]]:
    """The record's clock lattice: pinned timestamps + every registry bound."""
    reg = load_registry()
    times: dict[str, datetime] = {}
    bounds: list[dict[str, Any]] = []
    for r in reg:
        for c in r["clauses"]:
            a_ts = _resolve_ts(c["anchor"], record)
            d_ts = _resolve_ts(c["done"], record)
            if a_ts is not None:
                times[c["anchor"]] = a_ts
            if d_ts is not None:
                times[c["done"]] = d_ts
            bounds.append({**c, "check": r["id"], "layer": r["layer"] or "", "anchor_present": a_ts is not None})
    as_of = _resolve_ts("as_of", record)
    if not times:
        return STN(), {"t0": None, "as_of": None, "pending": [], "note": "no clock anchors resolvable on this record"}
    t0 = min(times.values())

    def m(dt: datetime) -> int:
        return int((dt - t0).total_seconds() // 60)

    stn = STN()
    for name, dt in times.items():
        stn.at(name, m(dt), label="recorded", layer="")
    for b in bounds:
        a_ts = times.get(b["anchor"])
        if b["kind"] == "within" and b["unit"] == "bd":
            if a_ts is not None:
                stn.at_most(b["done"], REFERENCE, m(_business_deadline(a_ts, b["bound"])),
                            label=f"{b['check']} {b['bound']} business days", layer=b["layer"])
            else:
                # the anchor is itself pending: chain through it with the widest calendar
                # span n business days can occupy (n + one weekend per started week)
                n = b["bound"]
                span = (n + 2 * ((n + 4) // 5)) * 1440
                stn.at_most(b["done"], b["anchor"], span,
                            label=f"{b['check']} {n} business days (calendar-conservative, anchor pending)", layer=b["layer"])
        elif b["kind"] == "within":
            stn.at_most(b["done"], b["anchor"], b["bound"],
                        label=f"{b['check']} <= {hhmm(b['bound']).replace(' ', '')}", layer=b["layer"])
        elif b["kind"] == "within_month_end":
            if a_ts is not None:
                deadline = engine._ts(engine._month_end_of(a_ts))
                stn.at_most(b["done"], REFERENCE, m(deadline) + b["bound"],
                            label=f"{b['check']} month end + {hhmm(b['bound']).replace(' ', '')}", layer=b["layer"])
            else:  # anchor pending: at most a 31-day month remainder plus the bound
                stn.at_most(b["done"], b["anchor"], 31 * 1440 + b["bound"],
                            label=f"{b['check']} month end + bound (calendar-conservative, anchor pending)", layer=b["layer"])
        else:  # month-end following: needs the anchor's calendar month
            if a_ts is not None:
                deadline = engine._ts(engine._month_end_following(a_ts))
                stn.at_most(b["done"], REFERENCE, m(deadline), label=f"{b['check']} month-end following", layer=b["layer"])
    closure = stn.close()
    pending = sorted({b["done"] for b in bounds if b["done"] not in times
                      and b["done"] in stn.names and closure.latest(b["done"]) < engine_INF_HALF})
    return stn, {"t0": t0, "as_of": m(as_of) if as_of else None, "pending": pending, "times": {k: m(v) for k, v in times.items()}}


engine_INF_HALF = 0x3F3F3F3F // 2


def selftest() -> list[str]:
    """The chain the flat timer list cannot see: organ recovery is the only recorded
    time; the feedback form's deadline follows from SV-030 and the DDR's from SV-031
    THROUGH the pending feedback node. Returns failures; empty = green."""
    fails: list[str] = []
    record = {"case_id": "OD-SELFTEST", "recovery": {"organ_recovery_ts": "2026-08-03T10:40:00Z"},
              "feedback": {}, "ddr": {}, "as_of": "2026-08-04T00:00:00Z"}
    stn, info = build_stn(record)
    c = stn.close()
    if "feedback.submitted_ts" not in info["pending"] or "ddr.submitted_ts" not in info["pending"]:
        fails.append(f"pending should hold feedback and ddr, got {info['pending']}")
        return fails
    fb = c.latest("feedback.submitted_ts")
    ddr = c.latest("ddr.submitted_ts")
    # Monday 2026-08-03 10:40 + 5 business days -> Monday 2026-08-10 23:59
    want_fb = int((datetime(2026, 8, 10, 23, 59, tzinfo=timezone.utc) - info["t0"]).total_seconds() // 60)
    if fb != want_fb:
        fails.append(f"feedback latest {fb}, want {want_fb} (5 business days from organ recovery)")
    if ddr != fb + 30 * 1440:
        fails.append(f"ddr latest {ddr}, want feedback latest + 30d = {fb + 30 * 1440} (chained through the pending feedback)")
    path = c.binding_path("ddr.submitted_ts")
    if [p.label.split()[0] for p in path] != ["SV-030", "SV-031"]:
        fails.append(f"ddr binding path should run SV-030 then SV-031, got {[p.label for p in path]}")
    # no anchors at all -> honest note, no crash
    stn2, info2 = build_stn({"case_id": "X"})
    if info2.get("t0") is not None:
        fails.append("a record with no clock anchors must report none, not invent a T0")
    return fails


def report_case(path: str) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    record = data.get("record", data)
    stn, info = build_stn(record)
    if info["t0"] is None:
        print(info["note"])
        return 0
    c = stn.close()
    print(f"case: {record.get('case_id', path)}   T0 = {info['t0'].isoformat()}   now = {hhmm(info['as_of']) if info['as_of'] is not None else '-'}")
    if not c.consistent:
        cyc = c.negative_cycle() or []
        print("INFEASIBLE - recorded times violate the lattice: " + " -> ".join(cyc))
        for k in c.cycle_constraints(cyc):
            print("   " + k.render())
        return 1
    print(f"{'event':<40}{'latest':>16}{'slack':>10}")
    print("-" * 66)
    for ev in info["pending"]:
        latest = c.latest(ev)
        row = f"{ev:<40}{hhmm(latest):>16}"
        if info["as_of"] is not None:
            s = c.slack(ev, info["as_of"])
            row += f"{(str(s) + 'm'):>10}" + ("   BREACHED" if s < 0 else "")
        print(row)
    print()
    for ev in info["pending"]:
        print(c.explain(ev))
        print()
    return 0


# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    if "--case" in sys.argv:
        sys.exit(report_case(sys.argv[sys.argv.index("--case") + 1]))
    if "--selftest" in sys.argv:
        f = selftest()
        print("\n".join(f) if f else "clocks selftest: green (implied DDR deadline chains through the pending feedback form)")
        sys.exit(1 if f else 0)
    reg = load_registry()
    print(f"{'check':<8}{'trigger':<18}{'anchor':<44}clauses")
    for r in reg:
        flag = "  !! " + "; ".join(r["problems"]) if r["problems"] else ""
        print(f"{r['id']:<8}{str(r['trigger']):<18}{str(r['anchor']):<44}{len(r['clauses'])}{flag}")
    g = grade_plants()
    print()
    for p in g["plants"]:
        state = "BROKEN " + p["problem"] if "problem" in p else f"ok  right={p['verdict_right']} wrong={p.get('verdict_wrong')}"
        print(f"plant {p['check']}/{p['fixture']}: {p['anchor']} vs {p['wrong_anchor']}: {state}")
    print(f"\nregistry: {g['registry']} anchored checks; plants: {len(g['plants'])} across {g['checks_with_plants']} checks; broken: {len(g['broken'])}")
    for b in g["broken"]:
        print("  - " + b)
    sys.exit(1 if g["broken"] else 0)
