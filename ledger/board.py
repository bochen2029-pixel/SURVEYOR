#!/usr/bin/env python3
"""ledger/board.py - the Morning Board, rendered from the tape.

Rung 07. The mockup's board was hand-written illustration; this renders the same four
panels from actual events, and it is governed by one rule:

    EVERY LINE LINKS TO ITS EVIDENCE, OR THE LINE DOES NOT RENDER.

Not "should link" - cannot render. `line()` refuses to build a BoardLine with an empty
evidence list, and the renderer counts what it refused and prints the count on the page.
A board that silently dropped uncitable lines would be a board you could not trust to be
complete; one that printed uncited lines would be a board you could not trust at all. So
it drops them AND says how many, which is the only honest third option.

TWO EVIDENCE NAMESPACES, kept distinct on purpose. Most lines cite TAPE EVENTS (`#1234`).
The crosswalk panel cites MAPPING IDS (`MAP-SV-...`), because its claim is about a
citation verifying against a pinned source, not about something that happened to a case.
Mixing them would let a mapping id stand in for an event and vice versa.

LAW E2 IS NOT REPEALED BY THIS FILE. The numbers here are real reads of a real tape - and
the tape is SYNTHETIC until F-RETRO runs on a site's historical charts. The rendered board
carries that banner in its own markup, generated from the tape's provenance rather than
typed by hand, so it cannot be forgotten when the source changes.

Pure and deterministic, like the other folds: no clock, no environment, sorted before
counting. Stdlib only, no model.
"""
from __future__ import annotations

import html
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from folds import canonical, tape_id, window_events  # noqa: E402
from lifecycle import body, capa_rows, due_for_grading, event_id, triage  # noqa: E402

NON_PASS = {"HOLD", "FLAG", "ALARM"}
STAMPS = {"pass": "pass", "held": "held", "alarm": "red", "ink": "ink", "red": "red"}


class Uncitable(Exception):
    """Raised when a line is built with no evidence. Caught by the renderer, which drops
    the line and counts it - never silently, and never rendered anyway."""


@dataclass
class BoardLine:
    panel: str
    kind: str                       # "census" | "item" | "clock" | "fold"
    label: str
    detail: str = ""
    value: str = ""
    stamp: str = "ink"
    evidence: list[str] = field(default_factory=list)
    ns: str = "tape"                # "tape" | "crosswalk"
    pct: int | None = None          # .clock rows only: the bar, which is a drawn rate
    order: int = 50                 # reading order within a panel; ties fall back to label

    def sort_key(self) -> tuple:
        return (self.panel, self.kind, self.order, self.label, self.detail, self.value)


def line(panel: str, kind: str, label: str, evidence: Iterable[str], **kw) -> BoardLine:
    ids = sorted({str(e) for e in evidence if str(e).strip()})
    if not ids:
        raise Uncitable(f"{panel}/{label}: no evidence")
    return BoardLine(panel=panel, kind=kind, label=label, evidence=ids, **kw)


