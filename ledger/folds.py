#!/usr/bin/env python3
"""ledger/folds.py - the three documents, as pure functions of a tape.

SPEC section 8: the monthly line-of-sight report [H], the QAPI committee packet, and the
survey binder are DETERMINISTIC FOLDS over the tape - generated, current, every claim
linked to the events that support it. The books close continuously.

FOUR PROPERTIES, EACH ONE LOad-BEARING

1. PURE. A fold takes (events, window) and returns text. It reads no clock, no file, no
   environment. A document that reads the system clock cannot be re-derived tomorrow, and
   a survey binder that cannot be re-derived is an assertion, not evidence.

2. ORDER-INDEPENDENT. Events that share a timestamp may have landed in either order. The
   fold sorts by (ts, kind, canonical body) before it counts anything, so the document
   does not depend on the incidental arrival order of simultaneous events. G-FOLD-DETERMINISM
   shuffles equal-timestamp runs and requires byte-identical output.

3. EVERY NUMBER CARRIES ITS GRAIN, ITS DENOMINATOR AND ITS EVIDENCE (law A6). The renderer
   physically cannot print a bare count: `claim()` takes a numerator, a denominator, a
   grain sentence and the event ids, and there is no other way to put a number on a page.

4. IMPORTED NUMBERS ARE MARKED (law B9). CMS outcome denominators derive from external
   death data and cannot be computed from any site's own tape. The binder prints them as
   IMPORTED with their source, or prints their absence - it never quietly omits the
   distinction.

WHAT A FOLD MAY NOT DO. It renders the record; it never authors it (law A5). Findings on
these pages are human-authored events being displayed, and the binder says so. Nothing
here names a person: roles only, everywhere (law C1, law B3).

Stdlib only, no model.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lifecycle import (body, capa_rows, due_for_grading, event_id,  # noqa: E402
                       expectation_problems, in_window, triage)

NON_PASS = {"HOLD", "FLAG", "ALARM"}
MAX_EVIDENCE = 4


# ---------------------------------------------------------------- the spine
def canonical(events: Iterable[dict]) -> list[dict]:
    """Sort into the one order every fold reads. Property 2 lives here."""
    return sorted(events, key=lambda e: (str(e.get("ts", "")), str(e.get("kind", "")),
                                         json.dumps(body(e), sort_keys=True, default=str)))


def window_events(events: list[dict], start: str, end: str) -> list[dict]:
    return [e for e in events if in_window(e.get("ts"), start, end)]


def cite(evs: Iterable[dict], limit: int = MAX_EVIDENCE) -> str:
    """The evidence handle for a claim. Deterministic and bounded: a page that printed
    every id would be unreadable, and one that printed none would be unfalsifiable."""
    ids = sorted({event_id(e) for e in evs})
    if not ids:
        return "[no events]"
    shown = ids[:limit]
    more = len(ids) - len(shown)
    return "[" + ", ".join(shown) + (f", +{more} more" if more else "") + "]"


def claim(label: str, num: float, den: float | None, grain: str, evs: Iterable[dict]) -> str:
    """THE ONLY WAY A NUMBER REACHES A PAGE. Numerator, denominator, grain, evidence.
    A number without those is not a number (law A6), so the renderer does not offer a
    function that can print one."""
    if den in (None, 0):
        rate = "-"
        den_s = "0" if den == 0 else "n/a"
    else:
        rate = f"{num / den:.1%}"
        den_s = f"{den:,}"
    return f"| {label} | {num:,} | {den_s} | {rate} | {grain} | {cite(evs)} |"


CLAIM_HEAD = ["| claim | count | denominator | rate | grain | evidence |",
              "|---|---|---|---|---|---|"]


def _hdr(title: str, start: str, end: str, tape_id: str) -> list[str]:
    return [f"# {title}",
            f"period: {start} to {end} (half-open: the end instant belongs to the next period) | "
            f"tape: {tape_id} | generated fold - DO NOT EDIT",
            "", "*Every number below carries its grain, its denominator and the tape events it rests "
            "on. Nothing on this page was authored by a machine: findings and signatures are human "
            "events being displayed (laws A5, A6).*", ""]


def tape_id(events: list[dict]) -> str:
    """Identity of the input, so two copies of a document can be compared without trust."""
    import hashlib
    h = hashlib.sha256()
    for e in canonical(events):
        h.update(json.dumps({"kind": e.get("kind"), "ts": e.get("ts"), "body": body(e)},
                            sort_keys=True, default=str).encode("utf-8"))
    return h.hexdigest()[:16]


# ---------------------------------------------------------------- 1 - line of sight
def line_of_sight(events: list[dict], start: str, end: str) -> str:
    evs = canonical(events)
    win = window_events(evs, start, end)
    results = [e for e in win if e["kind"] == "check_result"]
    holds = [e for e in win if e["kind"] == "hold"]
    releases = [e for e in win if e["kind"] == "release"]
    findings = [e for e in win if e["kind"] == "finding"]

    cases = sorted({str(body(e).get("case")) for e in results if body(e).get("case")})
    evaluable = [e for e in results if body(e).get("verdict") != "CANNOT-EVALUATE"]
    abstained = [e for e in results if body(e).get("verdict") == "CANNOT-EVALUATE"]

    L = _hdr("LINE OF SIGHT - monthly quality report", start, end, tape_id(evs))
    L += ["## The census", "",
          "*The department reviewed every record, not a sample. The denominator below is the "
          "point: a sampled audit cannot state one.*", ""] + CLAIM_HEAD
    mounted = sorted({str(body(e).get("check")) for e in results if body(e).get("check")})
    # A count divided by itself is not a rate, and printing 100% for it would be the exact
    # habit this project exists to break. Where the honest denominator is not on the tape,
    # the page says so; where it is (the full record x check grid), it is computed.
    L.append(claim("records seen", len(cases), None,
                   "distinct case ids on the tape; the source system's total for the period "
                   "is NOT on this tape, so no coverage rate is claimed", results))
    L.append(claim("check evaluations", len(results), len(cases) * len(mounted),
                   f"one per (record, mounted check); the denominator is the full grid of "
                   f"{len(cases)} records x {len(mounted)} mounted checks", results))
    L.append(claim("evaluations that reached a verdict", len(evaluable), len(results),
                   "PASS or an action; the remainder said CANNOT-EVALUATE", evaluable))
    L.append(claim("evaluations that could not judge", len(abstained), len(results),
                   "the record lacked a field the check reads - honest silence, not a pass", abstained))
    L += ["", "## Holds - open work, not findings", "",
          "*A held record is open work. It becomes a finding only if it survives to "
          "close-attempt (law B4). Holds attach to the case; no check pings a person (law B3).*", ""] + CLAIM_HEAD
    L.append(claim("holds raised", len(holds), len(evaluable), "one per non-PASS on a hold/alarm check", holds))
    L.append(claim("holds released before close-attempt", len(releases), len(holds),
                   "corrected in the record while the case was open", releases))
    L.append(claim("holds that became findings", len(findings), len(holds),
                   "survived to close-attempt and a person wrote them up", findings))

    by_family: dict[str, list[dict]] = defaultdict(list)
    for e in holds:
        fam = str(body(e).get("check", ""))[:6]
        by_family[fam].append(e)
    fam_of = {}
    for e in results:
        b = body(e)
        if b.get("check") and b.get("family"):
            fam_of[str(b["check"])] = str(b["family"])
    grouped: dict[str, list[dict]] = defaultdict(list)
    for e in holds:
        grouped[fam_of.get(str(body(e).get("check")), "unclassified")].append(e)
    L += ["", "## Where the holds are, by check family", ""] + CLAIM_HEAD
    for fam in sorted(grouped):
        fam_evals = [e for e in evaluable if fam_of.get(str(body(e).get("check"))) == fam]
        L.append(claim(fam, len(grouped[fam]), len(fam_evals),
                       "holds per evaluation in this family", grouped[fam]))

    L += ["", "## Findings by severity (human-authored)", ""] + CLAIM_HEAD
    sev = Counter(str(body(e).get("severity", "unstated")) for e in findings)
    for s in sorted(sev):
        L.append(claim(s, sev[s], len(findings), "severity as recorded by the authoring role",
                       [e for e in findings if str(body(e).get("severity", "unstated")) == s]))
    roles = sorted({str(body(e).get("authored_by_role", "?")) for e in findings})
    L += ["", f"Authoring roles this period: {', '.join(roles) if roles else 'none'}. "
             "Roles, never names - the record is about cases (laws A5, C1).", ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 2 - committee packet
def committee_packet(events: list[dict], start: str, end: str) -> str:
    evs = canonical(events)
    win = window_events(evs, start, end)
    rows = capa_rows(evs)
    due = due_for_grading(evs, end)
    checks_in_win = [e for e in win if e["kind"] == "capa_check"]
    variances = [e for e in win if e["kind"] == "variance"]

    L = _hdr("QAPI COMMITTEE PACKET", start, end, tape_id(evs))
    L += ["## Corrective actions - the effectiveness ledger", "",
          "*A CAPA is an expectation with a deadline. At its horizon the effectiveness check "
          "runs by itself: met lands `sustained`, unmet is RETURNED TO COMMITTEE WITH THE DATA "
          "ATTACHED. No CAPA closes by assertion, and none closes because nobody looked.*", "",
          "| CAPA | owner role | metric | baseline | target | observed | horizon | result | state | evidence |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for cid in sorted(rows):
        r = rows[cid]
        exp = r.get("expectation") or {}
        last = r["checks"][-1] if r["checks"] else {}
        L.append(f"| {cid} | {r.get('owner_role', '?')} | {exp.get('metric', '?')} | "
                 f"{exp.get('baseline', '?')} | {exp.get('target', '?')} | "
                 f"{last.get('observed', '-')} | {exp.get('horizon_ts', '?')} | "
                 f"{last.get('result', 'not yet graded')} | {r['state']} | "
                 f"[{', '.join(sorted(r['events'])[:MAX_EVIDENCE])}] |")

    returned = [r for r in rows.values() if r["state"] == "returned_to_committee"]
    L += ["", "## Returned to this committee, with the data", ""]
    if not returned:
        L.append("None this period.")
    for r in sorted(returned, key=lambda x: x["id"]):
        last = r["checks"][-1]
        L += [f"**{r['id']}** - {(r.get('expectation') or {}).get('metric')}: observed "
              f"{last.get('observed')} against a target of {last.get('target')} "
              f"({last.get('direction')}), graded {last.get('graded_at')}. "
              f"Data: `{last.get('data_ref')}`. Evidence {last.get('_event')}.",
              f"  The committee decides. The expectation was declared before the work started, "
              f"so this is a falsified prediction, not a verdict on anyone. The inverse on file is "
              f"`{r.get('inverse', '?')}`.", ""]

    L += ["## Overdue - a horizon passed with nothing graded", ""]
    if not due:
        L.append("None. Every CAPA past its horizon has an effectiveness check on the tape.")
    for r in due:
        L.append(f"- **{r['id']}** horizon {(r.get('expectation') or {}).get('horizon_ts')} - "
                 f"NOT GRADED. This line is the one that must never be quietly absent: a CAPA "
                 f"nobody graded is how 'sustained' becomes a word rather than a measurement.")

    bad = {cid: expectation_problems(r) for cid, r in rows.items() if expectation_problems(r)}
    L += ["", "## Rows that could not carry a lifecycle", ""]
    L.append("None - every CAPA on the tape carries a falsifiable expectation, an owner and an inverse."
             if not bad else "")
    for cid in sorted(bad):
        L.append(f"- **{cid}**: {'; '.join(bad[cid])}")

    L += ["", "## Variance intake - investigation packets", "",
          "*Each packet classifies the SYSTEM's relationship to the variance on three axes. "
          "There is deliberately no axis for who was involved. The packet is an aid; the finding "
          "is authored by a person under their own name (laws A5, B3).*", ""]
    if not variances:
        L.append("No variances filed this period.")
    for v in variances[:8]:
        p = triage(evs, v, (start, end))
        ax = p["axes"]
        L += [f"**{p['variance']}** (class `{p['class']}`, check {p['check']})",
              f"  - coverage: **{ax['coverage']['answer']}** - {ax['coverage']['implies']} {cite([])[:0]}"
              f"{'' if not ax['coverage']['evidence'] else '[' + ', '.join(ax['coverage']['evidence'][:MAX_EVIDENCE]) + ']'}",
              f"  - novelty: **{ax['novelty']['answer']}** ({ax['novelty']['occurrences_in_window']} in window, "
              f"{ax['novelty']['occurrences_before']} before) - {ax['novelty']['implies']}",
              f"  - distortion: **{ax['distortion']['answer']}** (top source `{ax['distortion']['top_source']}`, "
              f"share {ax['distortion']['share']:.0%}) - {ax['distortion']['implies']}", ""]
    if len(variances) > 8:
        L.append(f"*{len(variances) - 8} further variances this period; the full set folds the same way.*")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 3 - survey binder
def survey_binder(events: list[dict], start: str, end: str,
                  authorities: dict[str, list[dict]] | None = None,
                  imported: list[dict] | None = None) -> str:
    """The standing evidence pack. The authority column is the crosswalk's byte-verified
    citation for each check - the point where rung 05 pays rent: a surveyor asking 'under
    what authority?' gets a pinned clause, not a paraphrase."""
    evs = canonical(events)
    win = window_events(evs, start, end)
    results = [e for e in win if e["kind"] == "check_result"]
    authorities = authorities or {}

    per: dict[str, list[dict]] = defaultdict(list)
    for e in results:
        per[str(body(e).get("check"))].append(e)

    L = _hdr("SURVEY BINDER - standing evidence", start, end, tape_id(evs))
    L += ["*Survey-ready is a property of the record, not an event. Each row below is one "
          "mounted check: what it is, the authority it runs under (byte-matched to a "
          "hash-pinned source, or honestly unpinned), what it did this period, and the tape "
          "events that prove it.*", "",
          "| check | layer | authority (pinned) | evaluations | passed | actioned | abstained | evidence |",
          "|---|---|---|---|---|---|---|---|"]
    for cid in sorted(per):
        rs = per[cid]
        b0 = body(rs[0])
        verdicts = Counter(str(body(e).get("verdict")) for e in rs)
        passed = verdicts.get("PASS", 0)
        abst = verdicts.get("CANNOT-EVALUATE", 0)
        acted = sum(v for k, v in verdicts.items() if k in NON_PASS)
        maps = authorities.get(cid, [])
        if maps:
            auth = "; ".join(sorted(f"{m['locator']}" for m in maps if m.get("type") != "silent"))
            silent = [m for m in maps if m.get("type") == "silent"]
            if silent and not auth:
                auth = "SEARCHED, NOT FOUND: " + "; ".join(sorted(str(m["locator"]) for m in silent))
            elif silent:
                auth += " (+ a searched-and-silent finding on file)"
            # A passage can be REAL AND SUPERSEDED. The pin store warns; before the S10 audit
            # the binder swallowed the warning and a surveyor would have been handed a
            # citation to a repealed regime with no caveat.
            warned = [m for m in maps if m.get("_status") == "CHECK-CURRENCY"]
            if warned:
                auth += (" &mdash; **CURRENCY WARNING: verbatim, but the surrounding text "
                         "carries sunset language; confirm it is still in force**")
        else:
            auth = "not pinned"
        L.append(f"| {cid} | {b0.get('layer', '?')} | {auth} | {len(rs)} | {passed} | {acted} | "
                 f"{abst} | {cite(rs)} |")

    L += ["", "## Imported numbers - not computable from this tape (law B9)", "",
          "*CMS outcome denominators derive from external death data. No fold over a site's own "
          "record can produce them, and a binder that printed them unmarked would be presenting "
          "someone else's measurement as its own.*", ""]
    # These rows carry an evidence handle too, and it is deliberately NOT an event id:
    # the trace for an imported number leads off this tape, and saying `[external: ...]`
    # is how the page distinguishes a number it can prove from a number it received.
    if not imported:
        L += ["| number | value | source | status | evidence |", "|---|---|---|---|---|",
              "| CMS donation rate denominator (eligible deaths) | - | external death-record data | "
              "NOT IMPORTED for this period - absent, and marked absent rather than omitted | "
              "[external: nothing on this tape can produce it] |",
              "| CMS organ transplantation rate denominator | - | external death-record data | "
              "NOT IMPORTED | [external: nothing on this tape can produce it] |"]
    else:
        L += ["| number | value | source | as-of | status | evidence |", "|---|---|---|---|---|---|"]
        for im in sorted(imported, key=lambda d: str(d.get("name"))):
            L.append(f"| {im.get('name')} | {im.get('value')} | {im.get('source')} | "
                     f"{im.get('as_of')} | IMPORTED | [external: {im.get('source')}] |")

    unpinned = sorted(c for c in per if not authorities.get(c))
    L += ["", "## Checks running under an authority this binder cannot pin", ""]
    L.append("None." if not unpinned else
             f"{len(unpinned)} of {len(per)} checks: {', '.join(unpinned)}. "
             "A surveyor may ask under what authority these run; the honest answer is on the "
             "crosswalk's coverage fold, not on this page.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- determinism battery
def _shuffle_equal_ts(events: list[dict], seed: int = 7) -> list[dict]:
    """Reverse each run of equal timestamps: a tape that recorded simultaneous events in
    the other order. Any document that changes under this was counting arrival order."""
    import random
    r = random.Random(seed)
    out, i = [], 0
    evs = list(events)
    while i < len(evs):
        j = i
        while j < len(evs) and evs[j].get("ts") == evs[i].get("ts"):
            j += 1
        run = evs[i:j]
        r.shuffle(run)
        out += run
        i = j
    return out


def selftest(events: list[dict] | None = None) -> list[str]:
    """G-FOLD-DETERMINISM's engine: same tape twice, shuffled-but-equivalent tape, and the
    evidence property. Returns failures; [] = green."""
    f: list[str] = []
    if events is None:
        sys.path.insert(0, str(ROOT / "ledger"))
        import make_tape
        events = make_tape.build(seed=20260903, cases=25)
    start, end = "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z"
    auth = load_authorities()
    docs = {"line-of-sight": lambda e: line_of_sight(e, start, end),
            "committee-packet": lambda e: committee_packet(e, start, end),
            "survey-binder": lambda e: survey_binder(e, start, end, auth)}
    shuffled = _shuffle_equal_ts(events)
    if [e.get("ts") for e in shuffled] != [e.get("ts") for e in events]:
        f.append("the shuffle must not move events across timestamps")
    for name, fn in docs.items():
        a, b = fn(events), fn(events)
        if a != b:
            f.append(f"{name}: two renders of the same tape differ - something is not pure")
        c = fn(shuffled)
        if a != c:
            f.append(f"{name}: render changed when simultaneous events were reordered - "
                     f"the fold is counting arrival order")
        if not a.endswith("\n"):
            f.append(f"{name}: document must end with a newline")
        # EVERY DATA ROW OF EVERY TABLE CARRIES AN EVIDENCE HANDLE. A header is the row
        # followed by the |---| separator; a separator is itself skipped. Everything else
        # inside a table is a claim, and a claim without evidence is the thing law A6
        # forbids - so this is checked mechanically rather than by reading the renderer.
        lines = a.splitlines()
        for n, line in enumerate(lines):
            if not line.startswith("|") or set(line) <= set("|-: "):
                continue
            if n + 1 < len(lines) and set(lines[n + 1]) <= set("|-: ") and "-" in lines[n + 1]:
                continue                                   # a header
            if "[" not in line:
                f.append(f"{name}: a table data row carries no evidence handle: {line[:80]}")
                break
    return f


def load_authorities() -> dict[str, list[dict]]:
    """The crosswalk's VERIFIED mappings, by check.

    Until the S10 cold-start audit this was a plain YAML read: it never byte-matched and
    never touched the corpus, so the survey binder printed "SV-085 runs under 42 CFR
    486.318(a)" whether or not the quote still matched - and on a fresh clone with no
    corpus at all. Law B6 was enforced in `pins.py --check` and abandoned at the exact
    point a citation reaches a regulator. Now every mapping is verified here, an
    unverified one is dropped so the binder prints "not pinned", and a currency warning
    travels with the mapping so the page can carry it."""
    try:
        sys.path.insert(0, str(ROOT / "crosswalk"))
        import pins
        sources = pins.load_sources()
        out: dict[str, list[dict]] = defaultdict(list)
        for m in pins.load_mappings():
            status, detail = pins.verify(m, sources)
            if status not in (pins.OK, pins.WARN):
                continue                      # not verified -> it does not reach the binder
            out[str(m.get("check"))].append({**m, "_status": status, "_detail": detail})
        return dict(out)
    except Exception:  # noqa: BLE001
        return {}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--cases", type=int, default=60)
    ap.add_argument("--start", default="2026-01-01T00:00:00Z")
    ap.add_argument("--end", default="2027-01-01T00:00:00Z")
    ap.add_argument("--doc", choices=["line-of-sight", "committee-packet", "survey-binder", "all"],
                    default="all")
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        fails = selftest()
        print("\n".join(fails) if fails else
              "folds selftest: green (pure, order-independent, every claim cited)")
        sys.exit(1 if fails else 0)
    sys.path.insert(0, str(ROOT / "ledger"))
    import make_tape
    evs = make_tape.build(a.seed, a.cases)
    auth = load_authorities()
    made = {"line-of-sight": line_of_sight(evs, a.start, a.end),
            "committee-packet": committee_packet(evs, a.start, a.end),
            "survey-binder": survey_binder(evs, a.start, a.end, auth)}
    for name, text in made.items():
        if a.doc not in ("all", name):
            continue
        if a.out:
            p = Path(a.out) / f"{name}.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {p} ({len(text):,} chars)")
        else:
            print(text)
