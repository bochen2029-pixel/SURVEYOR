#!/usr/bin/env python3
"""clocks/closure.py - SURVEYOR's clocks: the SLA lattice as a temporal network.

Ported near-verbatim from REGISTRAR floor/closure.py @ 2026-08-26 (same author,
MIT) per law D7 (reuse before rebuild); SPEC section 6 names this engine as the
port. SURVEYOR changes: module path, fixtures path, docstring; the arithmetic,
the API, and the INF sentinel are untouched so the parity property holds.

A donor case is a Simple Temporal Network: time points joined by constraints
of the form  a <= x_j - x_i <= b.  Three classical facts do all the work here:

  1. The network is consistent  IF AND ONLY IF  its distance graph has no
     negative cycle.
  2. The tightest implied bounds are the all-pairs shortest paths of that
     graph, computed in the (min, +) tropical semiring.
  3. The feasible window of any event falls out as [ -D[j][0], D[0][j] ].

What that buys, which a flat list of timers cannot: IMPLIED deadlines. At the
moment a case becomes infeasible, no individual field is wrong. The failure
lives in the transitive closure of constraints that are each, separately,
satisfied. A coordinator knows every pairwise rule; nobody computes the
consequence.

And the shortest path is the explanation. `binding_path` returns the chain of
constraints that produced a deadline, recovered from the same computation that
produced the number - so the output is a derivation a quality professional can
check in seconds rather than an assertion.

CORRECTNESS DISCIPLINE
  Times are whole minutes. Arithmetic is integer (min, +), which is exactly
  associative, so there is no floating point anywhere and no accumulated drift.
  INF is 0x3f3f3f3f: large enough to mean unreachable, small enough that
  INF + INF does not overflow a 32-bit integer. An accelerated implementation
  must produce BIT-IDENTICAL output to this one, asserted by equality and never
  by tolerance, or it cannot pass replay determinism.

This module is the deterministic floor. It contains no model, learns nothing,
and behaves identically with every learned component in the system disabled
(law B2; test_closure.py keeps it that way).

Zero dependencies. Python 3.9+.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

INF = 0x3F3F3F3F  # doubles without overflowing int32 - see module docstring

REFERENCE = "T0"  # index 0: the case clock's origin


@dataclass(frozen=True)
class Constraint:
    """One binary temporal constraint, with the provenance to explain itself."""

    later: str
    earlier: str
    weight: int  # x_later - x_earlier <= weight
    label: str = ""
    layer: str = ""  # L0 | L1 | L2 | L3 - which layer owns this constraint

    def render(self) -> str:
        tag = f"  [{self.layer}]" if self.layer else ""
        return f"{self.later} - {self.earlier} <= {self.weight}{tag}  {self.label}".rstrip()


class Infeasible(Exception):
    """The network has a negative cycle: no schedule satisfies these constraints."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__("infeasible: " + " -> ".join(cycle))


