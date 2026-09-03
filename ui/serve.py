#!/usr/bin/env python3
"""ui/serve.py - the Morning Board, locally, with every claim clickable.

    python ui/serve.py            then open http://127.0.0.1:8731

WHAT THIS IS. The board that `ledger/board.py` renders into a page is a published
artifact: correct, cited, and dead. This serves the same folds live and makes the
citation a LINK - click the evidence beside a number and you land on the tape events
behind it; click a check id and you get its predicate, the regulatory clause it runs
under (byte-matched to a pinned source), its fixtures, and every verdict it returned on
this tape. "Every line links to its evidence" stops being a footer slogan and becomes
navigation.

WHAT IT IS NOT, AND CANNOT BECOME.

  READ-ONLY. GET is the only method; everything else is refused with 405. There is no
  write path to the tape, the checks, or the record, because the quality record is
  written by people (law A5) and a UI that could write it would be the one thing this
  architecture forbids.

  LOOPBACK ONLY. Bound to 127.0.0.1 explicitly, never 0.0.0.0. This is the zero-egress
  posture of SPEC section 11 held at the socket: a bind address is a policy statement,
  and the default in most tutorials is the wrong one.

  NO EXTERNAL ASSET. No CDN, no font service, no analytics, no script tag pointing
  anywhere. The stylesheet is inline and the fonts are whatever the machine already has.
  An air-gapped workstation renders this identically to a connected one, which is the
  test that matters - the product page loads a font service and this deliberately does
  not.

  NO FILE SERVING. Every response is rendered from objects in memory. There is no
  document root, so there is no path traversal to get wrong.

Stdlib only. `http.server` is imported here and nowhere near the organs: `floor/`,
`clocks/`, `ledger/` and `crosswalk/` are scanned for network imports on every gate run,
and this file sits outside that fence on purpose (law B2).

    python ui/serve.py --selftest    render every route and prove every link resolves
"""
from __future__ import annotations

import html
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
for d in ("floor", "ledger", "crosswalk", "clocks"):
    sys.path.insert(0, str(ROOT / d))
import board as B          # noqa: E402
import engine              # noqa: E402
import folds               # noqa: E402
import make_tape           # noqa: E402
from lifecycle import body, event_id  # noqa: E402

HOST, PORT = "127.0.0.1", 8731
START, END = "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z"
PROVENANCE = "SYNTHETIC TAPE - real reads of a generated record; F-RETRO has not run"