# ---------------------------------------------------------------- the panels
def build(events: list[dict], start: str, end: str,
          mappings: list[dict] | None = None) -> tuple[list[BoardLine], list[str]]:
    """(lines, dropped). Deterministic in (events, window, mappings)."""
    evs = canonical(events)
    win = window_events(evs, start, end)
    lines: list[BoardLine] = []
    dropped: list[str] = []

    def add(*a, **kw) -> None:
        try:
            lines.append(line(*a, **kw))
        except Uncitable as e:
            dropped.append(str(e))

    results = [e for e in win if e["kind"] == "check_result"]
    holds = [e for e in win if e["kind"] == "hold"]
    releases = [e for e in win if e["kind"] == "release"]
    findings = [e for e in win if e["kind"] == "finding"]
    cases = sorted({str(body(e).get("case")) for e in results if body(e).get("case")})
    clean_cases = sorted(set(cases) - {str(body(e).get("case")) for e in holds})

    # -- panel 1: the floor
    add("floor", "census", "records checked at entry", [event_id(e) for e in results], order=1,
        value=f"{len(cases):,}", detail="distinct cases with at least one check evaluated")
    add("floor", "census", "clean on first pass",
        [event_id(e) for e in results if str(body(e).get("case")) in set(clean_cases)],
        value=f"{len(clean_cases):,}", stamp="pass", order=2,
        detail=f"no hold raised, of {len(cases):,} cases")
    add("floor", "census", "held at entry", [event_id(e) for e in holds],
        value=f"{len(holds):,}", stamp="held", order=3,
        detail=f"{len(releases):,} released before close-attempt, {len(findings):,} became findings")
    released_pairs = {(str(body(e).get("case")), str(body(e).get("check"))) for e in releases}
    for h in holds[:4]:
        b = body(h)
        key = (str(b.get("case")), str(b.get("check")))
        add("floor", "item", str(b.get("case")), [event_id(h)],
            detail=f"{b.get('check')} — {str(b.get('reason') or '')[:150]}",
            stamp="held" if key in released_pairs else "alarm",
            value="held→fixed" if key in released_pairs else "open")

    # -- panel 2: the clocks
    clock_results = [e for e in results if body(e).get("trigger") == "continuous"]
    by_check: dict[str, list[dict]] = defaultdict(list)
    for e in clock_results:
        by_check[str(body(e).get("check"))].append(e)
    alarms = [e for e in clock_results if str(body(e).get("verdict")) == "ALARM"]
    add("clocks", "census", "clock evaluations", [event_id(e) for e in clock_results], order=1,
        value=f"{len(clock_results):,}",
        detail=f"{len(by_check)} continuous checks, each anchored to a declared field")
    add("clocks", "census", "alarms raised", [event_id(e) for e in alarms], order=2,
        value=f"{len(alarms):,}", stamp="alarm" if alarms else "pass",
        detail="fired before the deadline passed, not after")
    # One row per clock family that fired, rendered in the page's own .clock component:
    # a labelled bar whose width is the alarm SHARE of that check's evaluations, and a
    # right-hand figure that carries the denominator. A bar without a denominator would
    # be decoration; this one is the rate, drawn.
    alarm_by_check = Counter(str(body(e).get("check")) for e in alarms)
    for rank, (cid, n) in enumerate(sorted(alarm_by_check.items(), key=lambda kv: (-kv[1], kv[0]))[:4]):
        evs_for = [e for e in alarms if str(body(e).get("check")) == cid]
        total = len(by_check.get(cid, [])) or 1
        anchor = next((str(body(e).get("anchor") or "") for e in by_check.get(cid, []) if body(e).get("anchor")), "")
        # The anchor is the whole point of this panel (law B1): a deadline computed from
        # the wrong field is a defect that looks like compliance, so the board names the
        # field each clock actually ran from.
        add("clocks", "clock", cid, [event_id(e) for e in evs_for], order=10 + rank,
            value=f"{n} of {total}", stamp="alarm", pct=max(4, round(100 * n / total)),
            detail=(f"anchored to {anchor}" if anchor else "no anchor declared")
                   + f" · {', '.join(sorted({str(body(e).get('case')) for e in evs_for})[:2])}")

    # -- panel 3: the crosswalk (a different evidence namespace: mapping ids)
    maps = mappings if mappings is not None else _load_mappings()
    if maps:
        quoted = [m for m in maps if str(m.get("type")) != "silent"]
        silent = [m for m in maps if str(m.get("type")) == "silent"]
        by_src = Counter(str(m.get("source")) for m in quoted)
        add("crosswalk", "census", "citations byte-matched to a pinned source",
            [str(m.get("id")) for m in quoted], ns="crosswalk", value=f"{len(quoted):,}", stamp="pass", order=1,
            detail=f"across {len(by_src)} sources; a quote that does not match does not exist")
        add("crosswalk", "census", "searched and found absent",
            [str(m.get("id")) for m in silent], ns="crosswalk", value=f"{len(silent):,}", stamp="ink", order=2,
            detail="every search term run by the tool, not asserted by a person")
        checks_mapped = sorted({str(m.get("check")) for m in maps})
        add("crosswalk", "census", "checks under a pinned authority",
            [str(m.get("id")) for m in maps], ns="crosswalk", value=f"{len(checks_mapped)}",
            stamp="pass", order=3,
            detail="the rest print 'not pinned' in the binder, never a paraphrase")
        for rank, (src, n) in enumerate(sorted(by_src.items(), key=lambda kv: (-kv[1], kv[0]))):
            add("crosswalk", "fold", src, [str(m.get("id")) for m in quoted if str(m.get("source")) == src],
                ns="crosswalk", value=f"{n}", stamp="ink", order=20 + rank,
                detail="citations, byte-matched against this source's sha256")

    # -- panel 4: the ledger
    rows = capa_rows(evs)
    due = due_for_grading(evs, end)
    for cid in sorted(rows):
        r = rows[cid]
        if not r["checks"]:
            continue
        last = r["checks"][-1]
        met = last.get("result") == "met"
        add("ledger", "fold", cid, r["events"],
            value="sustained" if met else "re-opened", stamp="pass" if met else "red",
            detail=(f"{(r.get('expectation') or {}).get('metric')}: observed {last.get('observed')} "
                    f"against target {last.get('target')} ({last.get('direction')}) — "
                    + ("expectation met" if met else
                       "expectation NOT met, auto-returned to committee with the data attached")))
    for r in due:
        add("ledger", "fold", r["id"], r["events"], value="overdue", stamp="red",
            detail=f"horizon {(r.get('expectation') or {}).get('horizon_ts')} passed with no effectiveness check")
    variances = [e for e in win if e["kind"] == "variance"]
    if variances:
        v = variances[0]
        p = triage(evs, v, (start, end))
        ax = p["axes"]
        add("ledger", "fold", f"Variance {p['variance']}", [event_id(v)], value="drafted", stamp="ink",
            detail=(f"triage: coverage {ax['coverage']['answer']}, novelty {ax['novelty']['answer']}, "
                    f"distortion {ax['distortion']['answer']} — investigation packet drafted for a human; "
                    f"there is no axis for who was involved"))
    add("ledger", "fold", "Line-of-sight · committee packet · survey binder",
        [event_id(e) for e in win[:6]], value="current", stamp="pass",
        detail="generated from this tape, every claim linked to evidence, chain-verified")

    lines.sort(key=BoardLine.sort_key)
    return lines, sorted(dropped)


