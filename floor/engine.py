#!/usr/bin/env python3
"""floor/engine.py - SURVEYOR's floor: loads checks, evaluates predicates, three-state.

THE RECORD SCHEMA (the project's data spine - law from S1, decided before code):
a fixture (and later, an adapter emission) is
    {"expect": "PASS|HOLD|FLAG|ALARM|CANNOT-EVALUATE",   # fixtures only
     "record":  {...current state, flat-ish dict...},
     "history": [{"field":..., "value":..., "ts":..., "actor_role":...}, ...],
     "note":    "why this fixture exists"}
Checks trigger on the record's current state; the STN over history is rung 03.
Two conventions added at S2 (additive to the S1 freeze):
  - record.as_of  : the evaluation instant (ISO-8601). Clock predicates read it when
                    the completing event has not happened yet.
  - history[].actor_id : optional opaque staff id beside actor_role (attribution
                    checks need an identity; still never a name).

THE PREDICATE DSL v1 (grown from v0 at S2; v0 is a strict subset - tape decision):
    pred      := or_pred ( 'implies' or_pred )?
    or_pred   := and_pred ( 'or' and_pred )*
    and_pred  := not_pred ( 'and' not_pred )*
    not_pred  := 'not' not_pred | atom
    atom      := '(' pred ')'
               | exists(PATH)                 present, not null, not "" - the ONE lawful missing->False
               | contains(PATH, expr)         list membership
               | subset(PATH, PATH)           every value of the first list is in the second
               | same_set(PATH, PATH)         both lists hold the same values
               | every(PATH, pred)            for each item: item fields resolve first, then the record
               | every_pair(PATH, pred)       for each adjacent pair: prev.<field> / next.<field>
               | within(expr, PATH, DUR)      clock: done - anchor <= bound; done missing -> as_of - anchor <= bound
               | by(expr, PATH)               clock: done <= deadline; done missing -> as_of <= deadline
               | expr CMP expr
    expr      := term ( ('+'|'-') term )*
    term      := count(PATH) | distinct(PATH [, IDENT]) | sum(PATH, expr)
               | occurrences(PATH, IDENT, expr)  how many items of the list carry that field == expr
               | minutes_between(expr, expr)  second minus first, in minutes
               | month_end_of(expr)           the timestamp ending the given timestamp's month
               | month_end_following(expr)    the timestamp ending the month after the given one
               | PATH | NUMBER | DUR | 'string' | true | false
    PATH      := IDENT ( '[' PATH ']' | '.' IDENT )*   a[b] indexes a by the VALUE found at path b
    DUR       := NUMBER ('m'|'h'|'d'|'bd')             minutes; bd = business days, within() only
    CMP       := <= | >= | == | != | < | >
Reserved words (and, or, not, implies, true, false, every function name, prev, next)
are refused in EVERY path segment, not only the first: a record field may not be
named `by` or `next`. v1.1 (S2b, after the independent review): occurrences(),
month_end_of(), within() taking an expression as its anchor, the L1/L2 layer tag.
Semantics (three-state honesty, law A4): missing data -> CANNOT-EVALUATE everywhere
except inside exists(); blank ("" / null) counts as missing; a type mismatch in a
comparison is CANNOT-EVALUATE, never a silent False. and/or/implies evaluate left to
right and stop as soon as the result is determined, so `not exists(x) or f(x)` is the
lawful way to guard an optional field. Quantifiers evaluate every item; one item that
cannot be judged makes the whole quantifier CANNOT-EVALUATE.
Escape hatch `impl: python` + `impl_why:` - still unused; the S1 rule stands (>8 uses
across the catalog = the DSL is wrong and we print that).

Verdicts: predicate True -> PASS; False -> the check's action (HOLD|FLAG|ALARM);
unresolvable -> CANNOT-EVALUATE.

CLI: python floor/engine.py [--json]         run the full fixture battery
     python floor/engine.py --selftest        the DSL against known-good and known-bad inputs
     python floor/engine.py --fields [--write] the record vocabulary fold (floor/FIELDS.md)
"""
from __future__ import annotations

import calendar
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CHECKS_DIR = ROOT / "floor" / "checks"
FIXTURES_DIR = ROOT / "floor" / "fixtures"
FIELDS_MD = ROOT / "floor" / "FIELDS.md"

FORBIDDEN_IMPORTS = re.compile(
    r"^\s*(?:import|from)\s+(numpy|torch|pandas|sklearn|requests|urllib|socket|http)\b",
    re.MULTILINE)

# The check schema (law A3: typed, sourced, expiring, carrying its inverse).
REQUIRED_KEYS = ("id", "title", "family", "layer", "authority", "trigger", "predicate",
                 "action", "message", "evidence", "expires", "inverse", "tests")
LAYERS = {"L0", "L1", "L2", "L0/L2", "L1/L2"}
TRIGGERS = {"on_write", "on_close_attempt", "continuous", "on_mount"}
ACTIONS = {"hold", "flag", "alarm"}


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