@dataclass
class STN:
    """A Simple Temporal Network over named events, in whole minutes."""

    names: list[str] = field(default_factory=lambda: [REFERENCE])
    constraints: list[Constraint] = field(default_factory=list)

    # -- construction --------------------------------------------------------
    def node(self, name: str) -> int:
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)

    def at_most(self, later: str, earlier: str, minutes: int, label: str = "", layer: str = "") -> None:
        """x_later - x_earlier <= minutes."""
        self.node(later), self.node(earlier)
        self.constraints.append(Constraint(later, earlier, minutes, label, layer))

    def at_least(self, later: str, earlier: str, minutes: int, label: str = "", layer: str = "") -> None:
        """x_later - x_earlier >= minutes, i.e. x_earlier - x_later <= -minutes."""
        self.node(later), self.node(earlier)
        self.constraints.append(Constraint(earlier, later, -minutes, label, layer))

    def window(self, event: str, opens: int, closes: int, label: str = "", layer: str = "") -> None:
        """The event happens within [opens, closes], measured from the reference."""
        self.at_most(event, REFERENCE, closes, f"{label} closes", layer)
        self.at_least(event, REFERENCE, opens, f"{label} opens", layer)

    def at(self, event: str, minutes: int, label: str = "", layer: str = "") -> None:
        """A completed event, pinned to a known time."""
        self.at_most(event, REFERENCE, minutes, label, layer)
        self.at_least(event, REFERENCE, minutes, label, layer)

    # -- the closure ---------------------------------------------------------
    def close(self) -> "Closure":
        n = len(self.names)
        idx = {name: i for i, name in enumerate(self.names)}

        D = [[INF] * n for _ in range(n)]
        for i in range(n):
            D[i][i] = 0

        # Keep the tightest constraint per edge, and remember which one it was
        # so a path can explain itself.
        origin: dict[tuple[int, int], Constraint] = {}
        for c in self.constraints:
            i, j = idx[c.earlier], idx[c.later]
            if c.weight < D[i][j]:
                D[i][j] = c.weight
                origin[(i, j)] = c

        # nxt[i][j] = first hop on the shortest path i -> j
        nxt: list[list[int | None]] = [[None] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j and D[i][j] < INF:
                    nxt[i][j] = j

        # Floyd-Warshall in (min, +). In-place is safe: row k and column k are
        # fixed during pass k, because D[k][k] = 0.
        for k in range(n):
            Dk = D[k]
            for i in range(n):
                Dik = D[i][k]
                if Dik >= INF:
                    continue
                Di, nxti = D[i], nxt[i]
                for j in range(n):
                    if Dk[j] >= INF:
                        continue
                    cand = Dik + Dk[j]
                    if cand < Di[j]:
                        Di[j] = cand
                        nxti[j] = nxt[i][k]

        return Closure(self.names, idx, D, nxt, origin)


@dataclass
class Closure:
    names: list[str]
    idx: dict[str, int]
    D: list[list[int]]
    nxt: list[list[int | None]]
    origin: dict[tuple[int, int], Constraint]

    # -- consistency ---------------------------------------------------------
    @property
    def consistent(self) -> bool:
        return all(self.D[i][i] >= 0 for i in range(len(self.names)))

    def negative_cycle(self) -> list[str] | None:
        """
        A cycle whose weights sum negative, if one exists. Returned as the
        sequence of events, closing back on itself - because "infeasible" is
        not an answer a coordinator can act on, and "these five constraints
        cannot all hold" is.
        """
        n = len(self.names)
        for i in range(n):
            if self.D[i][i] >= 0:
                continue
            # A node with a negative self-distance may only REACH the cycle
            # rather than lie on it - the reference point usually does. So walk
            # toward i and take the first node seen twice: that one is on the
            # cycle, and the span between its two occurrences is the cycle.
            seen: dict[int, int] = {}
            order: list[int] = []
            cur = i
            for _ in range(2 * n + 2):
                if cur in seen:
                    ring = order[seen[cur]:] + [cur]
                    return [self.names[x] for x in ring]
                seen[cur] = len(order)
                order.append(cur)
                step = self.nxt[cur][i]
                if step is None:
                    break
                cur = step
        return None

    def cycle_constraints(self, cycle: list[str]) -> list[Constraint]:
        """The constraints along a cycle, so the contradiction can name itself."""
        out: list[Constraint] = []
        for a, b in zip(cycle, cycle[1:]):
            c = self.origin.get((self.idx[a], self.idx[b]))
            if c is not None:
                out.append(c)
        return out

    def check(self) -> None:
        cyc = self.negative_cycle()
        if cyc is not None:
            raise Infeasible(cyc)

    # -- windows -------------------------------------------------------------
    def latest(self, event: str) -> int:
        """The last moment `event` can occur and still leave the case feasible."""
        return self.D[0][self.idx[event]]

    def earliest(self, event: str) -> int:
        """The first moment `event` can occur."""
        return -self.D[self.idx[event]][0]

    def window_of(self, event: str) -> tuple[int, int]:
        return self.earliest(event), self.latest(event)

    def slack(self, event: str, now: int) -> int:
        """Minutes remaining before `event` must happen. Negative means breached."""
        return self.latest(event) - now

    # -- the explanation -----------------------------------------------------
    def _path(self, i: int, j: int) -> list[str]:
        if self.nxt[i][j] is None and i != j:
            return []
        out, cur, guard = [self.names[i]], i, 0
        while cur != j:
            nxt = self.nxt[cur][j]
            if nxt is None or guard > len(self.names) * 2:
                break
            cur = nxt
            out.append(self.names[cur])
            guard += 1
        return out

    def binding_path(self, event: str) -> list[Constraint]:
        """
        The chain of constraints that produces `latest(event)`.

        This is not commentary added afterwards. It is the shortest path that
        realises the bound, recovered from the same computation that produced
        it - which is what makes an advisory output reviewable rather than
        merely assertive.
        """
        j = self.idx[event]
        hops = self._path(0, j)
        out: list[Constraint] = []
        for a, b in zip(hops, hops[1:]):
            c = self.origin.get((self.idx[a], self.idx[b]))
            if c is not None:
                out.append(c)
        return out

    def explain(self, event: str) -> str:
        lines = [f"{event}: latest {hhmm(self.latest(event))}", "  because -"]
        running = 0
        for c in self.binding_path(event):
            running += c.weight
            lines.append(f"    {c.render():<62} cumulative {hhmm(running)}")
        return "\n".join(lines)


# -- presentation --------------------------------------------------------------
def hhmm(minutes: int) -> str:
    """Whole minutes from the reference, rendered as a clock time with day offset."""
    if abs(minutes) >= INF // 2:
        return "unbounded"
    day, rem = divmod(minutes, 1440)
    s = f"{rem // 60:02d}:{rem % 60:02d}"
    if day:
        s += f" ({day:+d}d)"
    return s


# -- case loading --------------------------------------------------------------
def load_case(path: str) -> tuple[STN, dict]:
    """
    Load a case fixture. JSON rather than YAML so the clocks run on a bare
    Python with nothing installed.
    """
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)

    stn = STN()
    for c in doc.get("constraints", []):
        kind = c["kind"]
        label, layer = c.get("label", ""), c.get("layer", "")
        if kind == "at_least":
            stn.at_least(c["later"], c["earlier"], int(c["minutes"]), label, layer)
        elif kind == "at_most":
            stn.at_most(c["later"], c["earlier"], int(c["minutes"]), label, layer)
        elif kind == "window":
            stn.window(c["event"], int(c["opens"]), int(c["closes"]), label, layer)
        elif kind == "at":
            stn.at(c["event"], int(c["minutes"]), label, layer)
        else:
            raise ValueError(f"unknown constraint kind: {kind!r}")
    return stn, doc