CSS = """
:root{--paper:#faf9f4;--paper-2:#f4f2ea;--ink-950:#0b2239;--ink-900:#0e2a47;--ink-700:#1d446b;
--ink-500:#3d648c;--ink-300:#8aa5bf;--ink-150:#c9d6e2;--ink-075:#e4ebf1;--stamp-green:#15733c;
--stamp-green-bg:#eaf5ee;--flag-red:#b3261e;--flag-red-bg:#fbeeed;--hold-amber:#955104;
--hold-amber-bg:#fdf3e4;--mono:'Consolas','JetBrains Mono',ui-monospace,monospace;
--sans:-apple-system,'Segoe UI',system-ui,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink-900);font-family:var(--sans);line-height:1.65;font-size:15px}
a{color:var(--ink-700)}
header{background:var(--ink-950);color:#d9e4ee;padding:.7rem 1.2rem;font-family:var(--mono);
font-size:.72rem;letter-spacing:.05em;display:flex;gap:1rem;align-items:center;flex-wrap:wrap;
position:sticky;top:0;z-index:9}
header a{color:#9fc0dd;text-decoration:none;margin-right:.9rem}
header a:hover{color:#fff;text-decoration:underline}
header .t{font-weight:700;letter-spacing:.12em;margin-right:.6rem}
header .sp{flex:1}
.note{background:#fff8e8;color:#7a5a12;border-bottom:1px solid #eadfbe;font-family:var(--mono);
font-size:.66rem;letter-spacing:.05em;padding:.5rem 1.2rem;text-transform:uppercase}
main{max-width:1180px;margin:0 auto;padding:1.2rem}
h1{font-size:1.35rem;margin:.4rem 0 1rem}
h2{font-size:.72rem;font-family:var(--mono);letter-spacing:.16em;text-transform:uppercase;
color:var(--ink-500);margin:1.6rem 0 .6rem;border-bottom:1px solid var(--ink-075);padding-bottom:.35rem}
.grid{display:grid;grid-template-columns:1.35fr 1fr 1fr;gap:1px;background:var(--ink-075);
border:1px solid var(--ink-150)}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.panel{background:#fff;padding:1rem 1.1rem}
.panel.wide{grid-column:1/-1}
.big{font-family:var(--mono);font-weight:700;font-size:1.9rem;line-height:1}
.sub{font-family:var(--mono);font-size:.68rem;color:var(--ink-500);margin-top:.2rem}
.census{display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:.8rem}
.row{display:grid;grid-template-columns:auto 1fr auto;gap:.7rem;align-items:baseline;
padding:.5rem 0;border-top:1px dashed var(--ink-150);font-size:.86rem}
.row .id{font-family:var(--mono);font-size:.7rem;color:var(--ink-300)}
.flex{display:flex;justify-content:space-between;gap:.8rem;align-items:center;
padding:.45rem 0;border-top:1px dashed var(--ink-150);font-size:.86rem}
.bar{height:6px;background:var(--ink-075);border-radius:4px;overflow:hidden;margin-top:4px}
.bar i{display:block;height:100%;background:var(--stamp-green)}
.bar i.warn{background:var(--hold-amber)}
.stamp{font-family:var(--mono);font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;
padding:.15rem .45rem;border:1px solid var(--ink-150);border-radius:2px;white-space:nowrap}
.stamp.pass{color:var(--stamp-green);border-color:var(--stamp-green);background:var(--stamp-green-bg)}
.stamp.held{color:var(--hold-amber);border-color:var(--hold-amber);background:var(--hold-amber-bg)}
.stamp.red{color:var(--flag-red);border-color:var(--flag-red);background:var(--flag-red-bg)}
.ev{font-family:var(--mono);font-size:.6rem;color:var(--ink-300);display:block;margin-top:3px;
overflow-wrap:anywhere}
.ev a{color:var(--ink-500);text-decoration:none;border-bottom:1px dotted var(--ink-300)}
.ev a:hover{color:var(--ink-950);background:#fff8e8}
table{border-collapse:collapse;width:100%;font-size:.84rem;margin:.5rem 0}
th,td{border:1px solid var(--ink-150);padding:.35rem .5rem;text-align:left;vertical-align:top}
th{background:var(--paper-2);font-family:var(--mono);font-size:.66rem;letter-spacing:.06em;
text-transform:uppercase;color:var(--ink-500)}
pre{background:var(--paper-2);border:1px solid var(--ink-150);padding:.7rem;overflow-x:auto;
font-family:var(--mono);font-size:.76rem;white-space:pre-wrap;overflow-wrap:anywhere}
code{font-family:var(--mono);font-size:.82em;background:var(--paper-2);padding:.05rem .25rem}
blockquote{margin:.6rem 0;padding:.5rem .9rem;border-left:3px solid var(--ink-150);
background:var(--paper-2);font-size:.88rem}
footer{font-family:var(--mono);font-size:.64rem;color:var(--ink-500);padding:1.2rem;
border-top:1px solid var(--ink-075);margin-top:2rem;letter-spacing:.05em}
"""


