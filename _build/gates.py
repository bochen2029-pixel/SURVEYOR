#!/usr/bin/env python3
"""gates.py - the build's own floor: deterministic gates on the repo itself.

Three-state honesty: every gate reports PASS, FAIL, or CANNOT-EVALUATE.
Exit code 1 if any gate FAILs, or if G-PRIVACY cannot evaluate (fail closed).

Usage:
  python _build/gates.py            # run gates, print table
  python _build/gates.py --record   # also append verdict events to the tape,
                                    # then regenerate the folds

Gates:
  G-FOLD              folds on disk match a fresh deterministic render of the tape
  G-PRIVACY           no denylisted term (from _local/denylist.txt) outside _local/
  G-CATALOG           every SV- check is either honestly UNENCODED or fully encoded
                      (check.yml + at least one pass* and one fail* fixture)
  F-FIXTURE           rung 01's executioner: the floor engine's DSL selftest + full
                      fixture battery + ledger selftest + no-model scan
  G-CATALOG-COMPLETE  rung 02's executioner: PASS only when every catalog check is encoded
  G-FIELDS            floor/FIELDS.md (the record vocabulary) matches a fresh fold of
                      the fixtures (law A1 applied to the vocabulary; added S2)
  G-ANCHOR-PLANTS     rung 03's executioner: every clock check declares an anchor the
                      predicate reads, every anchor-defect plant flips its verdict on
                      the wrong anchor, and the ported closure battery is green (law B1)
  F-FIXTURE-WORLD     SPEC section 12's decider, mechanised: the floor against the
                      synthetic OPO world at a pinned seed - dies if any planted defect
                      PASSes, or if the clean-record false-hold rate exceeds 1%
  G-CROSSWALK-PINS    rung 05's executioner: every crosswalk mapping's quote byte-matches
                      its sha256-pinned source, and the edition-diff fixture puts exactly
                      the mappings it should into the review queue (law B6). Fails closed:
                      a source absent on this machine is never a pass
  G-FOLD-DETERMINISM  rung 06's executioner: the same tape renders byte-identical documents,
                      a tape whose simultaneous events are reordered renders the SAME bytes,
                      every table data row carries an evidence handle, and the CAPA/variance
                      engines pass their own battery
  G-EVIDENCE-LINKS    rung 07's executioner: the Morning Board renders from the tape, a line
                      with no evidence CANNOT be built, refusals are counted on the page, and
                      the board published on site/surveyor.html is the one this tape produces
  G-FOREIGN-HARNESS   rung 09's executioner: the completion kit holds - conformance/run.py is
                      green, every refused draft is refused for the reason it declares, every
                      site-variant check has an elicit question, and the boot contract exists
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
FIELDS_MD = ROOT / "floor" / "FIELDS.md"

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


def _engine():
    sys.path.insert(0, str(ROOT / "floor"))
    import engine  # noqa: WPS433
    return engine


def gate_fixture():
    """Rung 01's executioner: the DSL selftest (known-good and known-bad predicates),
    the floor engine's full fixture battery, the ledger selftest, and the no-model
    scan. ImportError degrades to CANNOT-EVALUATE (the estate's pattern), everything
    else is graded."""
    try:
        engine = _engine()
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"floor engine unavailable: {e}"
    dsl_fails = engine.selftest() if hasattr(engine, "selftest") else []
    r = engine.run_battery()
    try:
        sys.path.insert(0, str(ROOT / "ledger"))
        import tape as product_tape
        ledger_fails = product_tape.selftest()
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"ledger unavailable: {e}"
    problems = ([f"DSL selftest: {f}" for f in dsl_fails] + list(r["broken"])
                + r["no_model_violations"] + ledger_fails)
    if problems:
        return "FAIL", "; ".join(problems[:4])
    hatches = r.get("hatches", [])
    return "PASS", (f"{r['encoded']} check(s) fully encoded, {r['fixtures_run']} fixtures "
                    f"green, DSL selftest green, {len(hatches)} impl hatch(es), ledger selftest "
                    f"green (append/verify/tamper/torn-tail), no-model clean")


def gate_catalog_complete():
    """Rung 02's executioner: PASS only when every catalog check is encoded."""
    status, detail = gate_catalog()
    if status != "PASS":
        return status, detail
    m = re.match(r"(\d+)/(\d+) encoded", detail)
    if m and m.group(1) == m.group(2):
        return "PASS", detail
    return "CANNOT-EVALUATE", f"in progress - {detail}"


def gate_fields():
    """floor/FIELDS.md is a fold over the fixtures (law A1): regenerate and compare."""
    try:
        engine = _engine()
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"floor engine unavailable: {e}"
    if not hasattr(engine, "fields_markdown"):
        return "CANNOT-EVALUATE", "engine has no fields fold"
    want = engine.fields_markdown()
    if not FIELDS_MD.exists():
        return "FAIL", "floor/FIELDS.md missing - run: python floor/engine.py --fields --write"
    have = FIELDS_MD.read_text(encoding="utf-8")
    if want == have:
        m = re.search(r"leaf paths: (\d+)", want)
        return "PASS", f"FIELDS.md matches the fixtures ({m.group(1) if m else '?'} leaf paths)"
    return "FAIL", "floor/FIELDS.md stale or hand-edited - run: python floor/engine.py --fields --write"


def gate_anchor_plants():
    """Rung 03's executioner (law B1 made mechanical): the anchor registry is complete,
    every anchor-defect plant flips on the wrong anchor, the closure battery is green."""
    import contextlib
    import io
    try:
        sys.path.insert(0, str(ROOT / "clocks"))
        import anchors
        import test_closure
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"clocks unavailable: {e}"
    g = anchors.grade_plants()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = test_closure.run()
    problems = list(g["broken"])
    if rc:
        problems.append(f"closure battery: {len(test_closure.FAIL)} failed")
    if hasattr(anchors, "selftest"):
        problems += [f"clocks selftest: {f}" for f in anchors.selftest()]
    if problems:
        return "FAIL", "; ".join(problems[:4])
    if not g["plants"]:
        return "CANNOT-EVALUATE", "registry present but no anchor-defect plants yet"
    return "PASS", (f"{g['registry']} anchored checks; {len(g['plants'])} anchor plants across "
                    f"{g['checks_with_plants']} checks all flip on the wrong anchor; closure battery "
                    f"{len(test_closure.PASS)} green")


# The pinned run: the numbers that publish. Changing these changes the receipt, so a
# change needs a tape decision saying why (the seed is arbitrary; the sizes are not).
WORLD_SEED, WORLD_CASES, WORLD_PLANTS = 20260903, 200, 5


def gate_fixture_world():
    """SPEC section 12's F-FIXTURE, mechanised now that the synthetic world exists.
    The hand-written battery (F-FIXTURE above) grades the checks against fixtures written
    FOR them; this grades them against a world that was authored without looking at them.
    That difference is the point: it found two live defects on its first run."""
    try:
        sys.path.insert(0, str(ROOT / "experiments" / "f-fixture"))
        import run as world
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"f-fixture harness unavailable: {e}"
    try:
        res = world.grade(WORLD_SEED, WORLD_CASES, WORLD_PLANTS)
    except AssertionError as e:            # the generator's own plant invariant
        return "FAIL", f"generator defect (instrument, not floor): {e}"
    if res["kill"]:
        return "FAIL", "; ".join(res["kill"])
    return "PASS", (f"{res['caught']}/{res['plants']} plants caught, 0 missed, "
                    f"{len(res['false_holds'])} false holds in {res['clean_pairs']} clean pairs "
                    f"({res['false_hold_rate']:.2%}), {len(res['collateral'])} collateral, "
                    f"seed {res['seed']} cases {res['n_cases']} k {res['k_plants']}")


def gate_crosswalk_pins():
    """Rung 05's executioner (law B6: a quote that does not byte-match does not exist).
    Three things at once: every mapping verifies against its pinned source; the edition
    diff moves exactly the mappings the fixture says it should; and a source that is
    absent on this machine is reported as unverifiable rather than passed."""
    try:
        sys.path.insert(0, str(ROOT / "crosswalk"))
        import pins
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"crosswalk unavailable: {e}"
    if not (ROOT / "crosswalk" / "mappings").exists():
        return "CANNOT-EVALUATE", "no mappings yet"
    res = pins.check_all()
    if res["mappings"] == 0:
        return "CANNOT-EVALUATE", "no mappings yet"
    if res["bad"]:
        bad = [r for r in res["rows"] if r["status"] not in (pins.OK, pins.WARN)][:3]
        return "FAIL", "; ".join(f"{r['check']} {r['locator']}: {r['detail']}" for r in bad)
    if res["unavailable"]:
        return "CANNOT-EVALUATE", (f"{res['unavailable']} of {res['mappings']} mappings could not be "
                                   f"checked - the pinned corpus is not on this machine "
                                   f"(set $SURVEYOR_CORPUS); an unchecked quote is never a pass")
    # the edition-diff fixture
    import engine as _e  # noqa: F401  (floor's flat-yaml reader, already on the path)
    exp_path = ROOT / "crosswalk" / "editions" / "optn-next-draft.expect.yml"
    if exp_path.exists():
        exp = _e.load_check_yml(exp_path)
        d = pins.diff_edition(str(exp["base"]), str(exp["edits"]))
        if "error" in d:
            return "FAIL", f"edition fixture: {d['error']}"
        want = sorted(exp.get("expect_review", []))
        got = sorted(d["checks_to_review"])
        if got != want:
            return "FAIL", f"edition fixture: review queue {got}, fixture says {want}"
        floor_intact = int(exp.get("expect_intact_min", 0))
        if len(d["intact"]) < floor_intact:
            return "FAIL", (f"edition fixture: only {len(d['intact'])} mappings survive the edition "
                            f"unchanged, fixture requires at least {floor_intact} - a diff that flags "
                            f"everything is as useless as one that flags nothing")
    cov = pins.coverage()
    return "PASS", (f"{res['mappings']} mappings byte-match their pinned sources "
                    f"({res['warned']} currency warning(s)); edition-diff fixture green; "
                    f"{cov['mapped']}/{cov['checks']} checks mapped, "
                    f"{cov['named_but_unmapped']} nameable but unmapped, "
                    f"{cov['authority_outside_corpus']} rest on authority outside the corpus")


def gate_fold_determinism():
    """Rung 06's executioner. Four properties at once, because a generated document is
    only evidence if it can be re-derived: (1) the CAPA lifecycle and variance triage pass
    their battery; (2) the same tape renders byte-identical documents; (3) a tape whose
    SIMULTANEOUS events arrived in a different order renders the same bytes, so the
    document is not counting arrival order; (4) every table data row carries an evidence
    handle, so no number reaches a page without its source (law A6). Also writes the tape
    through the real hash-chained ledger and verifies the chain."""
    try:
        sys.path.insert(0, str(ROOT / "ledger"))
        import folds
        import lifecycle
        import make_tape
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"ledger unavailable: {e}"
    problems = [f"lifecycle: {x}" for x in lifecycle.selftest()]
    events = make_tape.build(seed=20260903, cases=25)
    problems += [f"folds: {x}" for x in folds.selftest(events)]
    # the ported hash-chained ledger must actually carry the quality vocabulary
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        try:
            summary = make_tape.write_chain(events, Path(d))
        except Exception as e:  # noqa: BLE001
            problems.append(f"product tape rejected the quality vocabulary: {type(e).__name__}: {e}")
            summary = "chain not verified"
        else:
            if not summary.startswith("tape OK"):
                problems.append(f"product tape: {summary}")
    if problems:
        return "FAIL", "; ".join(problems[:3])
    auth = folds.load_authorities()
    n_auth = sum(1 for c in auth if auth[c])
    return "PASS", (f"3 documents render byte-identical twice and under reordered simultaneous "
                    f"events; {len(events):,} events; every table row cited; {n_auth} checks carry a "
                    f"pinned authority in the binder; {summary}")


SITE_PAGE = ROOT / "site" / "surveyor.html"
BOARD_BEGIN = "<!-- BOARD:GENERATED begin"


def gate_evidence_links():
    """Rung 07's executioner: every line on the Morning Board links to its evidence, or the
    line does not render. Three things: the renderer's own battery (which proves a line
    CANNOT be built without evidence, rather than merely that none lacks it); that the
    published page actually contains a generated board; and that every row of that
    published board carries the evidence element. The last one matters because the page is
    what a surveyor reads - a green renderer and a stale page would still be a false page."""
    try:
        sys.path.insert(0, str(ROOT / "ledger"))
        import board
        import make_tape
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"board unavailable: {e}"
    events = make_tape.build(seed=20260903, cases=25)
    problems = [f"board: {x}" for x in board.selftest(events)]
    if not SITE_PAGE.exists():
        problems.append("site/surveyor.html missing")
    else:
        page = SITE_PAGE.read_text(encoding="utf-8")
        if BOARD_BEGIN not in page:
            problems.append("the published page carries no generated board - it is still the mockup")
        else:
            frag = page.split(BOARD_BEGIN, 1)[1].split("BOARD:GENERATED end", 1)[0]
            rows = [r for r in frag.splitlines()
                    if any(c in r for c in ('class="item"', 'class="sub"',
                                            'class="clock"', 'class="fold-line"'))]
            uncited = [r for r in rows if 'class="ev"' not in r]
            if not rows:
                problems.append("the generated board on the page has no rows")
            if uncited:
                problems.append(f"{len(uncited)} published board row(s) carry no evidence element")
            if "board-note" not in frag or "refused" not in frag:
                problems.append("the published board does not state its provenance and refusal count")
    if problems:
        return "FAIL", "; ".join(problems[:3])
    lines, dropped = board.build(events, "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z")
    cited = sum(len(l.evidence) for l in lines)
    return "PASS", (f"{len(lines)} board lines, every one citing its evidence ({cited:,} handles), "
                    f"{len(dropped)} refused for lacking it; the published page carries the "
                    f"generated board and its provenance")


def gate_foreign_harness():
    """Rung 09's executioner: can a harness that is not us complete a fit here?

    The kit is graded by the command a foreign harness would actually run, which is the
    only honest way to grade a kit - a conformance report we do not run is a claim, and
    this whole repository is an argument against those. It also requires the REFUSED
    examples to be refused FOR THE REASON THEY DECLARE, because a narrated refusal nobody
    re-runs decays into fiction, and the refusals are the half that transfers."""
    # Loaded BY PATH, never by name. `import run` finds experiments/f-fixture/run.py first,
    # and this gate briefly graded that instead - passing green on the wrong module. A gate
    # that can be satisfied by a name collision is not a gate.
    try:
        import contextlib
        import importlib.util
        import io
        spec = importlib.util.spec_from_file_location(
            "surveyor_conformance", ROOT / "conformance" / "run.py")
        conformance = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conformance)
    except Exception as e:  # noqa: BLE001
        return "CANNOT-EVALUATE", f"conformance harness unavailable: {type(e).__name__}: {e}"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = conformance.main()
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"conformance crashed: {type(e).__name__}: {e}"
    if rc != 0:
        bad = [n for n in conformance._bad]
        return "FAIL", f"conformance: {len(bad)} failed - {', '.join(bad[:4])}"
    if not (ROOT / "AGENTS.md").exists():
        return "FAIL", "AGENTS.md missing - a foreign harness has no boot contract"
    refused = len(list((ROOT / "examples/worked/rejected").glob("*.check.yml")))
    asked = len([l for l in (ROOT / "elicit/questions.yml").read_text(encoding="utf-8").splitlines()
                 if l.startswith("check: ")])
    return "PASS", (f"conformance green ({len(conformance._ok)} checks); {refused} refused drafts each "
                    f"refused for the class it declares; {asked} variation points each carry a question; "
                    f"AGENTS.md + elicit/method.md + adapters/CONTRACT.md present; adapters empty by design")


def main():
    record = "--record" in sys.argv
    results = [
        ("G-FOLD",) + gate_fold(),
        ("G-PRIVACY",) + gate_privacy(),
        ("G-CATALOG",) + gate_catalog(),
        ("F-FIXTURE",) + gate_fixture(),
        ("G-CATALOG-COMPLETE",) + gate_catalog_complete(),
        ("G-FIELDS",) + gate_fields(),
        ("G-ANCHOR-PLANTS",) + gate_anchor_plants(),
        ("F-FIXTURE-WORLD",) + gate_fixture_world(),
        ("G-CROSSWALK-PINS",) + gate_crosswalk_pins(),
        ("G-FOLD-DETERMINISM",) + gate_fold_determinism(),
        ("G-EVIDENCE-LINKS",) + gate_evidence_links(),
        ("G-FOREIGN-HARNESS",) + gate_foreign_harness(),
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
        with TAPE.open("a", encoding="utf-8", newline="\n") as f:
            for name, status, detail in results:
                f.write(json.dumps({"ts": ts, "session": "gates", "type": "verdict",
                                    "gate": name, "status": status,
                                    "detail": detail}) + "\n")
        fold.write_folds()
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