def check_schema_problems(cid: str, check: dict[str, Any]) -> list[str]:
    """The schema half of law A3, graded mechanically."""
    problems = []
    for k in REQUIRED_KEYS:
        if k not in check or check[k] in ("", None, []):
            problems.append(f"missing required key {k!r}")
    if check.get("id") != cid:
        problems.append(f"id {check.get('id')!r} does not match filename {cid}")
    if check.get("layer") not in LAYERS:
        problems.append(f"layer {check.get('layer')!r} not in {sorted(LAYERS)}")
    if check.get("trigger") not in TRIGGERS:
        problems.append(f"trigger {check.get('trigger')!r} not in {sorted(TRIGGERS)}")
    if check.get("action") not in ACTIONS:
        problems.append(f"action {check.get('action')!r} not in {sorted(ACTIONS)}")
    if not isinstance(check.get("evidence"), list):
        problems.append("evidence must be an inline list [a, b]")
    if check.get("trigger") == "continuous" and \
       not (check.get("anchor") and check.get("anchor_why")):
        problems.append("a continuous (clock) check must declare anchor + anchor_why (law B1)")
    if "impl" in check and not check.get("impl_why"):
        problems.append("impl escape hatch requires impl_why")
    return problems


# ---------------------------------------------------------------- DSL v1
_TOKEN = re.compile(
    r"\s*(<=|>=|==|!=|<|>|\[|\]|\(|\)|\.|,|\+|"
    r"\d+(?:bd|m|h|d)\b|-?\d+(?:\.\d+)?|-|'[^']*'|\"[^\"]*\"|[A-Za-z_][A-Za-z0-9_]*)")
_KEYWORDS = {"and", "or", "not", "implies", "true", "false"}
_BOOL_FNS = {"exists", "contains", "subset", "same_set", "every", "every_pair", "within", "by"}
_EXPR_FNS = {"count", "distinct", "sum", "occurrences", "minutes_between", "month_end_of",
             "month_end_following"}
_RESERVED = _KEYWORDS | _BOOL_FNS | _EXPR_FNS | {"prev", "next"}
_CMP = ("<=", ">=", "==", "!=", "<", ">")
_DUR_UNIT = {"m": 1, "h": 60, "d": 1440}


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

    # -- predicates
    def parse_top(self) -> dict:
        node = self.parse_pred()
        if self.peek() is not None:
            raise ValueError(f"trailing tokens: {self.toks[self.i:]}")
        return node

    def parse_pred(self) -> dict:
        left = self.parse_or()
        if self.peek() == "implies":
            self.take()
            right = self.parse_or()
            return {"op": "implies", "a": left, "b": right}
        return left

    def parse_or(self) -> dict:
        node = self.parse_and()
        while self.peek() == "or":
            self.take()
            node = {"op": "or", "a": node, "b": self.parse_and()}
        return node

    def parse_and(self) -> dict:
        node = self.parse_not()
        while self.peek() == "and":
            self.take()
            node = {"op": "and", "a": node, "b": self.parse_not()}
        return node

    def parse_not(self) -> dict:
        if self.peek() == "not":
            self.take()
            return {"op": "not", "a": self.parse_not()}
        return self.parse_atom()

    def parse_atom(self) -> dict:
        tok = self.peek()
        if tok == "(":
            self.take()
            node = self.parse_pred()
            self.take(")")
            return node
        if tok in _BOOL_FNS:
            return self.parse_bool_fn()
        left = self.parse_expr()
        op = self.peek()
        if op not in _CMP:
            raise ValueError("predicate must be a comparison, a boolean function, or a grouping")
        self.take()
        right = self.parse_expr()
        return {"op": op, "a": left, "b": right}

    def parse_bool_fn(self) -> dict:
        fn = self.take()
        self.take("(")
        if fn == "exists":
            node = {"op": "exists", "a": self.parse_path()}
        elif fn == "contains":
            p = self.parse_path()
            self.take(",")
            node = {"op": "contains", "a": p, "b": self.parse_expr()}
        elif fn in ("subset", "same_set"):
            p = self.parse_path()
            self.take(",")
            node = {"op": fn, "a": p, "b": self.parse_path()}
        elif fn in ("every", "every_pair"):
            p = self.parse_path()
            self.take(",")
            node = {"op": fn, "a": p, "b": self.parse_pred()}
        elif fn == "within":
            anchor = self.parse_expr()
            self.take(",")
            done = self.parse_path()
            self.take(",")
            node = {"op": "within", "a": anchor, "b": done, "bound": self.parse_duration()}
        else:  # by
            deadline = self.parse_expr()
            self.take(",")
            node = {"op": "by", "a": deadline, "b": self.parse_path()}
        self.take(")")
        return node

    def parse_duration(self) -> dict:
        tok = self.take()
        m = re.fullmatch(r"(\d+)(bd|m|h|d)", tok)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            if unit == "bd":
                return {"op": "dur", "v": n, "unit": "bd"}
            return {"op": "dur", "v": n * _DUR_UNIT[unit], "unit": "m"}
        if re.fullmatch(r"\d+", tok):
            return {"op": "dur", "v": int(tok), "unit": "m"}
        raise ValueError(f"expected a duration like 24h / 7d / 5bd, got {tok!r}")

    # -- expressions
    def parse_expr(self) -> dict:
        node = self.parse_term()
        while self.peek() in ("+", "-"):
            op = self.take()
            node = {"op": "arith", "sym": op, "a": node, "b": self.parse_term()}
        return node

    def parse_term(self) -> dict:
        tok = self.peek()
        if tok is None:
            raise ValueError("unexpected end of predicate")
        if tok in _EXPR_FNS:
            return self.parse_expr_fn()
        m = re.fullmatch(r"(\d+)(bd|m|h|d)", tok)
        if m:
            self.take()
            if m.group(2) == "bd":
                raise ValueError("business-day durations are only valid as the bound of within()")
            return {"op": "lit", "v": int(m.group(1)) * _DUR_UNIT[m.group(2)]}
        if re.fullmatch(r"-?\d+(?:\.\d+)?", tok):
            self.take()
            return {"op": "lit", "v": float(tok) if "." in tok else int(tok)}
        if tok[0] in "'\"":
            self.take()
            return {"op": "lit", "v": tok[1:-1]}
        if tok in ("true", "false"):
            self.take()
            return {"op": "lit", "v": tok == "true"}
        if tok in _KEYWORDS or tok in _BOOL_FNS:
            raise ValueError(f"{tok!r} cannot start an expression")
        return self.parse_path()

    def parse_expr_fn(self) -> dict:
        fn = self.take()
        self.take("(")
        if fn == "count":
            node = {"op": "count", "a": self.parse_path()}
        elif fn == "distinct":
            p = self.parse_path()
            field = None
            if self.peek() == ",":
                self.take()
                field = self.take()
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field):
                    raise ValueError(f"distinct(): expected a field name, got {field!r}")
            node = {"op": "distinct", "a": p, "field": field}
        elif fn == "sum":
            p = self.parse_path()
            self.take(",")
            node = {"op": "sum", "a": p, "b": self.parse_expr()}
        elif fn == "occurrences":
            p = self.parse_path()
            self.take(",")
            field = self.take()
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field) or field in _RESERVED:
                raise ValueError(f"occurrences(): expected a field name, got {field!r}")
            self.take(",")
            node = {"op": "occurrences", "a": p, "field": field, "b": self.parse_expr()}
        elif fn == "minutes_between":
            a = self.parse_expr()
            self.take(",")
            node = {"op": "minutes_between", "a": a, "b": self.parse_expr()}
        elif fn == "month_end_of":
            node = {"op": "month_end_of", "a": self.parse_expr()}
        else:  # month_end_following
            node = {"op": "month_end_following", "a": self.parse_expr()}
        self.take(")")
        return node

    def _segment(self, what: str, root: bool = False) -> str:
        name = self.take()
        reserved = _RESERVED - ({"prev", "next"} if root else set())   # pair scopes are lawful roots
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or name in reserved:
            raise ValueError(f"expected a {what}, got {name!r} (reserved words cannot name fields)")
        return name

    def parse_path(self) -> dict:
        steps: list[dict] = [{"k": "name", "v": self._segment("field path", root=True)}]
        while self.peek() in ("[", "."):
            if self.take() == "[":
                steps.append({"k": "index_by", "v": self.parse_path()})
                self.take("]")
            else:
                steps.append({"k": "field", "v": self._segment("field name")})
        return {"op": "path", "steps": steps}