# ---------------------------------------------------------------- state
class World:
    """Everything the app renders, built once. Rebuilt only when asked, because a page
    whose numbers change between two reads of the same tape is not a fold."""

    def __init__(self, cases: int = 60) -> None:
        self.events = make_tape.build(seed=20260903, cases=cases)
        self.by_i = {int(e["i"]): e for e in self.events if e.get("i") is not None}
        self.checks = {p.name.split(".")[0]: engine.load_check_yml(p)
                       for p in sorted((ROOT / "floor" / "checks").glob("SV-*.check.yml"))}
        self.authorities = folds.load_authorities()
        self.lines, self.dropped = B.build(self.events, START, END)
        self.tape = folds.tape_id(self.events)
        # one pass over the tape, not one per page render
        self.results_by_check: dict[str, list[dict]] = {}
        for ev in self.events:
            if ev.get("kind") == "check_result":
                self.results_by_check.setdefault(str(body(ev).get("check")), []).append(ev)
        self._mappings: list[dict] | None = None
        self._page_cache: dict[str, tuple[int, str]] = {}
        self.docs = {
            "line-of-sight": lambda: folds.line_of_sight(self.events, START, END),
            "committee-packet": lambda: folds.committee_packet(self.events, START, END),
            "survey-binder": lambda: folds.survey_binder(self.events, START, END, self.authorities),
        }


W: World | None = None


def world() -> World:
    global W
    if W is None:
        W = World()
    return W


# ---------------------------------------------------------------- html helpers
def e(s) -> str:
    return html.escape(str(s), quote=True)


def page(title: str, body_html: str, crumb: str = "") -> str:
    w = world()
    nav = ('<a href="/">Board</a><a href="/doc/line-of-sight">Line of sight</a>'
           '<a href="/doc/committee-packet">Committee packet</a>'
           '<a href="/doc/survey-binder">Survey binder</a>'
           '<a href="/checks">Checks</a><a href="/gates">Gates</a><a href="/about">About</a>')
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{e(title)} - SURVEYOR</title><style>{CSS}</style></head><body>"
            f"<header><span class=t>SURVEYOR</span>{nav}<span class=sp></span>"
            f"<span>tape {w.tape}</span></header>"
            f"<div class=note>{e(PROVENANCE)} &middot; {e(START[:10])} to {e(END[:10])} "
            f"&middot; read-only &middot; 127.0.0.1 only &middot; no external asset</div>"
            f"<main>{crumb}{body_html}</main>"
            f"<footer>EVERY LINE LINKS TO ITS EVIDENCE &middot; EVERY SILENCE IS ON THE RECORD "
            f"&middot; LOCAL ONLY &middot; APPEND-ONLY, HASH-CHAINED &middot; "
            f"GREEN MOUNTS NOTHING: A HUMAN SIGNATURE IS THE ONLY WAY ACROSS</footer></body></html>")


def ev_links(l) -> str:
    """The evidence handles, as links. This is the whole point of the app."""
    out = []
    for h in l.evidence[: 3 if l.ns == "tape" else 2]:
        if l.ns == "tape" and h.startswith("#"):
            out.append(f'<a href="/event/{e(h[1:])}">{e(h)}</a>')
        elif l.ns == "crosswalk":
            out.append(f'<a href="/mapping/{e(h)}">{e(h)}</a>')
        else:
            out.append(e(h))
    more = len(l.evidence) - len(out)
    tag = "tape" if l.ns == "tape" else "pin"
    tail = f' <a href="/evidence/{e(l.panel)}/{e(l.label)}">+{more} more</a>' if more > 0 else ""
    return f'<span class=ev>{tag} ' + ", ".join(out) + tail + "</span>"


def check_link(text: str) -> str:
    """Turn every SV-xxx mentioned in a string into a link to that check."""
    return re.sub(r"\b(SV-\d{3})\b", lambda m: f'<a href="/check/{m.group(1)}">{m.group(1)}</a>', text)


