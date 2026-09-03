#!/usr/bin/env python3
"""_build/witness.py - the meta-gate. Law D11, named at S0 and built at S10.

THE PROBLEM, IN THE PROJECT'S OWN WORDS. "Nothing currently stops a session from weakening
gates.py instead of fixing what it caught." Every argument this repository makes rests on
its fences being mechanical - and a fence nobody tests is indistinguishable from a fence
that was quietly removed. A gate that passes on a broken repository is not a gate; it is a
decoration that raises confidence while lowering safety, which is worse than having none.

THE TEST. For each gate, a KNOWN-BAD REPOSITORY: a named, minimal perturbation of the thing
that gate exists to guard. The gate is then run against it and **must not report PASS**.
The gate must report FAIL. CANNOT-EVALUATE is NOT accepted: every perturbation here leaves
the organ present and damages only what the gate guards, so a gate that goes silent on one
of them is a gate that cannot see its own subject. This file accepted silence until the S10
cold-start audit pointed out that it was therefore certifying silence as refusal.

HOW IT IS RUN SAFELY. The whole repository is copied to a temporary directory once. Every
perturbation and every gate run happens THERE, in a subprocess, and the copy is destroyed
afterwards. This file never writes to the working tree - which matters, because a meta-gate
that could corrupt the repository while testing whether the repository can be corrupted
would be an unusually stupid way to lose a day's work.

WHAT IT CANNOT WITNESS, AND SAYS SO. G-COLDSTART is a fresh-agent audit recorded on the
tape by a human or an agent; there is no perturbation a machine can apply to make it fail,
so it is reported UNWITNESSABLE-BY-MACHINE with the reason rather than quietly skipped.

    python _build/witness.py [--verbose] [--only G-FOLD]
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", "__pycache__", "_backups", "out", "node_modules"}
# STRICT. Every perturbation below leaves the organ present and breaks only the thing the
# gate guards, so the gate must be able to JUDGE it and say FAIL. Accepting
# CANNOT-EVALUATE here - as this file did until the S10 audit - meant the meta-gate
# certified "12/12 gates refused a known-bad repository" when a gate had merely fallen
# silent, which is the exact failure the exit policy above now treats as a build break.
ACCEPTED = ("FAIL",)


# ---------------------------------------------------------------- perturbations
# Each returns a one-line description of the damage it did. Each is MINIMAL: one file, one
# edit, aimed at exactly what its gate claims to guard. A perturbation that broke several
# things at once would prove only that something noticed.

def _sub(p: Path, old: str, new: str, count: int = 1) -> None:
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise AssertionError(f"{p.name}: perturbation anchor not found: {old[:60]!r}")
    p.write_text(s.replace(old, new, count), encoding="utf-8", newline="\n")


def p_fold(r: Path) -> str:
    with (r / "_build/STATE.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("\nA line no fold would ever render.\n")
    return "appended a hand-written line to the generated STATE.md"


def p_privacy(r: Path) -> str:
    # A SYNTHETIC hard term, added to the denylist copy and then planted in a shipped file.
    # No real name is written anywhere, and the copy is destroyed with the temp directory.
    d = r / "_local/denylist.txt"
    d.parent.mkdir(parents=True, exist_ok=True)
    with d.open("a", encoding="utf-8", newline="\n") as f:
        f.write("\nZzWitnessSyntheticName\n")
    with (r / "docs/ONE-PAGER_v0.1.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("\nZzWitnessSyntheticName\n")
    return "planted a synthetic denylisted term in a shipped document"


def p_catalog(r: Path) -> str:
    victim = sorted((r / "floor/fixtures/SV-070").glob("fail_*.json"))
    for v in victim:
        v.unlink()
    return "deleted every fail_* fixture of SV-070, leaving an encoded check with nothing that fails"


def p_fixture(r: Path) -> str:
    f = r / "floor/fixtures/SV-070/pass_01.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["record"]["active_primary_offers"]["KI-L"] = ["OF-1001", "OF-1002"]
    f.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8", newline="\n")
    return "made a pass_* fixture of the flagship actually violate its own check"


def p_catalog_complete(r: Path) -> str:
    # Shrink the catalog itself. Deleting a check.yml only made this gate go QUIET
    # ("in progress - 58/59"), which the strict rule above no longer accepts and which
    # was the auditor's point: a catalog that can lose a row without a FAIL has no
    # denominator. Removing the row exercises the pinned CATALOG_COUNT instead.
    f = r / "floor/CATALOG.md"
    s2 = f.read_text(encoding="utf-8")
    i = s2.index("- **SV-055**")
    j = s2.index(chr(10), i) + 1
    f.write_text(s2[:i] + s2[j:], encoding="utf-8", newline=chr(10))
    (r / "floor/checks/SV-055.check.yml").unlink()
    return "removed a check from the catalog and its file, shrinking the pinned count"


def p_fields(r: Path) -> str:
    with (r / "floor/FIELDS.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("\n| `invented.path` | str | SV-999 |\n")
    return "added a field to the generated FIELDS.md that no fixture carries"


def p_anchor_plants(r: Path) -> str:
    f = r / "floor/fixtures/SV-030/pass_anchor_01.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    d["anchor_plant"]["wrong_anchor"] = "recovery.organ_recovery_ts"   # the RIGHT anchor
    f.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8", newline="\n")
    return "pointed an anchor plant at the correct anchor, so it can no longer flip"


def p_fixture_world(r: Path) -> str:
    # Weaken the flagship so a planted defect walks through: `<= 1` becomes `<= 99`.
    _sub(r / "floor/checks/SV-070.check.yml",
         'predicate: "count(active_primary_offers[organ_id]) <= 1"',
         'predicate: "count(active_primary_offers[organ_id]) <= 99"')
    return "weakened the flagship's bound so a planted defect passes"


def p_crosswalk(r: Path) -> str:
    f = r / "crosswalk/mappings/MAP-SV-060-optn-2.6.A.map.yml"
    _sub(f, "Be drawn on two separate occasions", "Be drawn on three separate occasions")
    return "altered one word inside a byte-matched regulatory quote"


def p_fold_determinism(r: Path) -> str:
    _sub(r / "ledger/folds.py",
         "def tape_id(events: list[dict]) -> str:",
         "def tape_id(events: list[dict]) -> str:\n"
         "    import random\n"
         "    return f'{random.random():.17f}'[2:18]  # witness: a fold that reads entropy")
    return "made a fold non-deterministic by giving it a source of entropy"


def p_evidence_links(r: Path) -> str:
    f = r / "site/surveyor.html"
    s = f.read_text(encoding="utf-8")
    start = s.index("<!-- BOARD:GENERATED begin")
    end = s.index("BOARD:GENERATED end")
    block = s[start:end].replace('<span class="ev">', '<span class="notev">', 1)
    f.write_text(s[:start] + block + s[end:], encoding="utf-8", newline="\n")
    return "stripped the evidence element from one row of the published board"


def p_foreign_harness(r: Path) -> str:
    _sub(r / "examples/worked/rejected/06-no-failing-fixture.check.yml",
         "refusal: no-failing-fixture", "refusal: predicate-does-not-parse")
    return "made a refused draft declare a refusal class it is not refused for"


WITNESSES: dict[str, tuple[str, object]] = {
    "G-FOLD": ("a hand-edited fold", p_fold),
    "G-PRIVACY": ("a denylisted term in a shipped file", p_privacy),
    "G-CATALOG": ("an encoded check with no failing fixture", p_catalog),
    "F-FIXTURE": ("a pass fixture that violates its own check", p_fixture),
    "G-CATALOG-COMPLETE": ("a missing check", p_catalog_complete),
    "G-FIELDS": ("a hand-edited vocabulary fold", p_fields),
    "G-ANCHOR-PLANTS": ("an anchor plant that cannot flip", p_anchor_plants),
    "F-FIXTURE-WORLD": ("a weakened check that lets a plant pass", p_fixture_world),
    "G-CROSSWALK-PINS": ("an altered regulatory quote", p_crosswalk),
    "G-FOLD-DETERMINISM": ("a fold that reads entropy", p_fold_determinism),
    "G-EVIDENCE-LINKS": ("a published board row with no evidence", p_evidence_links),
    "G-FOREIGN-HARNESS": ("a refused draft declaring the wrong reason", p_foreign_harness),
}

UNWITNESSABLE = {
    "G-COLDSTART": ("a fresh-agent audit recorded on the tape by a human or an agent; no "
                    "perturbation a machine can apply makes it fail, so it is named here "
                    "rather than quietly skipped"),
}


# ---------------------------------------------------------------- the runner
def copy_repo(dst: Path) -> None:
    shutil.copytree(ROOT, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*SKIP))


def run_gate(repo: Path, gate: str) -> tuple[str, str]:
    # SURVEYOR_WITNESS_CHILD stops a copy's battery from witnessing itself, which would
    # recurse until the disk ran out. --only already prevents it; this is the belt.
    import os
    env = {**os.environ, "SURVEYOR_WITNESS_CHILD": "1"}
    proc = subprocess.run([sys.executable, str(repo / "_build" / "gates.py"), "--only", gate],
                          cwd=repo, capture_output=True, text=True, timeout=600, env=env)
    out = (proc.stdout or "").strip().splitlines()
    for line in out:
        if line.startswith(gate):
            rest = line[len(gate):].strip()
            m = re.match(r"(PASS|FAIL|CANNOT-EVALUATE)\s+(.*)", rest)
            if m:
                return m.group(1), m.group(2)
    return "NO-VERDICT", (proc.stderr or "\n".join(out))[-300:]


def witness(only: str | None = None, verbose: bool = False) -> dict:
    """Returns {gate: {damage, verdict, proven}}. Nothing is written to the working tree."""
    results: dict[str, dict] = {}
    names = [only] if only else list(WITNESSES)
    with tempfile.TemporaryDirectory(prefix="surveyor-witness-") as td:
        repo = Path(td) / "repo"
        copy_repo(repo)
        # baseline: the copy must be green before anything is broken, or a FAIL below
        # would prove nothing about the perturbation
        for gate in names:
            base_status, base_detail = run_gate(repo, gate)
            if base_status != "PASS":
                results[gate] = {"damage": "-", "verdict": base_status, "proven": False,
                                 "note": f"the UNPERTURBED copy did not pass ({base_status}: "
                                         f"{base_detail[:90]}), so this witness proves nothing"}
                continue
            pristine = Path(td) / "pristine"
            if pristine.exists():
                shutil.rmtree(pristine)
            shutil.copytree(repo, pristine)
            desc, fn = WITNESSES[gate]
            try:
                damage = fn(repo)
                status, detail = run_gate(repo, gate)
            except Exception as e:  # noqa: BLE001
                damage, status, detail = f"perturbation failed: {type(e).__name__}: {e}", "ERROR", ""
            finally:
                shutil.rmtree(repo)
                shutil.move(str(pristine), str(repo))
            results[gate] = {"damage": damage, "verdict": status, "proven": status in ACCEPTED,
                             "note": detail[:140], "guards": desc}
            if verbose:
                print(f"  {gate}: {damage}\n      -> {status}  {detail[:110]}")
    return results


def summary(results: dict) -> tuple[list[str], list[str]]:
    proven = [g for g, r in results.items() if r["proven"]]
    unproven = [g for g, r in results.items() if not r["proven"]]
    return sorted(proven), sorted(unproven)



# ---------------------------------------------------------------- the witness's own witness
def selftest() -> list[str]:
    """Prove the meta-gate detects a NEUTERED gate - the exact attack law D11 describes.

    One level of self-reference is worth having and two would be turtles: this takes a copy
    of the repository, rewrites one gate so it can only ever return PASS, and asserts the
    witness reports it UNPROVEN. Without this, 'G-WITNESS would catch a weakened gate' is
    an assumption in a file whose entire subject is not making assumptions."""
    fails: list[str] = []
    with tempfile.TemporaryDirectory(prefix="surveyor-witness-self-") as td:
        repo = Path(td) / "repo"
        copy_repo(repo)
        g = repo / "_build" / "gates.py"
        s2 = g.read_text(encoding="utf-8")
        anchor = "def gate_catalog():"
        if anchor not in s2:
            return ["could not find gate_catalog to neuter"]
        neutered = anchor + "\n    return \"PASS\", \"neutered by the witness selftest\""
        g.write_text(s2.replace(anchor, neutered, 1), encoding="utf-8", newline="\n")
        # run the witness FROM the copy, so it exercises the copy's own neutered gate
        proc = subprocess.run([sys.executable, str(repo / "_build" / "witness.py"),
                               "--only", "G-CATALOG"],
                              cwd=repo, capture_output=True, text=True, timeout=600)
        out = proc.stdout or ""
        if "UNPROVEN" not in out:
            fails.append("a gate rewritten to always return PASS was still reported proven - "
                         "the meta-gate does not detect the attack it exists for")
        if proc.returncode == 0:
            fails.append("the witness exited 0 with an unproven gate")
    return fails

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        f = selftest()
        print("\n".join(f) if f else
              "witness selftest: green (a gate neutered to always PASS is reported UNPROVEN)")
        raise SystemExit(1 if f else 0)
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    verbose = "--verbose" in sys.argv
    print("G-WITNESS - every gate against a known-bad repository\n"
          "(a gate that passes on a broken repository is not a gate)\n")
    res = witness(only, verbose)
    width = max(len(g) for g in res) if res else 10
    for g in sorted(res):
        r = res[g]
        mark = "proven" if r["proven"] else "UNPROVEN"
        print(f"  {mark:<9} {g:<{width}}  broke: {r['damage'][:78]}")
        if not r["proven"]:
            print(f"            -> the gate said {r['verdict']}: {r.get('note', '')[:100]}")
    for g, why in UNWITNESSABLE.items():
        print(f"  n/a       {g:<{width}}  {why[:78]}")
    proven, unproven = summary(res)
    print(f"\n{len(proven)}/{len(res)} gates proven against a known-bad repository")
    if unproven:
        print("UNPROVEN: " + ", ".join(unproven))
        print("A gate that cannot be made to fail is not guarding what it claims to guard.")
    raise SystemExit(1 if unproven else 0)
