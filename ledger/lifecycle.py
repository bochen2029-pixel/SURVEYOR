#!/usr/bin/env python3
"""ledger/lifecycle.py - the CAPA lifecycle and the variance triage.

SPEC section 8. Two engines that sit between the floor and the folds, and neither of
them ever writes a verdict:

  THE CAPA IS AN EXPECTATION WITH A DEADLINE. Plan (draft carrying a falsifiable
  expectation) -> Do (shadow) -> Study (grade at the horizon, mechanically, from the
  data) -> Act (mount under signature, or retire with the reason printed). At the
  horizon the effectiveness check runs by itself: expectation met -> `sustained`;
  not met -> AUTO-RETURNED TO COMMITTEE WITH THE DATA ATTACHED. No CAPA closes by
  assertion, and no CAPA closes because nobody looked.

  THE VARIANCE TRIAGE IS A DISCRIMINATOR, NOT A JUDGE. Three questions, in order:
  COVERAGE - was anyone in a position to know? (did a mounted check cover this at the
  time it happened, or is this a hole in the floor); NOVELTY - did the world change?
  (is this class of variance new in the window); DISTORTION - does one source
  systematically disagree? (is one system, page or adapter carrying a disproportionate
  share). The output is an INVESTIGATION PACKET drafted for humans: the questions, the
  evidence event ids, and what each answer would imply. It never concludes.

WHAT NEITHER ENGINE MAY DO (law A5, law B3). No machine path runs from a record to a
verdict about a person. The triage classifies the SYSTEM's relationship to a variance -
coverage, novelty, distortion - and there is deliberately no fourth bucket for "who".
A packet names roles and systems and case ids; it never names or scores a person, and
there is no notify-person primitive anywhere in this module. That separation is the
mechanical content of Just Culture, which the reference site already professes [H].

Pure functions over event lists. No wall clock: every "now" is passed in, because a
document that reads the system clock cannot be re-derived tomorrow.
Stdlib only, no model.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable

CAPA_STATES = ("draft", "shadow", "mounted", "sustained", "returned_to_committee", "retired")
TRIAGE_AXES = ("coverage", "novelty", "distortion")


# ---------------------------------------------------------------- time
def ts(v: Any) -> datetime | None:
    if not isinstance(v, str) or not v:
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def in_window(v: Any, start: str, end: str) -> bool:
    """[start, end) - a period a document names, never a period it discovers."""
    t, a, b = ts(v), ts(start), ts(end)
    return bool(t and a and b and a <= t < b)


def body(e: dict) -> dict:
    """Product-tape records are {i, kind, ts, body, h}; build-tape events are flat.
    Both shapes appear in fixtures, so read either without pretending they are the same."""
    return e.get("body", e) if isinstance(e.get("body"), dict) else e


def event_id(e: dict) -> str:
    """The citation handle for a claim. A fold that cannot name the events behind a
    number has produced a number without a source, which law A6 says is not a number."""
    i = e.get("i")
    return f"#{i}" if i is not None else f"@{e.get('ts', '?')}"


# ---------------------------------------------------------------- CAPA lifecycle
def capa_rows(events: Iterable[dict]) -> dict[str, dict]:
    """Fold every `capa` and `capa_check` event into the current state of each CAPA.
    Later events supersede earlier ones for the same id: the tape is append-only, so a
    correction is a new event, never an edit (law A2)."""
    rows: dict[str, dict] = {}
    for e in events:
        if e.get("kind") not in ("capa", "capa_check", "signature", "retire"):
            continue
        b = body(e)
        cid = b.get("capa_id") or b.get("id")
        if not cid:
            continue
        row = rows.setdefault(cid, {"id": cid, "events": [], "state": "draft",
                                    "checks": [], "signatures": []})
        row["events"].append(event_id(e))
        if e["kind"] == "capa":
            for k, v in b.items():
                if k not in ("capa_id",):
                    row[k] = v
            row["state"] = b.get("status", row.get("state", "draft"))
        elif e["kind"] == "capa_check":
            row["checks"].append({**b, "_event": event_id(e), "ts": e.get("ts")})
            row["state"] = b.get("outcome_state", row["state"])
        elif e["kind"] == "signature":
            row["signatures"].append({"scope": b.get("scope"), "ts": e.get("ts"), "_event": event_id(e)})
        elif e["kind"] == "retire":
            row["state"] = "retired"
    return rows


def expectation_problems(row: dict) -> list[str]:
    """A CAPA whose expectation cannot fail is not an expectation. The floor's SV-081
    grades the row's completeness; this is the same law applied inside the ledger, so a
    row that reaches the lifecycle without a falsifiable expectation is refused here too."""
    exp = row.get("expectation") or {}
    missing = [k for k in ("metric", "baseline", "target", "horizon_ts") if not str(exp.get(k, "")).strip()]
    probs = [f"expectation missing {k}" for k in missing]
    if not str(row.get("owner_role", "")).strip():
        probs.append("no owner role")
    if not str(row.get("inverse", "")).strip():
        probs.append("no inverse - a CAPA that cannot be unwound is not a patch row")
    return probs


def due_for_grading(events: Iterable[dict], as_of: str) -> list[dict]:
    """CAPAs whose horizon has passed with no effectiveness check on the tape. This is
    the list that must never be empty-by-neglect: a CAPA nobody graded is the failure
    mode 'sustained corrective action' language exists to prevent [H]."""
    now = ts(as_of)
    out = []
    for row in capa_rows(events).values():
        if row["state"] in ("retired",):
            continue
        h = ts((row.get("expectation") or {}).get("horizon_ts"))
        if h and now and h <= now and not row["checks"]:
            out.append(row)
    return sorted(out, key=lambda r: ((r.get("expectation") or {}).get("horizon_ts", ""), r["id"]))


def grade(row: dict, observed: float, data_ref: str, at: str) -> dict:
    """The effectiveness check, as a `capa_check` event body. Mechanical: compare the
    observed value with the target the CAPA itself declared when it was mounted.

    Direction is read from baseline vs target rather than assumed, because half of these
    metrics improve downward (late forms per 100 cases) and half upward (documentation
    completeness), and guessing produces a CAPA that grades itself green while getting
    worse."""
    exp = row.get("expectation") or {}
    target, baseline = exp.get("target"), exp.get("baseline")
    if not isinstance(target, (int, float)) or not isinstance(observed, (int, float)):
        return {"capa_id": row["id"], "result": "cannot-evaluate", "observed": observed,
                "data_ref": data_ref, "graded_at": at,
                "why": "target or observation is not a number - the check says so rather than guessing",
                "outcome_state": row.get("state", "mounted")}
    lower_is_better = isinstance(baseline, (int, float)) and target <= baseline
    met = observed <= target if lower_is_better else observed >= target
    return {"capa_id": row["id"], "result": "met" if met else "unmet",
            "observed": observed, "target": target, "baseline": baseline,
            "direction": "lower-is-better" if lower_is_better else "higher-is-better",
            "data_ref": data_ref, "graded_at": at,
            # met -> sustained; unmet -> back to committee WITH the data. Never closed here:
            # closing is an Act, and an Act crosses under a human signature (law A5).
            "outcome_state": "sustained" if met else "returned_to_committee",
            "returned_with": None if met else {"data_ref": data_ref, "observed": observed, "target": target}}


# ---------------------------------------------------------------- variance triage
def _class_of(b: dict) -> str:
    return str(b.get("variance_class") or b.get("check") or "unclassified")


def triage(events: list[dict], variance: dict, window: tuple[str, str]) -> dict:
    """The three-way discriminator, over the tape. Returns an INVESTIGATION PACKET:
    a question per axis, the evidence behind each answer, and what the answer would
    imply. Every field is a draft for a human; nothing here is a conclusion, and the
    packet says so in its own text."""
    b = body(variance)
    klass = _class_of(b)
    start, end = window
    ev_cov, ev_nov, ev_dis = [], [], []

    # COVERAGE - was anyone in a position to know?
    covering = sorted({str(body(e).get("check")) for e in events
                       if e.get("kind") == "check_result" and body(e).get("check")
                       and str(body(e).get("check")) == str(b.get("check"))})
    mounted_before = [e for e in events if e.get("kind") == "mount"
                      and str(body(e).get("check", "")) == str(b.get("check", ""))
                      and ts(e.get("ts")) and ts(b.get("occurred_ts") or variance.get("ts"))
                      and ts(e["ts"]) <= ts(b.get("occurred_ts") or variance.get("ts"))]
    ev_cov = [event_id(e) for e in mounted_before][:6]
    if not b.get("check"):
        coverage = "no-check-named"
    elif covering and mounted_before:
        coverage = "covered"
    elif covering:
        coverage = "covered-but-mounted-after"
    else:
        coverage = "not-covered"

    # NOVELTY - did the world change?
    same_class = [e for e in events if e.get("kind") == "variance" and _class_of(body(e)) == klass]
    prior = [e for e in same_class if ts(e.get("ts")) and ts(start) and ts(e["ts"]) < ts(start)]
    inside = [e for e in same_class if in_window(e.get("ts"), start, end)]
    ev_nov = [event_id(e) for e in (prior[-3:] + inside[:3])]
    # Two independent facts - nothing before, and several inside - and collapsing them
    # into one label loses the most alarming combination. The four-way split keeps both.
    novelty = (("new-and-recurring" if len(inside) > 1 else "first-in-record") if not prior
               else ("recurring" if len(inside) > 1 else "seen-before"))

    # DISTORTION - does one source systematically disagree?
    sources = Counter(str(body(e).get("source_system") or body(e).get("source") or "unrecorded")
                      for e in inside)
    ev_dis = [event_id(e) for e in inside[:6]]
    top, share = ("", 0.0)
    if sources:
        name, n = sources.most_common(1)[0]
        top, share = name, n / sum(sources.values())
    distortion = ("concentrated" if share >= 0.75 and sum(sources.values()) >= 4 else
                  "spread" if sources else "no-data")

    return {
        "variance": b.get("id") or event_id(variance),
        "class": klass,
        "check": b.get("check"),
        "window": {"start": start, "end": end},
        "axes": {
            "coverage": {"question": "Was anyone in a position to know?",
                         "answer": coverage, "evidence": ev_cov,
                         "implies": {"not-covered": "a hole in the floor - the answer is a new or widened check, not a conversation",
                                     "covered-but-mounted-after": "the check exists now and did not then; check the mount date before reading this as a miss",
                                     "covered": "the check was mounted and did not prevent it - read the check's predicate before reading the case",
                                     "no-check-named": "the variance was filed without naming a check; a human must say what it should have caught"}[coverage]},
            "novelty": {"question": "Did the world change?",
                        "answer": novelty, "evidence": ev_nov,
                        "occurrences_in_window": len(inside), "occurrences_before": len(prior),
                        "implies": {"first-in-record": "nothing like this is on the tape before this window - look for what changed outside the department",
                                    "new-and-recurring": "nothing before this window and more than once inside it - the strongest signal on this axis: something changed, and it is still changing",
                                    "recurring": "more than once in one window - a standing condition, not an incident",
                                    "seen-before": "known class; compare with how the last one closed"}[novelty]},
            "distortion": {"question": "Does one source systematically disagree?",
                           "answer": distortion, "evidence": ev_dis,
                           "top_source": top, "share": round(share, 3),
                           "implies": {"concentrated": f"{round(share * 100)}% of this window's occurrences carry one source - suspect the instrument before the practice",
                                       "spread": "no single source dominates - the condition is general",
                                       "no-data": "no occurrences in the window to compare"}[distortion]},
        },
        "not_a_verdict": ("This packet is an investigation aid. It classifies the SYSTEM's relationship "
                          "to the variance - coverage, novelty, distortion - and deliberately has no axis "
                          "for who was involved. The finding is authored by a person, under their name, "
                          "and only after this is read (laws A5 and B3)."),
    }


# ---------------------------------------------------------------- selftest
def selftest() -> list[str]:
    """Known-good and known-bad inputs for both engines. Returns failures; [] = green."""
    f: list[str] = []
    base = {"id": "CAPA-1", "owner_role": "quality_manager", "inverse": "retire",
            "expectation": {"metric": "late_forms_per_100", "baseline": 6, "target": 2,
                            "horizon_ts": "2026-06-30T00:00:00Z"}}

    # direction is read, not assumed
    g = grade(base, 1, "FOLD-A", "2026-07-01T00:00:00Z")
    if g["result"] != "met" or g["direction"] != "lower-is-better":
        f.append(f"lower-is-better met: {g}")
    if grade(base, 5, "FOLD-A", "2026-07-01T00:00:00Z")["result"] != "unmet":
        f.append("lower-is-better unmet not detected")
    up = {**base, "expectation": {**base["expectation"], "baseline": 60, "target": 90}}
    if grade(up, 95, "F", "2026-07-01T00:00:00Z")["result"] != "met":
        f.append("higher-is-better met not detected")
    if grade(up, 70, "F", "2026-07-01T00:00:00Z")["result"] != "unmet":
        f.append("higher-is-better unmet not detected")
    # unmet never closes; met never closes silently either - both route onward
    if grade(base, 5, "F", "2026-07-01T00:00:00Z")["outcome_state"] != "returned_to_committee":
        f.append("unmet must return to committee")
    if grade(base, 5, "F", "2026-07-01T00:00:00Z")["returned_with"] is None:
        f.append("unmet must return WITH the data attached")
    if grade(base, 1, "F", "2026-07-01T00:00:00Z")["outcome_state"] != "sustained":
        f.append("met must land sustained")
    # a non-numeric observation abstains rather than guessing
    if grade(base, "n/a", "F", "2026-07-01T00:00:00Z")["result"] != "cannot-evaluate":
        f.append("non-numeric observation must abstain")
    # an unfalsifiable expectation is refused
    if not expectation_problems({"owner_role": "x", "inverse": "retire",
                                 "expectation": {"metric": "", "baseline": "", "target": "", "horizon_ts": "2026-01-01T00:00:00Z"}}):
        f.append("an expectation with no metric/baseline/target must be refused")
    if expectation_problems(base):
        f.append(f"a complete row must pass: {expectation_problems(base)}")

    # due_for_grading: past horizon and ungraded
    evs = [{"kind": "capa", "ts": "2026-05-01T00:00:00Z", "i": 1, "body": {**base, "status": "mounted"}}]
    if [r["id"] for r in due_for_grading(evs, "2026-07-01T00:00:00Z")] != ["CAPA-1"]:
        f.append("a CAPA past its horizon with no check must be due")
    if due_for_grading(evs, "2026-06-01T00:00:00Z"):
        f.append("a CAPA before its horizon is not due")
    graded = evs + [{"kind": "capa_check", "ts": "2026-07-01T00:00:00Z", "i": 2,
                     "body": grade(base, 1, "F", "2026-07-01T00:00:00Z")}]
    if due_for_grading(graded, "2026-07-02T00:00:00Z"):
        f.append("a graded CAPA is not still due")
    if capa_rows(graded)["CAPA-1"]["state"] != "sustained":
        f.append("a met grade must fold the row to sustained")

    # triage: three axes, no fourth
    W = ("2026-06-01T00:00:00Z", "2026-07-01T00:00:00Z")
    vs = [{"kind": "variance", "ts": f"2026-06-0{d}T00:00:00Z", "i": 10 + d,
           "body": {"id": f"VAR-{d}", "variance_class": "documentation", "check": "SV-013",
                    "source_system": "records-A" if d < 5 else "records-B",
                    "occurred_ts": f"2026-06-0{d}T00:00:00Z"}} for d in range(1, 6)]
    p = triage(vs, vs[-1], W)
    if set(p["axes"]) != set(TRIAGE_AXES):
        f.append(f"triage must have exactly the three axes: {sorted(p['axes'])}")
    if p["axes"]["novelty"]["answer"] != "new-and-recurring":
        f.append(f"nothing before + five inside is new-and-recurring: {p['axes']['novelty']}")
    older = [{"kind": "variance", "ts": "2026-01-09T00:00:00Z", "i": 5,
              "body": {"id": "VAR-0", "variance_class": "documentation", "check": "SV-013"}}]
    if triage(older + vs, vs[-1], W)["axes"]["novelty"]["answer"] != "recurring":
        f.append("a prior occurrence plus several inside is recurring, not new")
    if triage(older + vs[:1], vs[0], W)["axes"]["novelty"]["answer"] != "seen-before":
        f.append("a prior occurrence plus one inside is seen-before")
    if p["axes"]["distortion"]["answer"] != "concentrated":
        f.append(f"4 of 5 from one source is concentrated: {p['axes']['distortion']}")
    if p["axes"]["coverage"]["answer"] != "not-covered":
        f.append(f"no check_result on the tape means not-covered: {p['axes']['coverage']}")
    blob = str(p).lower()
    for forbidden in ("staff_name", "employee", "who_was", "person_id", "blame"):
        if forbidden in blob:
            f.append(f"a packet must never carry {forbidden!r}")
    if not p.get("not_a_verdict"):
        f.append("a packet must say in its own text that it is not a verdict")
    return f


if __name__ == "__main__":
    import sys
    fails = selftest()
    print("\n".join(fails) if fails else "lifecycle selftest: green (CAPA grading + variance triage)")
    sys.exit(1 if fails else 0)