def compile_predicate(src: str) -> dict:
    return _Parser(_tokenize(src)).parse_top()


# ---------------------------------------------------------------- evaluation
def _path_text(node: dict) -> str:
    out = []
    for s in node["steps"]:
        if s["k"] == "name":
            out.append(s["v"])
        elif s["k"] == "field":
            out.append("." + s["v"])
        else:
            out.append("[" + _path_text(s["v"]) + "]")
    return "".join(out)


def _resolve_path(node: dict, scopes: list[dict]) -> Any:
    """Innermost scope first (quantifier items), then outward to the record."""
    steps = node["steps"]
    name = steps[0]["v"]
    cur = None
    for scope in reversed(scopes):
        if isinstance(scope, dict) and name in scope:
            cur = scope[name]
            break
    else:
        raise CannotEvaluate(f"record has no field {name!r}")
    for step in steps[1:]:
        if step["k"] == "index_by":
            key = _resolve_path(step["v"], scopes)
            if key is None or key == "":
                raise CannotEvaluate(f"blank index value at {_path_text(step['v'])}")
            if not isinstance(cur, dict):
                raise CannotEvaluate(f"cannot index a non-object by {_path_text(step['v'])}")
            if key not in cur:
                raise CannotEvaluate(f"no entry for {key!r}")
            cur = cur[key]
        else:
            if not isinstance(cur, dict) or step["v"] not in cur:
                raise CannotEvaluate(f"no field {step['v']!r}")
            cur = cur[step["v"]]
    return cur


def _present(v: Any) -> bool:
    return v is not None and v != ""


def _ts(v: Any, what: str = "timestamp") -> datetime:
    if not isinstance(v, str) or not v:
        raise CannotEvaluate(f"{what} is not a timestamp: {v!r}")
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        raise CannotEvaluate(f"{what} is not ISO-8601: {v!r}") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _minutes(a: datetime, b: datetime) -> float:
    m = (b - a).total_seconds() / 60.0
    return int(m) if m == int(m) else m


