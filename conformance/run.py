#!/usr/bin/env python3
"""conformance/run.py - the one command a foreign harness runs.

If you are an AI harness completing a site's fit, this is the first thing you run and the
last thing you run. It reports what is actually here rather than what any document claims,
and it grades the kit itself:

  1. THE SEED IS INTACT      - the floor battery, the DSL selftest, the clocks, the folds
  2. THE ACCEPTED EXAMPLE MOUNTS - a site-authored check with pass, fail and cannot fixtures
  3. EVERY REFUSED DRAFT IS ACTUALLY REFUSED - and for the reason its own file declares.
     This is the part that matters. A worked example showing only the finished artifact
     teaches a harness to produce something that LOOKS finished. What transfers is the
     shape of the refusals, and a narrated refusal nobody re-runs decays into fiction.
  4. EVERY VARIATION POINT HAS A QUESTION - the catalog cannot grow a site-variant check
     without elicit/questions.yml growing its question, or this fails
  5. THE ADAPTER CONTRACT EXISTS - and adapters/ is empty, which is a claim, not an omission

Exit 0 when all five hold. Stdlib only, no model, no network.

    python conformance/run.py [--verbose]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for d in ("floor", "clocks", "ledger", "crosswalk"):
    sys.path.insert(0, str(ROOT / d))
import engine  # noqa: E402

EXAMPLES = ROOT / "examples" / "worked"
ELICIT = ROOT / "elicit" / "questions.yml"
CATALOG = ROOT / "floor" / "CATALOG.md"
CHECKS = ROOT / "floor" / "checks"

VERBOSE = "--verbose" in sys.argv
_ok, _bad = [], []


def report(name: str, passed: bool, detail: str) -> None:
    (_ok if passed else _bad).append(name)
    mark = "ok    " if passed else "FAILED"
    print(f"  {mark}  {name:<44} {detail}")


# ---------------------------------------------------------------- 1 the seed
def seed_intact() -> None:
    dsl = engine.selftest()
    report("DSL selftest", not dsl, "green" if not dsl else f"{len(dsl)} failure(s): {dsl[0][:70]}")
    r = engine.run_battery()
    report("floor battery", not r["broken"] and not r["no_model_violations"],
           f"{r['encoded']} checks, {r['fixtures_run']} fixtures"
           + ("" if not r["broken"] else f", broken: {r['broken'][0][:60]}"))
    try:
        import test_closure
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            rc = test_closure.run()
        report("clocks closure battery", rc == 0, f"{len(test_closure.PASS)} assertions")
    except Exception as e:  # noqa: BLE001
        report("clocks closure battery", False, f"unavailable: {e}")
    try:
        import folds
        import lifecycle
        import make_tape
        evs = make_tape.build(seed=20260903, cases=12)
        f1, f2 = lifecycle.selftest(), folds.selftest(evs)
        report("ledger + folds", not f1 and not f2,
               "green" if not (f1 or f2) else f"{(f1 + f2)[0][:70]}")
    except Exception as e:  # noqa: BLE001
        report("ledger + folds", False, f"unavailable: {e}")


# ---------------------------------------------------------------- 2 accepted
def accepted_mounts() -> None:
    d = EXAMPLES / "accepted"
    files = sorted(d.glob("*.check.yml"))
    if not files:
        report("accepted example", False, "none present")
        return
    for p in files:
        c = engine.load_check_yml(p)
        probs = engine.check_schema_problems(c.get("id", p.stem), c)
        try:
            engine.compile_predicate(str(c["predicate"]))
        except ValueError as e:
            probs.append(f"predicate: {e}")
        else:
            ap = engine.applicability_problem(c)
            if ap:
                probs.append(ap)
        fdir = d / "fixtures" / str(c.get("id"))
        fx = sorted(fdir.glob("*.json")) if fdir.exists() else []
        for kind in ("pass", "fail"):
            if not any(f.name.startswith(kind) for f in fx):
                probs.append(f"no {kind}_* fixture")
        import json
        for f in fx:
            data = json.loads(f.read_text(encoding="utf-8"))
            want = data.get("expect")
            got = engine.evaluate(c, data.get("record", {}))
            if got != want:
                probs.append(f"{f.name}: got {got}, expected {want}")
        report(f"accepted {c.get('id')}", not probs,
               f"{len(fx)} fixtures, mounts clean" if not probs else "; ".join(probs[:2]))


# ---------------------------------------------------------------- 3 refusals
def refuse(draft: dict, path: Path) -> list[str]:
    """Every mechanical objection to a draft check, in one place. Returns refusal CLASSES."""
    out: list[str] = []
    cid = str(draft.get("id", path.stem))

    # a. does it parse, and is it well-formed?
    try:
        engine.compile_predicate(str(draft.get("predicate", "")))
    except ValueError:
        out.append("predicate-does-not-parse")

    # b. does it fire where it does not apply?
    if "predicate-does-not-parse" not in out and engine.applicability_problem(draft):
        out.append("fires-on-the-empty-record")

    # c. does it duplicate a check the mandated seed already carries? A second, divergent
    #    copy of the law is worse than no copy: it drifts locally while the real one moves.
    pred = re.sub(r"\s+", " ", str(draft.get("predicate", ""))).strip()
    for q in sorted(CHECKS.glob("SV-*.check.yml")):
        seeded = engine.load_check_yml(q)
        if pred and re.sub(r"\s+", " ", str(seeded.get("predicate", ""))).strip() == pred:
            out.append("duplicates-a-mandated-check")
            break

    # d. does it claim a layer this kit may not author? L2/L3 only (SPEC section 10).
    if str(draft.get("layer", "")).strip() in ("L0", "L1"):
        out.append("authors-a-mandated-layer")

    # e. law B5, mechanically - but only when the draft DECLARES its correction channel.
    #    SV-062 is a floor check that runs over a check definition, so the floor refuses
    #    the check using the same engine that runs the checks.
    if draft.get("corrects_field") and draft.get("verification_fields"):
        sv062 = engine.load_check_yml(CHECKS / "SV-062.check.yml")
        rec = {"check": {"id": cid, "corrects_field": draft["corrects_field"],
                         "verification_fields": draft["verification_fields"]}}
        if engine.evaluate(sv062, rec) != "PASS":
            out.append("verification-channel-is-the-corrected-field")

    # f. a check without fixtures is a sentence
    fdir = path.parent / "fixtures" / cid
    fx = sorted(fdir.glob("*.json")) if fdir.exists() else []
    if not any(f.name.startswith("fail") for f in fx):
        out.append("no-failing-fixture")
    return out


def refusals_are_real() -> None:
    d = EXAMPLES / "rejected"
    files = sorted(d.glob("*.check.yml"))
    if not files:
        report("refused drafts", False, "none present - the most useful half of the kit is missing")
        return
    undeclared = 0
    for p in files:
        draft = engine.load_check_yml(p)
        want = str(draft.get("refusal", "")).strip()
        got = refuse(draft, p)
        if not want:
            undeclared += 1
        ok = bool(got) and (want in got if want else True)
        report(f"refused {p.name[:34]}", ok,
               (f"refused as {want}" + (f" (+{len(got)-1} more)" if len(got) > 1 else ""))
               if ok else f"declared {want!r}, engine said {got or 'nothing - IT WOULD MOUNT'}")
    report("every refused draft declares its class", undeclared == 0,
           "all declared" if undeclared == 0 else f"{undeclared} undeclared")
    # and the narration must exist and name every class
    ref = EXAMPLES / "REFUSED.md"
    if not ref.exists():
        report("REFUSED.md", False, "missing")
    else:
        txt = ref.read_text(encoding="utf-8")
        missing = [str(engine.load_check_yml(p).get("refusal")) for p in files
                   if str(engine.load_check_yml(p).get("refusal")) not in txt]
        report("REFUSED.md names every refusal class", not missing,
               "all narrated" if not missing else f"missing: {missing}")


# ---------------------------------------------------------------- 4 elicit coverage
def elicit_covers_variation_points() -> None:
    if not ELICIT.exists():
        report("elicit coverage", False, "elicit/questions.yml missing")
        return
    asked = set(re.findall(r"^check: (SV-\d{3})", ELICIT.read_text(encoding="utf-8"), re.M))
    variation = set()
    for p in sorted(CHECKS.glob("SV-*.check.yml")):
        c = engine.load_check_yml(p)
        if "L2" in str(c.get("layer", "")):
            variation.add(str(c["id"]))
    missing = sorted(variation - asked)
    extra = sorted(asked - variation)
    report("every variation point has a question", not missing,
           f"{len(asked)}/{len(variation)} asked" if not missing else f"no question for: {', '.join(missing)}")
    if extra:
        report("no question without a variation point", False, f"asks about non-variant checks: {extra}")


# ---------------------------------------------------------------- 5 adapters
def adapter_contract() -> None:
    c = ROOT / "adapters" / "CONTRACT.md"
    report("adapter contract", c.exists(), "present" if c.exists() else "missing")
    bindings = [p for p in (ROOT / "adapters").glob("*") if p.suffix in (".py", ".json", ".yml")]
    report("adapters/ carries no invented binding", not bindings,
           "empty by design - a real binding needs export specs an OPO holds"
           if not bindings else f"{len(bindings)} binding file(s) present, unexpected")


def main() -> int:
    print("SURVEYOR - conformance\n")
    print("1 - the seed")
    seed_intact()
    print("\n2 - the accepted example")
    accepted_mounts()
    print("\n3 - the refused drafts (the half that transfers)")
    refusals_are_real()
    print("\n4 - elicit coverage")
    elicit_covers_variation_points()
    print("\n5 - adapters")
    adapter_contract()
    print(f"\n{len(_ok)} passed, {len(_bad)} failed")
    if _bad:
        print("\nfailed:")
        for n in _bad:
            print(f"  - {n}")
        print("\nThis command reports what is HERE. Trust it over any prose in this repository,")
        print("including AGENTS.md, which was written at a commit and will drift.")
        return 1
    print("\nThe seed is intact, the accepted example mounts, every refused draft is refused for")
    print("the reason it declares, every variation point has its question, and adapters/ is")
    print("empty on purpose. GREEN still mounts nothing: a human signature is the only way across.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    raise SystemExit(main())