def report(path: str, now: int | None = None) -> int:
    stn, doc = load_case(path)
    closure = stn.close()

    print(f"case: {doc.get('id', path)}")
    if doc.get("note"):
        print(f"      {doc['note']}")
    print()

    if not closure.consistent:
        cyc = closure.negative_cycle() or []
        print("INFEASIBLE - this plan cannot be met.")
        print("  " + " -> ".join(cyc))
        print("  these constraints cannot all hold -")
        total = 0
        for c in closure.cycle_constraints(cyc):
            total += c.weight
            print(f"    {c.render():<62} running {total:+d}m")
        print(f"    {'':<62} {'short by':>10} {-total}m")
        return 1

    watch = doc.get("watch") or [n for n in stn.names if n != REFERENCE]
    now = doc.get("now") if now is None else now

    print(f"{'event':<22}{'earliest':>10}{'latest':>12}" + (f"{'slack':>10}" if now is not None else ""))
    print("-" * (44 + (10 if now is not None else 0)))
    for name in watch:
        e, l = closure.window_of(name)
        row = f"{name:<22}{hhmm(e):>10}{hhmm(l):>12}"
        if now is not None:
            s = closure.slack(name, now)
            row += f"{(str(s) + 'm'):>10}" + ("   BREACHED" if s < 0 else "")
        print(row)

    if doc.get("explain"):
        print()
        for name in doc["explain"]:
            print(closure.explain(name))
            print()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("usage: python clocks/closure.py <case.json> [now_minutes]")
        raise SystemExit(2)
    raise SystemExit(report(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None))