# ---------------------------------------------------------------- views
def view_board() -> str:
    w = world()
    titles = {"floor": "The Floor - census, at entry", "clocks": "Clocks - the SLA lattice",
              "crosswalk": "Crosswalk - regulation to your policy",
              "ledger": "Corrective actions - variance intake - the ledger"}
    out = [f"<h1>Morning Board</h1>", "<div class=grid>"]
    for panel in ("floor", "clocks", "crosswalk", "ledger"):
        pl = [l for l in w.lines if l.panel == panel]
        if not pl:
            continue
        out.append(f"<div class='panel{' wide' if panel == 'ledger' else ''}'><h2>{e(titles[panel])}</h2>")
        census = [l for l in pl if l.kind == "census"]
        if census:
            out.append("<div class=census>")
            for l in census:
                col = {"pass": "var(--stamp-green)", "held": "var(--hold-amber)",
                       "alarm": "var(--flag-red)", "red": "var(--flag-red)"}.get(l.stamp, "")
                st = f" style='color:{col}'" if col else ""
                out.append(f"<div><div class=big{st}>{e(l.value)}</div>"
                           f"<div class=sub>{check_link(e(l.label))}<br>{check_link(e(l.detail))}"
                           f"{ev_links(l)}</div></div>")
            out.append("</div>")
        for l in pl:
            if l.kind == "census":
                continue
            cls = B.STAMPS.get(l.stamp, "ink")
            if l.kind == "clock":
                warn = " warn" if l.stamp in ("alarm", "red") else ""
                out.append(f"<div class=flex><span style='flex:1'><b>{check_link(e(l.label))}</b> - "
                           f"{e(l.detail)}{ev_links(l)}"
                           f"<div class=bar><i class='{warn.strip()}' style='width:{l.pct or 0}%'></i></div>"
                           f"</span><span class='stamp {cls}'>{e(l.value)}</span></div>")
            elif l.kind == "fold":
                out.append(f"<div class=flex><span><b>{check_link(e(l.label))}</b> - "
                           f"{check_link(e(l.detail))}{ev_links(l)}</span>"
                           f"<span class='stamp {cls}'>{e(l.value)}</span></div>")
            else:
                out.append(f"<div class=row><span class=id>{e(l.label)}</span>"
                           f"<span>{check_link(e(l.detail))}{ev_links(l)}</span>"
                           f"<span class='stamp {cls}'>{e(l.value)}</span></div>")
        out.append("</div>")
    out.append("</div>")
    out.append(f"<p class=sub>{len(w.lines)} lines, every one carrying its evidence. "
               f"{len(w.dropped)} refused for lacking it - a line that cannot cite itself does not render.</p>")
    return "".join(out)


def view_event(i: str) -> str | None:
    w = world()
    try:
        ev = w.by_i[int(i)]
    except (ValueError, KeyError):
        return None
    b = body(ev)
    citing = [l for l in w.lines if f"#{i}" in l.evidence]
    rows = "".join(f"<tr><th>{e(k)}</th><td>{check_link(e(json.dumps(v) if isinstance(v, (dict, list)) else v))}</td></tr>"
                   for k, v in sorted(b.items()))
    cite_html = "".join(f"<li>{e(l.panel)} / {check_link(e(l.label))} - {e(l.value)}</li>" for l in citing)
    return page(f"event #{i}", (
        f"<h1>Tape event #{e(i)}</h1>"
        f"<p class=sub>kind <b>{e(ev.get('kind'))}</b> &middot; {e(ev.get('ts'))}</p>"
        f"<table>{rows}</table>"
        f"<h2>Board lines that cite this event</h2>"
        + (f"<ul>{cite_html}</ul>" if citing else
           "<p>None directly - this event is inside a larger citation. Every claim names at "
           "most a few handles and then a count, so that a page stays readable while remaining "
           "falsifiable.</p>")),
        '<p class=sub><a href="/">&larr; board</a></p>')


