#!/usr/bin/env python3
"""floor/engine.py - SURVEYOR's floor: loads checks, evaluates predicates, three-state.

THE RECORD SCHEMA (the project's data spine - law from S1, decided before code):
a fixture (and later, an adapter emission) is
    {"expect": "PASS|HOLD|FLAG|ALARM|CANNOT-EVALUATE",   # fixtures only
     "record":  {...current state, flat-ish dict...},
     "history": [{"field":..., "value":..., "ts":..., "actor_role":...}, ...],
     "note":    "why this fixture exists"}
Checks trigger on the record's current state; timer/sequence checks (rung 03) will
read history. Nothing else is assumed.

THE PREDICATE DSL v0 (deliberately small - a quality director can read it):
    predicate := expr CMP expr | exists(PATH) | not exists(PATH)
    expr      := count(PATH) | PATH | NUMBER | 'string'
    PATH      := IDENT ( '[' IDENT ']' | '.' IDENT )*
    CMP       := <= | >= | == | != | < | >
Semantics: IDENTs resolve in record; a[b] indexes a by the VALUE of record's b;
count() = len of list/dict; exists() is the ONE place where a missing path means
False rather than CANNOT-EVALUATE. Anywhere else, missing data -> CANNOT-EVALUATE
(three-state honesty, law A4: a check that cannot judge must say so, never pass).
Escape hatch (unused so far): `impl: python` + `impl_why:` - each use listed honestly.
If more than ~8 of 59 checks need the hatch, the DSL is wrong and we say so (S1 decision).

Verdicts: predicate True -> PASS; False -> the check's action (HOLD|FLAG|ALARM);
unresolvable -> CANNOT-EVALUATE.

CLI: python floor/engine.py [--json]   # run the full fixture battery
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = ROOT / "floor" / "checks"
FIXTURES_DIR = ROOT / "floor" / "fixtures"

FORBIDDEN_IMPORTS = re.compile(
    r"^\s*(?:import|from)\s+(numpy|torch|pandas|sklearn|requests|urllib|socket|http)\b",
    re.MULTILINE)


class CannotEvaluate(Exception):
    """Raised when a predicate touches data the record does not carry."""


# ---------------------------------------------------------------- flat YAML
def load_check_yml(path: Path) -> dict[str, Any]:
    """Deliberately minimal flat-YAML reader: `key: value` lines, quoted or bare
    strings, ints, inline [a, b] lists, full-line and trailing # comments.
    Checks are AUTHORED under this constraint - flatness is a feature (law: a
    quality director can read a check)."""
    out: dict[str, Any] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path.name}: not key:value - {raw!r}")
        key, val = line.split(":", 1)
        val = val.strip()
        # strip trailing comment (only when not inside quotes)
        if val.count('"') % 2 == 0 and val.count("'") % 2 == 0 and " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            out[key.strip()] = items
        elif val.startswith('"') and val.endswith('"') and len(val) >= 2:
            out[key.strip()] = val[1:-1]
        elif val.startswith("'") and val.endswith("'") and len(val) >= 2:
            out[key.strip()] = val[1:-1]
        elif re.fullmatch(r"-?\d+", val):
            out[key.strip()] = int(val)
        else:
            out[key.strip()] = val
    return out


# ---------------------------------------------------------------- DSL v0
_TOKEN = re.compile(r"\s*(<=|>=|==|!=|<|>|\[|\]|\(|\)|\.|,|-?\d+|'[^']*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_]*)")


def _tokenize(src: str) -> list[str]:
    toks, pos = [], 0
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:
            if src[pos:].strip():
                raise ValueError(f"bad token at: {src[pos:]!r}")
            break
        toks.append(m.group(1))
        pos = m.end()
    return toks


class _Parser:
    def __init__(self, toks: list[str]):
        self.toks, self.i = toks, 0

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, want: str | None = None) -> str:
        tok = self.peek()
        if tok is None or (want is not None and tok != want):
            raise ValueError(f"expected {want or 'token'}, got {tok!r}")
        self.i += 1
        return tok

    def parse_predicate(self) -> dict:
        if self.peek() == "not":
            self.take()
            inner = self.parse_predicate()
            return {"op": "not", "a": inner}
        left = self.parse_expr()
        if self.peek() in ("<=", ">=", "==", "!=", "<", ">"):
            op = self.take()
            right = self.parse_expr()
            node = {"op": op, "a": left, "b": right}
        elif left.get("op") == "exists":
            node = left
        else:
            raise ValueError("predicate must be a comparison or exists()")
        if self.peek() is not None:
            raise ValueError(f"trailing tokens: {self.toks[self.i:]}")
        return node

    def parse_expr(self) -> dict:
        tok = self.peek()
        if tok in ("count", "exists"):
            fn = self.take()
            self.take("(")
            path = self.parse_path()
            self.take(")")
            return {"op": fn, "a": path}
        if tok and re.fullmatch(r"-?\d+", tok):
            self.take()
            return {"op": "lit", "v": int(tok)}
        if tok and tok[0] in "'\"":
            self.take()
            return {"op": "lit", "v": tok[1:-1]}
        return self.parse_path()

    def parse_path(self) -> dict:
        steps: list[dict] = [{"k": "name", "v": self.take()}]
        while self.peek() in ("[", "."):
            if self.take() == "[":
                steps.append({"k": "index_by", "v": self.take()})
                self.take("]")
            else:
                steps.append({"k": "field", "v": self.take()})
        return {"op": "path", "steps": steps}


def _resolve_path(node: dict, record: dict) -> Any:
    steps = node["steps"]
    name = steps[0]["v"]
    if name not in record:
        raise CannotEvaluate(f"record has no field {name!r}")
    cur = record[name]
    for step in steps[1:]:
        if step["k"] == "index_by":
            key_field = step["v"]
            if key_field not in record:
                raise CannotEvaluate(f"record has no field {key_field!r} (index)")
            key = record[key_field]
            if not isinstance(cur, dict):
                raise CannotEvaluate(f"cannot index non-object by {key_field!r}")
            if key not in cur:
                raise CannotEvaluate(f"no entry for {key!r}")
            cur = cur[key]
        else:
            if not isinstance(cur, dict) or step["v"] not in cur:
                raise CannotEvaluate(f"no field {step['v']!r}")
            cur = cur[step["v"]]
    return cur


def _eval(node: dict, record: dict) -> Any:
    op = node["op"]
    if op == "lit":
        return node["v"]
    if op == "path":
        return _resolve_path(node, record)
    if op == "count":
        v = _eval(node["a"], record)
        if isinstance(v, (list, dict, str)):
            return len(v)
        raise CannotEvaluate(f"count() of non-collection {type(v).__name__}")
    if op == "exists":
        try:
            _resolve_path(node["a"], record)
            return True
        except CannotEvaluate:
            return False           # the ONE lawful missing->False
    if op == "not":
        return not _eval(node["a"], record)
    a, b = _eval(node["a"], record), _eval(node["b"], record)
    if type(a) is bool or type(b) is bool or \
       (isinstance(a, str) != isinstance(b, str)):
        raise CannotEvaluate(f"type mismatch: {type(a).__name__} vs {type(b).__name__}")
    return {"<=": a <= b, ">=": a >= b, "==": a == b,
            "!=": a != b, "<": a < b, ">": a > b}[op]


def evaluate(check: dict, record: dict) -> str:
    """One check against one record -> PASS | <action> | CANNOT-EVALUATE."""
    try:
        ast = _Parser(_tokenize(check["predicate"])).parse_predicate()
        ok = _eval(ast, record)
    except CannotEvaluate:
        return "CANNOT-EVALUATE"
    if ok:
        return "PASS"
    return str(check.get("action", "flag")).upper()


# ---------------------------------------------------------------- battery
def no_model_scan() -> list[str]:
    """Law B2's executioner (adopted from the estate): the floor imports no
    learned/network machinery. Scans floor/ and ledger/ sources."""
    hits = []
    for d in (ROOT / "floor", ROOT / "ledger"):
        for p in d.glob("*.py"):
            m = FORBIDDEN_IMPORTS.search(p.read_text(encoding="utf-8"))
            if m:
                hits.append(f"{p.relative_to(ROOT).as_posix()}: imports {m.group(1)}")
    return hits


def run_battery() -> dict[str, Any]:
    """Every encoded check against every one of its fixtures. Naming law:
    pass_* must PASS; fail_* must land the check's action; cannot_* must
    CANNOT-EVALUATE; every fixture's own `expect` field must agree too."""
    results: dict[str, Any] = {"checks": {}, "encoded": 0, "broken": [],
                               "fixtures_run": 0, "no_model_violations": no_model_scan()}
    for yml in sorted(CHECKS_DIR.glob("SV-*.check.yml")) if CHECKS_DIR.exists() else []:
        cid = yml.name.split(".")[0]
        try:
            check = load_check_yml(yml)
        except Exception as e:  # noqa: BLE001
            results["broken"].append(f"{cid}: unparseable yml ({e})")
            continue
        fdir = FIXTURES_DIR / cid
        fixtures = sorted(fdir.glob("*.json")) if fdir.exists() else []
        problems: list[str] = []
        for fx in fixtures:
            data = json.loads(fx.read_text(encoding="utf-8"))
            got = evaluate(check, data.get("record", {}))
            want = data.get("expect")
            by_name = ("PASS" if fx.name.startswith("pass") else
                       "CANNOT-EVALUATE" if fx.name.startswith("cannot") else
                       str(check.get("action", "flag")).upper())
            if want != by_name:
                problems.append(f"{fx.name}: expect field {want!r} disagrees with naming law {by_name!r}")
            elif got != want:
                problems.append(f"{fx.name}: got {got}, expected {want}")
            results["fixtures_run"] += 1
        if not any(f.name.startswith("pass") for f in fixtures) or \
           not any(f.name.startswith("fail") for f in fixtures):
            problems.append("missing pass_* or fail_* fixture (a check without fixtures is a sentence)")
        results["checks"][cid] = {"fixtures": len(fixtures), "problems": problems}
        if problems:
            results["broken"].append(f"{cid}: " + "; ".join(problems))
        else:
            results["encoded"] += 1
    return results


if __name__ == "__main__":
    r = run_battery()
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1))
    else:
        for cid, info in r["checks"].items():
            state = "OK" if not info["problems"] else "BROKEN"
            print(f"{cid}: {state} ({info['fixtures']} fixtures)")
            for p in info["problems"]:
                print(f"   - {p}")
        print(f"battery: {r['encoded']} check(s) fully encoded, "
              f"{len(r['broken'])} broken, {r['fixtures_run']} fixtures run")
        if r["no_model_violations"]:
            print("NO-MODEL VIOLATIONS: " + "; ".join(r["no_model_violations"]))
    sys.exit(1 if (r["broken"] or r["no_model_violations"]) else 0)