def _business_days(a: datetime, b: datetime) -> int:
    """Weekdays in (a, b] by calendar date; negative if b precedes a. Holidays are
    site-variant (an L2 refinement) and are not modelled here."""
    da, db = a.date(), b.date()
    sign = 1
    if db < da:
        da, db, sign = db, da, -1
    n, d = 0, da
    while d < db:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return sign * n


def _month_end_of(dt: datetime) -> str:
    last = calendar.monthrange(dt.year, dt.month)[1]
    return f"{dt.year:04d}-{dt.month:02d}-{last:02d}T23:59:59Z"


def _month_end_following(dt: datetime) -> str:
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-{last:02d}T23:59:59Z"


def _list_at(node: dict, scopes: list[dict], what: str) -> list:
    v = _resolve_path(node, scopes)
    if not isinstance(v, list):
        raise CannotEvaluate(f"{what} expects a list at {_path_text(node)}")
    return v


def _hashable(v: Any, where: str) -> Any:
    try:
        hash(v)
    except TypeError:
        raise CannotEvaluate(f"{where}: values must be scalars") from None
    if v is None:
        raise CannotEvaluate(f"{where}: blank value")
    return v


def _cmp(op: str, a: Any, b: Any) -> bool:
    if a is None or b is None:
        raise CannotEvaluate("blank value in comparison")
    if isinstance(a, bool) or isinstance(b, bool):
        if not (isinstance(a, bool) and isinstance(b, bool)) or op not in ("==", "!="):
            raise CannotEvaluate("booleans compare only with booleans, only for equality")
    elif isinstance(a, (list, dict)) or isinstance(b, (list, dict)):
        raise CannotEvaluate("collections compare via count/subset/same_set, not directly")
    elif isinstance(a, str) != isinstance(b, str):
        raise CannotEvaluate(f"type mismatch: {type(a).__name__} vs {type(b).__name__}")
    return {"<=": a <= b, ">=": a >= b, "==": a == b,
            "!=": a != b, "<": a < b, ">": a > b}[op]


def _done_or_as_of(done_node: dict, scopes: list[dict]) -> datetime:
    try:
        v = _resolve_path(done_node, scopes)
    except CannotEvaluate:
        v = None
    if _present(v):
        return _ts(v, _path_text(done_node))
    for scope in reversed(scopes):
        if isinstance(scope, dict) and _present(scope.get("as_of")):
            return _ts(scope["as_of"], "as_of")
    raise CannotEvaluate(f"{_path_text(done_node)} not yet recorded and no as_of to judge against")


def _eval(node: dict, scopes: list[dict]) -> Any:
    op = node["op"]
    if op == "lit":
        return node["v"]
    if op == "path":
        return _resolve_path(node, scopes)
    if op == "dur":
        return node["v"]
    if op == "arith":
        a, b = _eval(node["a"], scopes), _eval(node["b"], scopes)
        if isinstance(a, bool) or isinstance(b, bool) or \
           not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise CannotEvaluate("arithmetic needs numbers")
        return a + b if node["sym"] == "+" else a - b
    if op == "count":
        v = _eval(node["a"], scopes)
        if isinstance(v, (list, dict, str)):
            return len(v)
        raise CannotEvaluate(f"count() of non-collection {type(v).__name__}")
    if op == "distinct":
        items = _list_at(node["a"], scopes, "distinct()")
        if node["field"] is not None:
            vals = []
            for it in items:
                if not isinstance(it, dict) or node["field"] not in it:
                    raise CannotEvaluate(f"distinct(): item lacks {node['field']!r}")
                vals.append(it[node["field"]])
        else:
            vals = items
        return len({_hashable(v, "distinct()") for v in vals})
    if op == "sum":
        total: float = 0
        for it in _list_at(node["a"], scopes, "sum()"):
            v = _eval(node["b"], scopes + [it if isinstance(it, dict) else {"value": it}])
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise CannotEvaluate("sum() over non-numbers")
            total += v
        return total
    if op == "occurrences":
        items = _list_at(node["a"], scopes, "occurrences()")
        want = _eval(node["b"], scopes)
        if want is None or want == "":
            raise CannotEvaluate("occurrences(): blank value to count")
        n = 0
        for it in items:
            if not isinstance(it, dict) or node["field"] not in it:
                raise CannotEvaluate(f"occurrences(): item lacks {node['field']!r}")
            if it[node["field"]] == want:
                n += 1
        return n
    if op == "minutes_between":
        a = _ts(_eval(node["a"], scopes), "minutes_between() first argument")
        b = _ts(_eval(node["b"], scopes), "minutes_between() second argument")
        return _minutes(a, b)
    if op == "month_end_of":
        return _month_end_of(_ts(_eval(node["a"], scopes), "month_end_of()"))
    if op == "month_end_following":
        return _month_end_following(_ts(_eval(node["a"], scopes), "month_end_following()"))
    # -- boolean nodes
    if op == "exists":
        try:
            return _present(_resolve_path(node["a"], scopes))
        except CannotEvaluate:
            return False           # the ONE lawful missing->False
    if op == "contains":
        items = _list_at(node["a"], scopes, "contains()")
        return _eval(node["b"], scopes) in items
    if op in ("subset", "same_set"):
        a = {_hashable(v, op) for v in _list_at(node["a"], scopes, op + "()")}
        b = {_hashable(v, op) for v in _list_at(node["b"], scopes, op + "()")}
        return a <= b if op == "subset" else a == b
    if op == "every":
        items = _list_at(node["a"], scopes, "every()")
        verdicts, cannot = [], None
        for it in items:
            try:
                verdicts.append(bool(_eval(node["b"], scopes + [it if isinstance(it, dict) else {"value": it}])))
            except CannotEvaluate as e:
                cannot = cannot or e
        if cannot:
            raise cannot
        return all(verdicts)
    if op == "every_pair":
        items = _list_at(node["a"], scopes, "every_pair()")
        verdicts, cannot = [], None
        for prev, nxt in zip(items, items[1:]):
            try:
                verdicts.append(bool(_eval(node["b"], scopes + [{"prev": prev, "next": nxt}])))
            except CannotEvaluate as e:
                cannot = cannot or e
        if cannot:
            raise cannot
        return all(verdicts)
    if op == "within":
        anchor = _ts(_eval(node["a"], scopes), "anchor")
        end = _done_or_as_of(node["b"], scopes)
        bound = node["bound"]
        if bound["unit"] == "bd":
            return _business_days(anchor, end) <= bound["v"]
        return _minutes(anchor, end) <= bound["v"]
    if op == "by":
        deadline = _ts(_eval(node["a"], scopes), "deadline")
        return _done_or_as_of(node["b"], scopes) <= deadline
    if op == "not":
        return not _eval(node["a"], scopes)
    if op == "and":
        return bool(_eval(node["a"], scopes)) and bool(_eval(node["b"], scopes))
    if op == "or":
        return bool(_eval(node["a"], scopes)) or bool(_eval(node["b"], scopes))
    if op == "implies":
        return (not _eval(node["a"], scopes)) or bool(_eval(node["b"], scopes))
    if op in _CMP:
        return _cmp(op, _eval(node["a"], scopes), _eval(node["b"], scopes))
    raise ValueError(f"unknown node {op!r}")