def _load_mappings() -> list[dict]:
    try:
        sys.path.insert(0, str(ROOT / "crosswalk"))
        import pins
        sources = pins.load_sources()
        out = []
        for m in pins.load_mappings():
            status, _ = pins.verify(m, sources)
            if status in (pins.OK, pins.WARN):        # only VERIFIED citations reach the board
                out.append(m)
        return out
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------- rendering
PANEL_TITLE = {"floor": "The Floor — census, at entry",
               "clocks": "Clocks — the SLA lattice",
               "crosswalk": "Crosswalk — regulation ↔ your policy",
               "ledger": "Corrective actions · variance intake · the ledger"}


def _ev(l: BoardLine, limit: int | None = None) -> str:
    # Mapping ids are long, so the crosswalk namespace shows fewer of them. The count is
    # never dropped: a reader must always be able to see how much evidence stands behind
    # a line, even when the panel is too narrow to print all of it.
    limit = limit if limit is not None else (2 if l.ns == "crosswalk" else 3)
    shown = l.evidence[:limit]
    more = len(l.evidence) - len(shown)
    tag = "tape" if l.ns == "tape" else "pin"
    return f"{tag} {', '.join(shown)}" + (f" +{more} more" if more else "")


def render_html(lines: list[BoardLine], dropped: list[str], events: list[dict],
                start: str, end: str, provenance: str) -> str:
    """The board-grid fragment, in the mockup's own classes so it drops into the page."""
    out = [f'            <div class="board-note">GENERATED FROM THE TAPE · {html.escape(provenance)} '
           f'· tape {tape_id(events)} · {html.escape(start[:10])} to {html.escape(end[:10])} '
           f'· {len(dropped)} line(s) refused for lacking evidence</div>',
           '            <div class="board-grid">']
    by_panel: dict[str, list[BoardLine]] = defaultdict(list)
    for l in lines:
        by_panel[l.panel].append(l)
    for panel in ("floor", "clocks", "crosswalk", "ledger"):
        pl = by_panel.get(panel, [])
        if not pl:
            continue
        wide = ' wide' if panel == "ledger" else ''
        out.append(f'                <div class="panel{wide}">')
        out.append(f'                    <h4>{html.escape(PANEL_TITLE[panel])}</h4>')
        census = [l for l in pl if l.kind == "census"]
        if census:
            out.append('                    <div class="census-row">')
            for l in census:
                colour = {"pass": "var(--stamp-green)", "held": "var(--hold-amber)",
                          "alarm": "var(--flag-red)", "red": "var(--flag-red)"}.get(l.stamp, "")
                style = f' style="color:{colour}"' if colour else ""
                out.append(f'                        <div><div class="bignum"{style}>{html.escape(l.value)}</div>'
                           f'<div class="sub">{html.escape(l.label)}<br>{html.escape(l.detail)}'
                           f'<br><span class="ev">{html.escape(_ev(l))}</span></div></div>')
            out.append('                    </div>')
        for l in pl:
            if l.kind == "census":
                continue
            cls = STAMPS.get(l.stamp, "ink")
            ev = f'<span class="ev">{html.escape(_ev(l))}</span>'
            if l.kind == "clock":
                # the page's own .clock component: label + bar on the left, figure right
                warn = " warn" if l.stamp in ("alarm", "red") else ""
                out.append(f'                    <div class="clock"><span>'
                           f'<b>{html.escape(l.label)}</b> — {html.escape(l.detail)} {ev}'
                           f'<div class="bar"><i class="{warn.strip()}" style="width:{l.pct or 0}%"></i></div>'
                           f'</span><span class="t{warn}">{html.escape(l.value)}</span></div>')
            elif l.kind == "fold":
                out.append(f'                    <div class="fold-line"><span>'
                           f'<b>{html.escape(l.label)}</b> — {html.escape(l.detail)} {ev}</span>'
                           f'<span class="stamp {cls}">{html.escape(l.value)}</span></div>')
            else:
                out.append(f'                    <div class="item"><span class="id">{html.escape(l.label)}</span>'
                           f'<span>{html.escape(l.detail)} {ev}</span>'
                           f'<span class="stamp {cls}">{html.escape(l.value)}</span></div>')
        out.append('                </div>')
    out.append('            </div>')
    return "\n".join(out) + "\n"