def view_check(cid: str) -> str | None:
    w = world()
    c = w.checks.get(cid)
    if not c:
        return None
    verdicts: dict[str, int] = {}
    cases: list[tuple[str, str]] = []
    for ev in w.results_by_check.get(cid, []):
        b = body(ev)
        v = str(b.get("verdict"))
        verdicts[v] = verdicts.get(v, 0) + 1
        # ACTED ON means the check returned its action. An abstention is not an action -
        # listing CANNOT-EVALUATE here would put every register and referral in a table
        # headed "cases it acted on", which is precisely the kind of imprecise label this
        # project exists to remove.
        if v not in ("PASS", "CANNOT-EVALUATE") and len(cases) < 12:
            cases.append((str(b.get("case")), f"#{ev['i']}"))
    maps = w.authorities.get(cid, [])
    auth_rows = "".join(
        f"<tr><td><a href='/mapping/{e(m.get('id'))}'>{e(m.get('locator'))}</a></td>"
        f"<td>{e(m.get('type'))}</td><td>{e(m.get('source'))}</td>"
        f"<td>{e(str(m.get('quote') or '(asserts silence; search terms recorded)')[:180])}</td></tr>"
        for m in maps)
    vrows = "".join(f"<tr><td>{e(k)}</td><td>{v:,}</td></tr>" for k, v in sorted(verdicts.items()))
    crows = "".join(f"<tr><td>{e(a)}</td><td><a href='/event/{e(b_[1:])}'>{e(b_)}</a></td></tr>"
                    for a, b_ in cases)
    fdir = ROOT / "floor" / "fixtures" / cid
    fx = "".join(f"<li><code>{e(p.name)}</code> - {e(json.loads(p.read_text(encoding='utf-8')).get('note', ''))}</li>"
                 for p in sorted(fdir.glob("*.json"))) if fdir.exists() else ""
    return page(cid, (
        f"<h1>{e(cid)} &mdash; {e(c.get('title'))}</h1>"
        f"<p class=sub>layer <b>{e(c.get('layer'))}</b> &middot; trigger {e(c.get('trigger'))} "
        f"&middot; action {e(c.get('action'))} &middot; expires {e(c.get('expires'))} "
        f"&middot; inverse {e(c.get('inverse'))}</p>"
        f"<h2>Predicate</h2><pre>{e(c.get('predicate'))}</pre>"
        + (f"<h2>Anchor</h2><p><code>{e(c.get('anchor'))}</code></p>"
           f"<blockquote>{e(c.get('anchor_why'))}</blockquote>" if c.get("anchor") else "")
        + f"<h2>Authority</h2><p>{e(c.get('authority'))}</p>"
        + (f"<table><tr><th>clause</th><th>type</th><th>source</th><th>quote (byte-matched)</th></tr>"
           f"{auth_rows}</table>" if maps else
           "<p>Not pinned. The survey binder prints 'not pinned' for this check rather than a "
           "paraphrase, and the crosswalk coverage fold says why.</p>")
        + f"<h2>Verdicts on this tape</h2><table><tr><th>verdict</th><th>count</th></tr>{vrows}</table>"
        + (f"<h2>Cases it acted on</h2><p class=sub>the check returned its action here; abstentions are counted above and are not actions</p><table><tr><th>case</th><th>event</th></tr>{crows}</table>" if crows else "<h2>Cases it acted on</h2><p>None on this tape. It passed or abstained everywhere.</p>")
        + (f"<h2>Fixtures</h2><ul>{fx}</ul>" if fx else "")),
        '<p class=sub><a href="/checks">&larr; all checks</a></p>')


def view_checks() -> str:
    w = world()
    rows = []
    for cid in sorted(w.checks):
        c = w.checks[cid]
        n = len(w.authorities.get(cid, []))
        rows.append(f"<tr><td><a href='/check/{e(cid)}'>{e(cid)}</a></td><td>{e(c.get('title'))}</td>"
                    f"<td>{e(c.get('layer'))}</td><td>{e(c.get('action'))}</td>"
                    f"<td>{'yes, ' + str(n) if n else '<b>not pinned</b>'}</td></tr>")
    return page("checks", f"<h1>The floor &mdash; {len(w.checks)} checks</h1><table>"
                f"<tr><th>id</th><th>title</th><th>layer</th><th>action</th><th>authority pinned</th></tr>"
                + "".join(rows) + "</table>")


