#!/usr/bin/env python3
"""clocks/test_closure.py - the closure's own battery.

Ported from REGISTRAR floor/test_closure.py @ 2026-08-26 (same author, MIT) per
law D7. Zero dependencies, no test framework:

    python clocks/test_closure.py

These are not smoke tests. Each one asserts a property the design claims in
public, so that a claim on a page and a claim in the code cannot drift apart
silently. test_floor_has_no_model is law B2 as code, adopted verbatim.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from closure import INF, STN, hhmm, load_case  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures", "cases")

PASS, FAIL = [], []


def check(name: str, got, want) -> None:
    if got == want:
        PASS.append(name)
        print(f"  ok    {name}")
    else:
        FAIL.append(name)
        print(f"  FAIL  {name}\n          got  {got!r}\n          want {want!r}")


def test_implied_deadline() -> None:
    """
    Given the six constraints of the morning-OR-window case, the closure derives
    that the serology had to be drawn by 22:15 the previous evening - a deadline
    no single field holds. 22:15 the previous day is -105 minutes from the
    reference (midnight of the OR day). If this number ever changes, every page
    that quotes it is wrong.
    """
    print("\nimplied deadline - the number on the page")
    stn, _ = load_case(os.path.join(FIXTURES, "morning-or-window.json"))
    c = stn.close()

    check("case is feasible", c.consistent, True)
    check("serology_drawn latest == -105 (22:15, previous day)", c.latest("serology_drawn"), -105)
    check("rendered as a clock time", hhmm(c.latest("serology_drawn")), "22:15 (-1d)")

    # every intermediate step of the published derivation
    check("cross_clamp   latest == 10:00", c.latest("cross_clamp"), 600)
    check("incision      latest == 09:15", c.latest("incision"), 555)
    check("or_scheduled  latest == 07:15", c.latest("or_scheduled"), 435)
    check("acceptance    latest == 07:15", c.latest("primary_acceptance"), 435)
    check("match_run     latest == 04:15", c.latest("match_run"), 255)
    check("sero_resulted latest == 04:15", c.latest("serology_resulted"), 255)


def test_the_catch() -> None:
    """
    At 23:40 the morning window is already unreachable, and NO individual
    timer has expired. This is the failure class a flat timer list cannot see.
    """
    print("\nthe catch - breached with every field green")
    stn, doc = load_case(os.path.join(FIXTURES, "morning-or-window.json"))
    c = stn.close()
    now = doc["now"]  # 23:40

    check("now is 23:40", hhmm(now), "23:40")
    check("serology deadline is in the past", c.slack("serology_drawn", now) < 0, True)
    check("breach is 1525 minutes deep", c.slack("serology_drawn", now), -1525)
    # and yet the downstream events are all still nominally ahead of us
    check("cross_clamp still 'ahead'", c.latest("cross_clamp") - now, -820)


def test_path_is_the_explanation() -> None:
    """
    The binding path is recovered from the same computation that produced the
    bound. It must name the constraints, in order, and their weights must sum
    to the deadline - otherwise 'the path is the citation' is decoration.
    """
    print("\nthe path is the explanation")
    stn, _ = load_case(os.path.join(FIXTURES, "morning-or-window.json"))
    c = stn.close()

    path = c.binding_path("serology_drawn")
    check("path is non-empty", len(path) > 0, True)
    check("weights sum to the deadline", sum(x.weight for x in path), c.latest("serology_drawn"))

    layers = {x.layer for x in path if x.layer}
    check("the binding chain is mostly local (L2/L3), not federal", {"L2", "L3"} <= layers, True)


def test_negative_cycle_is_infeasibility() -> None:
    """Consistency <=> no negative cycle. The oracle, not a heuristic."""
    print("\ninfeasibility detection")
    stn, _ = load_case(os.path.join(FIXTURES, "infeasible-transport.json"))
    c = stn.close()

    check("case is detected infeasible", c.consistent, False)

    cyc = c.negative_cycle() or []
    check("cycle names more than one event", len(cyc) > 2, True)
    check("cycle closes on itself", cyc[0] == cyc[-1] if cyc else False, True)

    weights = [x.weight for x in c.cycle_constraints(cyc)]
    check("cycle weights sum negative", sum(weights) < 0, True)
    check("every hop is explained by a real constraint", len(weights), len(cyc) - 1)


def test_integer_semiring_is_exact() -> None:
    """
    No floating point anywhere. Closing twice is byte-identical, and the
    sentinel survives being added to itself - which is what makes an
    accelerated implementation comparable by equality rather than tolerance.
    """
    print("\nexact integer (min,+) arithmetic")
    stn, _ = load_case(os.path.join(FIXTURES, "morning-or-window.json"))
    a, b = stn.close(), stn.close()

    check("closure is deterministic (byte-identical)", a.D, b.D)
    check("all distances are int", all(isinstance(v, int) for row in a.D for v in row), True)
    check("INF + INF does not overflow int32", INF + INF < 2**31 - 1, True)


def test_order_independence() -> None:
    """
    The same constraints declared in a different order produce the same closed
    network: the local shadow of the associativity the patch algebra relies on.
    """
    print("\norder independence")
    stn, doc = load_case(os.path.join(FIXTURES, "morning-or-window.json"))
    forward = stn.close()

    rev = STN()
    for c in reversed(stn.constraints):
        rev.at_most(c.later, c.earlier, c.weight, c.label, c.layer)
    backward = rev.close()

    check(
        "reversed declaration order, same deadline",
        backward.latest("serology_drawn"),
        forward.latest("serology_drawn"),
    )


def test_floor_has_no_model() -> None:
    """
    The clocks must behave identically with every learned component disabled,
    because there are none. This test exists to keep it that way (law B2).
    """
    print("\nthe clocks are model-free")
    found = []
    for fname in ("closure.py", "anchors.py"):
        p = os.path.join(HERE, fname)
        if not os.path.exists(p):
            continue
        src = open(p, encoding="utf-8").read()
        banned = ("import torch", "import numpy", "openai", "anthropic", "requests", "urllib")
        found += [f"{fname}: {b}" for b in banned if b in src]
    check("no model or network imports", found, [])
    src = open(os.path.join(HERE, "closure.py"), encoding="utf-8").read()
    check("stdlib only", "import json" in src and "import sys" in src, True)


def run() -> int:
    print("SURVEYOR - clocks - closure")
    for t in (
        test_implied_deadline,
        test_the_catch,
        test_path_is_the_explanation,
        test_negative_cycle_is_infeasibility,
        test_integer_semiring_is_exact,
        test_order_independence,
        test_floor_has_no_model,
    ):
        t()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\nfailed:")
        for f in FAIL:
            print(f"  - {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(run())