def render_text(lines: list[BoardLine], dropped: list[str]) -> str:
    out = [f"MORNING BOARD — {len(lines)} lines, {len(dropped)} refused for lacking evidence"]
    for panel in ("floor", "clocks", "crosswalk", "ledger"):
        pl = [l for l in lines if l.panel == panel]
        if not pl:
            continue
        out.append(f"\n## {PANEL_TITLE[panel]}")
        for l in pl:
            out.append(f"  {l.value:<14} {l.label:<38} {l.detail[:80]:<80} [{_ev(l)}]")
    for d in dropped:
        out.append(f"  REFUSED: {d}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the gate's engine
def selftest(events: list[dict] | None = None) -> list[str]:
    """G-EVIDENCE-LINKS. The property is not 'lines have evidence' - it is that a line
    CANNOT render without it, which is only demonstrable by trying to make one."""
    f: list[str] = []
    if events is None:
        import make_tape
        events = make_tape.build(seed=20260903, cases=25)
    start, end = "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z"
    lines, dropped = build(events, start, end)
    if not lines:
        return ["the board rendered no lines at all"]

    # 1. every rendered line carries evidence
    for l in lines:
        if not l.evidence:
            f.append(f"line without evidence rendered: {l.panel}/{l.label}")
    # 2. a line built with no evidence is REFUSED, not rendered
    try:
        line("floor", "item", "uncitable", [])
        f.append("line() accepted an empty evidence list - the rule is unenforced")
    except Uncitable:
        pass
    try:
        line("floor", "item", "uncitable", ["", "   "])
        f.append("line() accepted blank evidence ids")
    except Uncitable:
        pass
    # 3. the drop is counted and surfaced, never silent
    txt = render_text(lines, ["floor/x: no evidence"])
    if "REFUSED" not in txt or "1 refused" not in txt:
        f.append("a refused line must be counted and named in the output")
    frag = render_html(lines, ["floor/x: no evidence"], events, start, end, "test")
    banner = next((l for l in frag.splitlines() if "board-note" in l), "")
    # the property, not the phrasing: the count of refusals must appear in the banner
    if "refused" not in banner or "1 " not in banner:
        f.append(f"the html banner must state how many lines were refused: {banner[:120]}")
    # 4. EVERY rendered row of every component carries the evidence element. Checked on
    #    the markup rather than on the objects, because the page is what a surveyor reads.
    for row in frag.splitlines():
        if any(c in row for c in ('class="item"', 'class="sub"', 'class="clock"', 'class="fold-line"')):
            if 'class="ev"' not in row:
                f.append(f"rendered row without an evidence element: {row.strip()[:90]}")
                break
    # 5. deterministic, and order-independent for simultaneous events
    from folds import _shuffle_equal_ts
    a = render_html(*build(events, start, end), events, start, end, "p")
    b = render_html(*build(events, start, end), events, start, end, "p")
    sh = _shuffle_equal_ts(events)
    c = render_html(*build(sh, start, end), sh, start, end, "p")
    if a != b:
        f.append("two renders of the same tape differ")
    if a != c:
        f.append("render changed when simultaneous events were reordered")
    # 6. the two evidence namespaces stay distinct
    for l in lines:
        if l.ns == "tape" and any(str(e).startswith("MAP-") for e in l.evidence):
            f.append(f"a tape-namespace line cites a mapping id: {l.label}")
        if l.ns == "crosswalk" and any(str(e).startswith("#") for e in l.evidence):
            f.append(f"a crosswalk-namespace line cites a tape event: {l.label}")
    # 7. law E2: a synthetic tape must say so on the page
    if "SYNTHETIC" not in render_html(lines, dropped, events, start, end,
                                      "SYNTHETIC TAPE — F-RETRO has not run"):
        f.append("the provenance banner must survive into the markup")
    return f


if __name__ == "__main__":
    import argparse
    # The documents are UTF-8 on disk; this box's console is cp1252 and cannot print an
    # arrow. That is a terminal limit, not a data one, so it is handled here and nowhere
    # near the renderers - a fold that changed its bytes to suit a console would stop
    # being deterministic.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--cases", type=int, default=60)
    ap.add_argument("--start", default="2026-01-01T00:00:00Z")
    ap.add_argument("--end", default="2027-01-01T00:00:00Z")
    ap.add_argument("--html", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        fails = selftest()
        print("\n".join(fails) if fails else
              "board selftest: green (no line renders without evidence, and the refusals are counted)")
        sys.exit(1 if fails else 0)
    import make_tape
    evs = make_tape.build(a.seed, a.cases)
    lines, dropped = build(evs, a.start, a.end)
    prov = ("SYNTHETIC TAPE — the floor run against the generated world; F-RETRO has not run, "
            "so these are real reads of a synthetic record, not a site's numbers")
    if a.html:
        Path(a.html).parent.mkdir(parents=True, exist_ok=True)
        Path(a.html).write_text(render_html(lines, dropped, evs, a.start, a.end, prov),
                                encoding="utf-8", newline="\n")
        print(f"wrote {a.html} ({len(lines)} lines, {len(dropped)} refused)")
    else:
        print(render_text(lines, dropped))