def view_mapping(mid: str) -> str | None:
    sys.path.insert(0, str(ROOT / "crosswalk"))
    import pins
    w = world()
    if w._mappings is None:
        w._mappings = pins.load_mappings()
    m = next((x for x in w._mappings if str(x.get("id")) == mid), None)
    if not m:
        return None
    status, detail = pins.verify(m, pins.load_sources())
    rows = "".join(f"<tr><th>{e(k)}</th><td>{check_link(e(v))}</td></tr>"
                   for k, v in sorted(m.items()) if not k.startswith("_"))
    return page(mid, (
        f"<h1>{e(mid)}</h1>"
        f"<p class=sub>verification: <b>{e(status)}</b> &mdash; {e(detail)}</p>"
        f"<table>{rows}</table>"
        f"<blockquote>A quote that does not byte-match its sha256-pinned source does not exist. "
        f"A mapping that asserts the regulation is <i>silent</i> has every one of its search terms "
        f"run by the tool, and one hit rejects it.</blockquote>"),
        '<p class=sub><a href="/">&larr; board</a></p>')


def view_evidence(panel: str, label: str) -> str | None:
    w = world()
    l = next((x for x in w.lines if x.panel == panel and x.label == label), None)
    if not l:
        return None
    items = []
    for h in l.evidence:
        if l.ns == "tape" and h.startswith("#"):
            ev = w.by_i.get(int(h[1:]))
            k = ev.get("kind") if ev else "?"
            items.append(f"<tr><td><a href='/event/{e(h[1:])}'>{e(h)}</a></td><td>{e(k)}</td>"
                         f"<td>{e(ev.get('ts') if ev else '')}</td></tr>")
        else:
            items.append(f"<tr><td><a href='/mapping/{e(h)}'>{e(h)}</a></td><td>mapping</td><td></td></tr>")
    return page("evidence", (
        f"<h1>Evidence behind one line</h1>"
        f"<p class=sub>{e(panel)} / {e(label)} &mdash; {e(l.value)} &mdash; {e(l.detail)}</p>"
        f"<p>{len(l.evidence):,} handles. The board shows the first few and a count; this is all of them.</p>"
        f"<table><tr><th>handle</th><th>kind</th><th>when</th></tr>{''.join(items[:400])}</table>"
        + (f"<p class=sub>showing the first 400 of {len(items):,}.</p>" if len(items) > 400 else "")),
        '<p class=sub><a href="/">&larr; board</a></p>')


def md_to_html(md: str) -> str:
    """Enough markdown for the folds: headings, tables, bold, code, italics, lists."""
    out, in_tbl = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: ") and cells:
                continue
            tag = "th" if not in_tbl else "td"
            if not in_tbl:
                out.append("<table>")
                in_tbl = True
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            continue
        if in_tbl:
            out.append("</table>")
            in_tbl = False
        if line.startswith("# "):
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            out.append(f"<p>&bull; {line[2:]}</p>")
        elif not line:
            out.append("")
        else:
            out.append(f"<p>{line}</p>")
    if in_tbl:
        out.append("</table>")
    s = "\n".join(out)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", s)
    return s


def view_doc(name: str) -> str | None:
    w = world()
    fn = w.docs.get(name)
    if not fn:
        return None
    md = fn()
    # the folds cite `#123`; make those links, then the check ids
    body_html = md_to_html(e(md).replace("&quot;", '"'))
    body_html = re.sub(r"#(\d+)", lambda m: f'<a href="/event/{m.group(1)}">#{m.group(1)}</a>', body_html)
    return page(name, check_link(body_html), '<p class=sub><a href="/">&larr; board</a></p>')