_AST_CACHE: dict[str, dict] = {}


def evaluate(check: dict, record: dict) -> str:
    """One check against one record -> PASS | <action> | CANNOT-EVALUATE.
    A predicate that does not parse raises ValueError (the battery reports it)."""
    src = check["predicate"]
    ast = _AST_CACHE.get(src)
    if ast is None:
        ast = _AST_CACHE[src] = compile_predicate(src)
    try:
        ok = _eval(ast, [record])
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
                               "fixtures_run": 0, "no_model_violations": no_model_scan(),
                               "hatches": []}
    for yml in sorted(CHECKS_DIR.glob("SV-*.check.yml")) if CHECKS_DIR.exists() else []:
        cid = yml.name.split(".")[0]
        try:
            check = load_check_yml(yml)
        except Exception as e:  # noqa: BLE001
            results["broken"].append(f"{cid}: unparseable yml ({e})")
            continue
        problems: list[str] = check_schema_problems(cid, check)
        if "impl" in check:
            results["hatches"].append(cid)
        if "predicate" in check:
            try:
                compile_predicate(str(check["predicate"]))
            except ValueError as e:
                problems.append(f"predicate does not parse: {e}")
        fdir = FIXTURES_DIR / cid
        fixtures = sorted(fdir.glob("*.json")) if fdir.exists() else []
        for fx in fixtures:
            try:
                data = json.loads(fx.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                problems.append(f"{fx.name}: invalid JSON ({e})")
                continue
            want = data.get("expect")
            by_name = ("PASS" if fx.name.startswith("pass") else
                       "CANNOT-EVALUATE" if fx.name.startswith("cannot") else
                       str(check.get("action", "flag")).upper())
            if want != by_name:
                problems.append(f"{fx.name}: expect field {want!r} disagrees with naming law {by_name!r}")
            elif not any(p.startswith("predicate does not parse") for p in problems):
                got = evaluate(check, data.get("record", {}))
                if got != want:
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


# ---------------------------------------------------------------- selftest
def selftest() -> list[str]:
    """The DSL against known-good and known-bad inputs (law D11's spirit: an engine
    proven against fixtures it must reject). Returns failures; empty = green."""
    fails: list[str] = []
    H = {"action": "hold"}

    def case(pred: str, record: dict, want: str) -> None:
        try:
            got = evaluate({**H, "predicate": pred}, record)
        except ValueError as e:
            got = f"PARSE-ERROR({e})"
        if got != want:
            fails.append(f"{pred!r} on {json.dumps(record)}: got {got}, want {want}")

    def bad(pred: str) -> None:
        try:
            compile_predicate(pred)
        except ValueError:
            return
        fails.append(f"{pred!r} should not parse")

    # v0 core
    case("count(x) <= 1", {"x": [1]}, "PASS")
    case("count(x) <= 1", {"x": [1, 2]}, "HOLD")
    case("count(x) <= 1", {}, "CANNOT-EVALUATE")
    case("count(a[k]) <= 1", {"a": {"KI-L": ["o1"]}, "k": "KI-L"}, "PASS")
    case("count(a[k]) <= 1", {"a": {"KI-L": ["o1"]}, "k": "KI-R"}, "CANNOT-EVALUATE")
    # exists: blank is absent, explicit zero is present
    case("exists(a.b)", {"a": {"b": ""}}, "HOLD")
    case("exists(a.b)", {"a": {"b": None}}, "HOLD")
    case("exists(a.b)", {"a": {"b": 0}}, "PASS")
    case("not exists(a.b)", {"a": {}}, "PASS")
    # connectives, left-to-right, stop when determined
    case("a == 1 and b == 2", {"a": 1, "b": 2}, "PASS")
    case("a == 1 and b == 2", {"a": 1, "b": 3}, "HOLD")
    case("a == 1 and b == 2", {"a": 2}, "HOLD")
    case("a == 1 and b == 2", {"a": 1}, "CANNOT-EVALUATE")
    case("a == 1 or b == 2", {"a": 1}, "PASS")
    case("a == 1 or b == 2", {"a": 2, "b": 2}, "PASS")
    case("a == 1 or b == 2", {"a": 2}, "CANNOT-EVALUATE")
    case("not exists(s) or minutes_between(s, t) >= 0", {}, "PASS")
    case("a == 'yes' implies exists(b)", {"a": "no"}, "PASS")
    case("a == 'yes' implies exists(b)", {"a": "yes"}, "HOLD")
    case("a == 'yes' implies exists(b)", {"a": "yes", "b": "x"}, "PASS")
    case("(a == 1 or b == 1) and c == 1", {"a": 0, "b": 1, "c": 1}, "PASS")
    case("not (a == 1 and b == 1)", {"a": 1, "b": 1}, "HOLD")
    # types: honesty, never coercion
    case("a == true", {"a": True}, "PASS")
    case("a == true", {"a": 1}, "CANNOT-EVALUATE")
    case("a == 1", {"a": "1"}, "CANNOT-EVALUATE")
    case("a == 1", {"a": None}, "CANNOT-EVALUATE")
    case("a != b", {"a": "x", "b": "y"}, "PASS")
    case("a == b", {"a": [1], "b": [1]}, "CANNOT-EVALUATE")
    # sets and lists
    case("contains(xs, 'b')", {"xs": ["a", "b"]}, "PASS")
    case("contains(xs, 'b')", {"xs": ["a"]}, "HOLD")
    case("contains(xs, 'b')", {"xs": "ab"}, "CANNOT-EVALUATE")
    case("subset(a, b)", {"a": [1, 2], "b": [1, 2, 3]}, "PASS")
    case("subset(a, b)", {"a": [4], "b": [1]}, "HOLD")
    case("same_set(a, b)", {"a": [1, 2], "b": [2, 1]}, "PASS")
    case("same_set(a, b)", {"a": [1], "b": [1, 2]}, "HOLD")
    case("distinct(xs) == 2", {"xs": ["a", "b", "a"]}, "PASS")
    case("count(items) - distinct(items, seq) == count(pairs)",
         {"items": [{"seq": 1}, {"seq": 2}, {"seq": 2}], "pairs": [[2]]}, "PASS")
    case("count(items) - distinct(items, seq) == count(pairs)",
         {"items": [{"seq": 1}, {"seq": 2}, {"seq": 2}], "pairs": []}, "HOLD")
    case("sum(xs, ml) == total", {"xs": [{"ml": 100}, {"ml": 250}], "total": 350}, "PASS")
    # quantifiers
    case("every(items, v >= 1)", {"items": [{"v": 1}, {"v": 2}]}, "PASS")
    case("every(items, v >= 1)", {"items": [{"v": 0}]}, "HOLD")
    case("every(items, v >= 1)", {"items": []}, "PASS")
    case("every(items, v >= 1)", {"items": [{"v": 1}, {}]}, "CANNOT-EVALUATE")
    case("every(items, v >= 1)", {"items": [{"v": 0}, {}]}, "CANNOT-EVALUATE")
    case("every(items, v >= floor)", {"items": [{"v": 5}], "floor": 3}, "PASS")
    case("every(items, p == 'yes' implies every(kids, exists(a)))",
         {"items": [{"p": "no", "kids": [{}]}, {"p": "yes", "kids": [{"a": 1}]}]}, "PASS")
    case("every(items, p == 'yes' implies every(kids, exists(a)))",
         {"items": [{"p": "yes", "kids": [{"a": ""}]}]}, "HOLD")
    segs = [{"start": "2026-01-01T10:00Z", "end": "2026-01-01T10:14Z"},
            {"start": "2026-01-01T10:15Z", "end": "2026-01-01T10:29Z"}]
    case("every_pair(segs, minutes_between(prev.end, next.start) == 1)", {"segs": segs}, "PASS")
    case("every_pair(segs, minutes_between(prev.end, next.start) == 1)",
         {"segs": [segs[0], {"start": "2026-01-01T10:16Z", "end": "2026-01-01T10:30Z"}]}, "HOLD")
    case("every_pair(segs, minutes_between(prev.end, next.start) == 1)", {"segs": segs[:1]}, "PASS")
    # time
    case("minutes_between(a, b) <= 24h", {"a": "2026-01-01T00:00Z", "b": "2026-01-02T00:00Z"}, "PASS")
    case("minutes_between(a, b) <= 24h", {"a": "2026-01-01T00:00Z", "b": "2026-01-02T01:00Z"}, "HOLD")
    case("minutes_between(a, b) <= 24h", {"a": "yesterday", "b": "2026-01-02T01:00Z"}, "CANNOT-EVALUATE")
    case("minutes_between(a, b) >= 0", {"a": "2026-01-01T00:00+00:00", "b": "2025-12-31T23:59Z"}, "HOLD")
    W = "within(anchor, done, 24h)"
    case(W, {"anchor": "2026-01-01T00:00Z", "done": "2026-01-01T20:00Z"}, "PASS")
    case(W, {"anchor": "2026-01-01T00:00Z", "done": "2026-01-02T00:01Z"}, "HOLD")
    case(W, {"anchor": "2026-01-01T00:00Z", "as_of": "2026-01-01T12:00Z"}, "PASS")
    case(W, {"anchor": "2026-01-01T00:00Z", "as_of": "2026-01-02T12:00Z"}, "HOLD")
    case(W, {"anchor": "2026-01-01T00:00Z", "done": "", "as_of": "2026-01-02T12:00Z"}, "HOLD")
    case(W, {"anchor": "2026-01-01T00:00Z"}, "CANNOT-EVALUATE")
    case(W, {"done": "2026-01-01T20:00Z"}, "CANNOT-EVALUATE")
    B = "within(anchor, done, 5bd)"        # 2026-01-05 is a Monday
    case(B, {"anchor": "2026-01-05T09:00Z", "done": "2026-01-12T17:00Z"}, "PASS")
    case(B, {"anchor": "2026-01-05T09:00Z", "done": "2026-01-13T08:00Z"}, "HOLD")
    case(B, {"anchor": "2026-01-05T09:00Z", "as_of": "2026-01-09T08:00Z"}, "PASS")
    M = "by(month_end_following(ref), done)"
    case(M, {"ref": "2026-03-14T10:00Z", "done": "2026-04-30T10:00Z"}, "PASS")
    case(M, {"ref": "2026-03-14T10:00Z", "done": "2026-05-01T00:30Z"}, "HOLD")
    case(M, {"ref": "2026-12-14T10:00Z", "done": "2027-01-31T10:00Z"}, "PASS")
    case(M, {"ref": "2026-03-14T10:00Z", "as_of": "2026-04-10T10:00Z"}, "PASS")
    case(M, {"ref": "2026-03-14T10:00Z"}, "CANNOT-EVALUATE")
    case("sum(xs, minutes_between(out_ts, in_ts)) <= 15h",
         {"xs": [{"out_ts": "2026-01-01T00:00Z", "in_ts": "2026-01-01T08:00Z"},
                 {"out_ts": "2026-01-01T10:00Z", "in_ts": "2026-01-01T18:00Z"}]}, "HOLD")
    # nested index paths
    case("m[f.id].rev == f.rev", {"m": {"F1": {"rev": "R5"}}, "f": {"id": "F1", "rev": "R5"}}, "PASS")
    case("m[f.id].rev == f.rev", {"m": {"F1": {"rev": "R5"}}, "f": {"id": "F1", "rev": "R4"}}, "HOLD")
    case("m[f.id] == 'x'", {"m": {"F1": "x"}, "f": {}}, "CANNOT-EVALUATE")
    # index by a quantified scalar: every named field must be present on the object
    case("every(req, exists(auth[value]))", {"req": ["a", "b"], "auth": {"a": 1, "b": "x"}}, "PASS")
    case("every(req, exists(auth[value]))", {"req": ["a", "b"], "auth": {"a": 1, "b": ""}}, "HOLD")
    case("every(req, exists(auth[value]))", {"req": ["a", "c"], "auth": {"a": 1}}, "HOLD")
    # v1.1: occurrences / month_end_of / within on an expression anchor
    O = "every(items, occurrences(items, seq, seq) == 1 or (contains(pairs, seq) and occurrences(items, seq, seq) == 2))"
    case(O, {"items": [{"seq": 1}, {"seq": 4}, {"seq": 4}], "pairs": [4]}, "PASS")
    case(O, {"items": [{"seq": 1}, {"seq": 1}, {"seq": 3}], "pairs": [4]}, "HOLD")
    case(O, {"items": [{"seq": 1}, {"tissue": "x"}], "pairs": []}, "CANNOT-EVALUATE")
    case("every(ms, exists(d) or occurrences(ms, f, f) == occurrences(ms, v, v))",
         {"ms": [{"f": "A", "v": "a1"}, {"f": "A", "v": "a2"}]}, "HOLD")
    case("every(ms, exists(d) or occurrences(ms, f, f) == occurrences(ms, v, v))",
         {"ms": [{"f": "A", "v": "a1"}, {"f": "B", "v": "b1"}]}, "PASS")
    E = "within(month_end_of(ref), done, 30d)"
    case(E, {"ref": "2025-12-30T04:00Z", "done": "2026-01-30T18:00Z"}, "PASS")
    case(E, {"ref": "2025-12-30T04:00Z", "done": "2026-01-31T18:00Z"}, "HOLD")
    case(E, {"ref": "2026-02-10T04:00Z", "as_of": "2026-03-20T00:00Z"}, "PASS")
    case(E, {"ref": "2026-02-10T04:00Z"}, "CANNOT-EVALUATE")
    case("minutes_between(a, b) == 0", {"a": "2026-08-20T08:40:00Z", "b": "2026-08-20T08:40:00+00:00"}, "PASS")
    # known-bad predicates must be refused, never guessed at
    for p in ("count(x)", "a == 1 blah", "within(a, b, 5bd", "5bd <= 3", "a ==", "every(xs)",
              "exists(a) == true", "a = 1", "and a == 1", "count(x) <= 1 or", "within(a, b, x)",
              "distinct(xs, a.b) == 1", "a == 1 implies b == 1 implies c == 1",
              "signoff.by == 'x'", "exists(a.next)", "occurrences(xs, by, 1) == 1", "a.prev == 1"):
        bad(p)
    return fails


# ---------------------------------------------------------------- fields fold
_TS_RX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _walk(value: Any, prefix: str, out: dict[str, set[str]]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, f"{prefix}.{k}" if prefix else k, out)
    elif isinstance(value, list):
        out.setdefault(prefix, set()).add("list")
        for v in value:
            _walk(v, prefix + "[]", out)
    else:
        if isinstance(value, bool):
            t = "bool"
        elif isinstance(value, (int, float)):
            t = "number"
        elif value is None or value == "":
            t = "blank"
        elif isinstance(value, str) and _TS_RX.match(value):
            t = "ts"
        else:
            t = "str"
        out.setdefault(prefix, set()).add(t)


def fields_markdown() -> str:
    """The record vocabulary the encoded checks read, folded from the fixtures
    (exact, not inferred): every leaf path, its observed types, the checks whose
    fixtures carry it. Deterministic - a fold, never authored (law A1 applied)."""
    paths: dict[str, dict[str, set[str]]] = {}     # path -> {"types": set, "checks": set}
    n_checks = n_fixtures = 0
    predicates: list[tuple[str, str, str]] = []
    for yml in sorted(CHECKS_DIR.glob("SV-*.check.yml")) if CHECKS_DIR.exists() else []:
        cid = yml.name.split(".")[0]
        try:
            check = load_check_yml(yml)
        except Exception:  # noqa: BLE001
            continue
        n_checks += 1
        predicates.append((cid, str(check.get("trigger", "?")), str(check.get("predicate", "?"))))
        fdir = FIXTURES_DIR / cid
        for fx in sorted(fdir.glob("*.json")) if fdir.exists() else []:
            try:
                data = json.loads(fx.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            n_fixtures += 1
            seen: dict[str, set[str]] = {}
            _walk(data.get("record", {}), "", seen)
            for p, types in seen.items():
                slot = paths.setdefault(p, {"types": set(), "checks": set()})
                slot["types"] |= types
                slot["checks"].add(cid)
    lines = ["# FIELDS - the record vocabulary the floor reads. Generated fold. DO NOT EDIT.",
             "Regenerate: `python floor/engine.py --fields --write` (gates.py G-FIELDS enforces).",
             "Folded from the fixtures, so it is exact for what the checks have been proven "
             "against and silent about anything else. Types are observed, not declared: "
             "ts = ISO-8601 timestamp, blank = null or empty string.",
             "",
             f"checks: {n_checks} | fixtures: {n_fixtures} | leaf paths: {len(paths)}",
             ""]
    by_obj: dict[str, list[str]] = {}
    for p in sorted(paths):
        by_obj.setdefault(p.split(".")[0].split("[")[0], []).append(p)
    for obj in sorted(by_obj):
        lines.append(f"## {obj}")
        lines.append("| path | observed types | carried by fixtures of |")
        lines.append("|---|---|---|")
        for p in by_obj[obj]:
            slot = paths[p]
            lines.append(f"| `{p}` | {', '.join(sorted(slot['types']))} | "
                         f"{', '.join(sorted(slot['checks']))} |")
        lines.append("")
    lines.append("## predicates")
    lines.append("| check | trigger | predicate |")
    lines.append("|---|---|---|")
    for cid, trig, pred in predicates:
        lines.append(f"| {cid} | {trig} | `{pred}` |")
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        f = selftest()
        print("\n".join(f) if f else "DSL selftest: green")
        sys.exit(1 if f else 0)
    if "--fields" in sys.argv:
        md = fields_markdown()
        if "--write" in sys.argv:
            FIELDS_MD.write_text(md, encoding="utf-8", newline="\n")
            print(f"wrote {FIELDS_MD.relative_to(ROOT).as_posix()}")
        else:
            print(md, end="")
        sys.exit(0)
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
              f"{len(r['broken'])} broken, {r['fixtures_run']} fixtures run, "
              f"{len(r['hatches'])} impl hatch(es)")
        if r["no_model_violations"]:
            print("NO-MODEL VIOLATIONS: " + "; ".join(r["no_model_violations"]))
    sys.exit(1 if (r["broken"] or r["no_model_violations"]) else 0)