def view_gates() -> str:
    """The build's own gate verdicts, from its tape. The app reports the same numbers the
    gates recorded rather than recomputing them, so a stale app is visible as a stale tape."""
    verdicts: dict[str, dict] = {}
    for line in (ROOT / "_build" / "TAPE.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("type") == "verdict":
            verdicts[d.get("gate", "?")] = d
    rows = "".join(
        f"<tr><td><b>{e(g)}</b></td><td><span class='stamp "
        f"{'pass' if v['status'] == 'PASS' else ('red' if v['status'] == 'FAIL' else 'held')}'>"
        f"{e(v['status'])}</span></td><td>{e(v['ts'])}</td><td>{check_link(e(v.get('detail', '')))}</td></tr>"
        for g, v in sorted(verdicts.items()))
    return page("gates", f"<h1>Gates &mdash; the build's own floor</h1>"
                f"<table><tr><th>gate</th><th>verdict</th><th>as of</th><th>detail</th></tr>{rows}</table>"
                f"<blockquote>Three-state honesty: every gate reports PASS, FAIL or CANNOT-EVALUATE, "
                f"never silence. These are read from the build tape, not recomputed here.</blockquote>")


def view_about() -> str:
    w = world()
    return page("about", (
        "<h1>What this is</h1>"
        "<p>The Morning Board, served locally from a tape, with every claim clickable. Click the "
        "small grey handles beside a number to reach the events behind it; click a check id for its "
        "predicate, its pinned regulatory clause, its fixtures and every verdict it returned.</p>"
        "<h2>What it cannot do</h2>"
        "<p>&bull; <b>Write.</b> GET only; everything else is refused. The quality record is written "
        "by people, and there is no code path here that could touch it.</p>"
        "<p>&bull; <b>Leave this machine.</b> Bound to 127.0.0.1, never 0.0.0.0. No CDN, no font "
        "service, no analytics, no outbound request of any kind. An air-gapped workstation renders "
        "this identically.</p>"
        "<p>&bull; <b>Serve a file.</b> Every response is rendered from memory; there is no document "
        "root, so there is no path traversal to get wrong.</p>"
        "<h2>The numbers</h2>"
        f"<p>Tape <code>{e(w.tape)}</code>, {len(w.events):,} events, {len(w.checks)} encoded checks. "
        "<b>The tape is synthetic</b>: the floor run against a generated world. They are real reads of "
        "a real tape and they are not a site's numbers, and they will not be until F-RETRO runs on a "
        "programme's historical charts.</p>"))


# ---------------------------------------------------------------- routing
def route(path: str) -> tuple[int, str]:
    p = unquote(path.split("?", 1)[0]).rstrip("/") or "/"
    cached = world()._page_cache.get(p)
    if cached is not None:
        return cached
    code, text = _route(p)
    if len(world()._page_cache) < 3000:
        world()._page_cache[p] = (code, text)
    return code, text


def _route(p: str) -> tuple[int, str]:
    if p == "/":
        return 200, page("board", view_board())
    if p == "/checks":
        return 200, view_checks()
    if p == "/gates":
        return 200, view_gates()
    if p == "/about":
        return 200, view_about()
    for prefix, fn in (("/event/", view_event), ("/check/", view_check),
                       ("/mapping/", view_mapping), ("/doc/", view_doc)):
        if p.startswith(prefix):
            got = fn(p[len(prefix):])
            if got:
                return 200, got
            return 404, page("not found", f"<h1>Not found</h1><p>No such {e(prefix.strip('/'))}: "
                                          f"<code>{e(p[len(prefix):])}</code></p>")
    if p.startswith("/evidence/"):
        parts = p[len("/evidence/"):].split("/", 1)
        got = view_evidence(parts[0], parts[1]) if len(parts) == 2 else None
        if got:
            return 200, got
    return 404, page("not found", f"<h1>Not found</h1><p><code>{e(p)}</code></p>")


class Handler(BaseHTTPRequestHandler):
    server_version = "SURVEYOR-local"

    def _send(self, code: int, text: str) -> None:
        blob = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        # nothing on this page may reach off this machine, and the header says so too
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; form-action 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(blob)

    def do_GET(self) -> None:  # noqa: N802
        try:
            code, text = route(self.path)
        except Exception as ex:  # noqa: BLE001
            code, text = 500, page("error", f"<h1>Error</h1><pre>{e(type(ex).__name__)}: {e(ex)}</pre>")
        self._send(code, text)

    def _refuse(self) -> None:
        self._send(405, page("read-only", "<h1>Read-only</h1><p>This application has no write path. "
                                          "The quality record is written by people, under their own "
                                          "names, and a user interface that could write it is the one "
                                          "thing this architecture forbids.</p>"))

    do_POST = do_PUT = do_DELETE = do_PATCH = _refuse

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("  %s\n" % (fmt % args))


# ---------------------------------------------------------------- selftest
def selftest() -> list[str]:
    """Render every route and prove EVERY internal link resolves. A board whose evidence
    handles are links is only better than one whose handles are text if the links go
    somewhere - a dead citation is worse than a printed one, because it looks checkable."""
    f: list[str] = []
    global W
    W = World(cases=12)          # a smaller tape: this proves the wiring, not the numbers
    w = world()
    pages = {"/": route("/")[1], "/checks": route("/checks")[1], "/gates": route("/gates")[1],
             "/about": route("/about")[1]}
    for name in w.docs:
        pages[f"/doc/{name}"] = route(f"/doc/{name}")[1]
    links: set[str] = set()
    for src, body_html in pages.items():
        for m in re.finditer(r'href="(/[^"#]*)"', body_html):
            links.add(m.group(1))
    if not any(l.startswith("/event/") for l in links):
        f.append("the board carries no event links - the evidence is not clickable")
    if not any(l.startswith("/check/") for l in links):
        f.append("no check links - a check id on the board must reach its definition")
    for l in sorted(links):
        code, _ = route(l)
        if code != 200:
            f.append(f"dead link {l} -> {code}")
    # follow one level deeper from the board's own links
    deep = sorted(x for x in links if x.startswith(("/event/", "/check/", "/mapping/", "/evidence/")))
    for l in deep[:24]:          # bounded: one level deep on a sample, not the transitive closure
        code, html_ = route(l)
        if code != 200:
            continue
        for m in re.finditer(r'href="(/[^"#]*)"', html_):
            c2, _ = route(m.group(1))
            if c2 != 200:
                f.append(f"dead link {m.group(1)} (from {l}) -> {c2}")
                break
    # a page that reached the network would defeat the whole posture
    joined = "".join(pages.values())
    for bad in ("http://", "https://", "//fonts.", "<script"):
        if bad in joined:
            f.append(f"page references {bad!r} - this app must not reach off the machine")
    # read-only
    if not hasattr(Handler, "do_POST") or Handler.do_POST is not Handler._refuse:
        f.append("POST is not refused")
    if any(hasattr(Handler, m) and getattr(Handler, m) is not Handler._refuse
           for m in ("do_PUT", "do_DELETE", "do_PATCH")):
        f.append("a write method is not refused")
    return f


def main() -> int:
    if "--selftest" in sys.argv:
        fails = selftest()
        print("\n".join(fails) if fails else
              "ui selftest: green (every rendered link resolves; read-only; no external reference)")
        return 1 if fails else 0
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT
    w = world()
    srv = ThreadingHTTPServer((HOST, port), Handler)
    print(f"SURVEYOR - local\n"
          f"  http://{HOST}:{port}\n"
          f"  tape {w.tape} - {len(w.events):,} events, {len(w.lines)} board lines, "
          f"{len(w.checks)} checks\n"
          f"  read-only, loopback only, no external asset. Ctrl-C to stop.\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
