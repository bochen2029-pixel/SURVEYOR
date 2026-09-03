#!/usr/bin/env python3
"""experiments/f-fixture/run.py - F-FIXTURE arm A: the floor vs the synthetic OPO world.

Runs every encoded check over every generated record, compares with the ground truth
the generator owns, prints the tables, writes RESULTS.md (a fold: deterministic in the
seed and sizes), exits non-zero on a kill condition (SPEC section 12):
  - any planted deterministic defect PASSes;
  - clean-record false-hold rate above 1 percent.
Grains are named in PREDICTIONS.md and repeated in the output. Funerals print.

CLI: python experiments/f-fixture/run.py [--seed S] [--cases N] [--plants K] [--out DIR] [--write-results]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "floor"))
sys.path.insert(0, str(HERE))
import engine  # noqa: E402
import generate  # noqa: E402

RESULTS_MD = HERE / "RESULTS.md"
PREDICTIONS_MD = HERE / "PREDICTIONS.md"
NON_PASS = {"HOLD", "FLAG", "ALARM"}


def load_checks() -> dict[str, dict]:
    return {p.name.split(".")[0]: engine.load_check_yml(p) for p in sorted(engine.CHECKS_DIR.glob("SV-*.check.yml"))}


def verdicts(checks: dict[str, dict], record: dict) -> dict[str, str]:
    return {cid: engine.evaluate(c, record) for cid, c in checks.items()}


def catalog_hash(checks: dict[str, dict]) -> str:
    h = hashlib.sha256()
    for cid in sorted(checks):
        h.update((engine.CHECKS_DIR / f"{cid}.check.yml").read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def grade(seed: int, n_cases: int, k_plants: int) -> dict:
    t0 = time.perf_counter()
    checks = load_checks()
    rows = generate.corpus(seed, n_cases, k_plants)
    res = {"seed": seed, "n_cases": n_cases, "k_plants": k_plants, "catalog_hash": catalog_hash(checks),
           "records": len(rows), "clean_records": 0, "plants": 0,
           "clean_pairs": 0, "false_holds": [], "cannot_by_check": Counter(), "evaluable_by_check": Counter(),
           "coverage_by_variant": defaultdict(lambda: [0, 0]),
           "caught": 0, "abstained": [], "missed": [], "collateral": [], "by_check": {}}
    for row in rows:
        v = verdicts(checks, row["record"])
        if row["clean"]:
            res["clean_records"] += 1
            evaluable = [cid for cid, x in v.items() if x != "CANNOT-EVALUATE"]
            res["clean_pairs"] += len(evaluable)
            cov = res["coverage_by_variant"][row["variant"]]
            cov[0] += len(evaluable)
            cov[1] += 1
            for cid, x in v.items():
                if x == "CANNOT-EVALUATE":
                    res["cannot_by_check"][cid] += 1
                else:
                    res["evaluable_by_check"][cid] += 1
                    if x in NON_PASS:
                        res["false_holds"].append({"corpus_id": row["corpus_id"], "variant": row["variant"], "check": cid, "verdict": x})
        else:
            res["plants"] += 1
            plant = row["plants"][0]
            cid = plant["check"]
            expect = str(checks[cid].get("action", "flag")).upper()
            got = v[cid]
            entry = res["by_check"].setdefault(cid, {"expect": expect, "caught": 0, "abstained": 0, "missed": 0})
            if got == expect:
                res["caught"] += 1
                entry["caught"] += 1
            elif got == "CANNOT-EVALUATE":
                res["abstained"].append({"corpus_id": row["corpus_id"], "check": cid, "how": plant["how"]})
                entry["abstained"] += 1
            else:
                res["missed"].append({"corpus_id": row["corpus_id"], "check": cid, "how": plant["how"], "got": got})
                entry["missed"] += 1
            base_v = verdicts(checks, row["base_record"])
            for other, x in v.items():
                if other != cid and x in NON_PASS and base_v.get(other) == "PASS":
                    res["collateral"].append({"corpus_id": row["corpus_id"], "plant": cid, "check": other, "verdict": x})
    res["false_hold_rate"] = (len(res["false_holds"]) / res["clean_pairs"]) if res["clean_pairs"] else 0.0
    res["seconds"] = round(time.perf_counter() - t0, 2)
    res["kill"] = []
    if res["missed"]:
        res["kill"].append(f"{len(res['missed'])} planted defect(s) PASSED")
    if res["false_hold_rate"] > 0.01:
        res["kill"].append(f"false-hold rate {res['false_hold_rate']:.2%} exceeds 1%")
    res["rows"] = rows
    return res


SWEEP_SEEDS = (20260903, 7, 991, 4242, 13, 20261231, 555, 88)


def sweep(seeds=SWEEP_SEEDS, cases: int = 120, plants: int = 3) -> list[dict]:
    """The same battery over several worlds. A single seed establishes that the floor
    caught THAT world's plants; the robustness claim needs more than one, and the S10
    cold-start audit found that claim attached to a single-seed result in the file
    addressed to foreign harnesses. Now it is computed and printed."""
    out = []
    for s in seeds:
        r = grade(s, cases, plants)
        out.append({"seed": s, "plants": r["plants"], "caught": r["caught"],
                    "missed": len(r["missed"]), "abstained": len(r["abstained"]),
                    "clean_pairs": r["clean_pairs"], "false_holds": len(r["false_holds"]),
                    "rate": r["false_hold_rate"], "kill": r["kill"]})
    return out


def render(res: dict, sweep_rows: list[dict] | None = None) -> str:
    pred_hash = hashlib.sha256(PREDICTIONS_MD.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16] if PREDICTIONS_MD.exists() else "absent"
    L = ["# F-FIXTURE arm A - RESULTS (generated fold; regenerate with run.py --write-results)",
         f"seed {res['seed']} | cases {res['n_cases']} | plants per check {res['k_plants']} | catalog {res['catalog_hash']} | predictions {pred_hash} | {res['seconds']} s",
         "", "## Verdict",
         ("**KILLED:** " + "; ".join(res["kill"])) if res["kill"] else "**ALIVE:** no planted defect passed; false-hold rate within the 1% kill line.",
         "", "## Numbers (grain named)",
         "| measure | value | grain |", "|---|---|---|",
         f"| plants | {res['plants']} | one planted record per (check, variant), {res['k_plants']} per check |",
         f"| caught | {res['caught']} ({res['caught'] / res['plants']:.1%}) | named check returned its declared action |",
         f"| abstained | {len(res['abstained'])} ({len(res['abstained']) / res['plants']:.1%}) | named check returned CANNOT-EVALUATE |",
         f"| missed | {len(res['missed'])} | named check returned PASS - the kill |",
         f"| clean records | {res['clean_records']} | donor cases, referrals, registers |",
         f"| clean pairs | {res['clean_pairs']} | (clean record, evaluable check) |",
         f"| false holds | {len(res['false_holds'])} ({res['false_hold_rate']:.2%}) | clean pairs with HOLD/FLAG/ALARM |",
         f"| collateral | {len(res['collateral'])} ({len(res['collateral']) / res['plants']:.2f} per plant) | other checks flipped PASS -> non-PASS on a plant |",
         ""]
    cov = res["coverage_by_variant"]
    L += ["## Evaluable coverage by record variant", "| variant | records | evaluable checks per record (of 59) |", "|---|---|---|"]
    for k in sorted(cov):
        pairs, n = cov[k]
        L.append(f"| {k} | {n} | {pairs / n:.1f} ({pairs / n / 59:.0%}) |")
    L += ["", "## Plants by check", "| check | expect | caught | abstained | missed |", "|---|---|---|---|---|"]
    for cid in sorted(res["by_check"]):
        e = res["by_check"][cid]
        L.append(f"| {cid} | {e['expect']} | {e['caught']} | {e['abstained']} | {e['missed']} |")
    if res["missed"]:
        L += ["", "## FUNERAL - planted defects the floor passed", "| corpus id | check | the plant | got |", "|---|---|---|---|"]
        L += [f"| {m['corpus_id']} | {m['check']} | {m['how']} | {m['got']} |" for m in res["missed"]]
    if res["abstained"]:
        L += ["", "## Abstains on plants (CANNOT-EVALUATE where a catch was expected)", "| corpus id | check | the plant |", "|---|---|---|"]
        L += [f"| {m['corpus_id']} | {m['check']} | {m['how']} |" for m in res["abstained"]]
    if res["false_holds"]:
        L += ["", "## False holds on clean records", "| corpus id | variant | check | verdict |", "|---|---|---|---|"]
        L += [f"| {m['corpus_id']} | {m['variant']} | {m['check']} | {m['verdict']} |" for m in res["false_holds"][:60]]
        if len(res["false_holds"]) > 60:
            L.append(f"| ... | | {len(res['false_holds']) - 60} more | |")
    if res["collateral"]:
        pairs = Counter((c["plant"], c["check"]) for c in res["collateral"])
        L += ["", "## Collateral firings (plant check -> other check), distinct pairs", "| plant | other check | count |", "|---|---|---|"]
        L += [f"| {p} | {o} | {n} |" for (p, o), n in sorted(pairs.items())]
    if sweep_rows:
        tot_p = sum(r["plants"] for r in sweep_rows)
        tot_c = sum(r["caught"] for r in sweep_rows)
        tot_m = sum(r["missed"] for r in sweep_rows)
        tot_cp = sum(r["clean_pairs"] for r in sweep_rows)
        tot_fh = sum(r["false_holds"] for r in sweep_rows)
        L += ["", "## The sweep - the same battery over several worlds", "",
              "*One seed establishes that the floor caught THAT world's plants. The robustness "
              "claim needs more than one, so it is computed here rather than remembered.*", "",
              "| seed | plants | caught | missed | clean pairs | false holds | rate | verdict |",
              "|---|---|---|---|---|---|---|---|"]
        for r in sweep_rows:
            L.append(f"| {r['seed']} | {r['plants']} | {r['caught']} | {r['missed']} | "
                     f"{r['clean_pairs']:,} | {r['false_holds']} | {r['rate']:.2%} | "
                     f"{'KILLED: ' + '; '.join(r['kill']) if r['kill'] else 'alive'} |")
        L.append(f"| **{len(sweep_rows)} seeds** | **{tot_p}** | **{tot_c}** | **{tot_m}** | "
                 f"**{tot_cp:,}** | **{tot_fh}** | **{tot_fh / tot_cp if tot_cp else 0:.2%}** | "
                 f"**{'KILLED' if tot_m or tot_fh / max(tot_cp,1) > 0.01 else 'alive'}** |")
        L.append("")
    L += ["", "## Checks that never evaluate on a clean record (registers or event-conditional)",
          ", ".join(cid for cid in sorted(res["cannot_by_check"]) if res["evaluable_by_check"][cid] == 0) or "none", ""]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--cases", type=int, default=200)
    ap.add_argument("--plants", type=int, default=5)
    ap.add_argument("--out", default=None, help="directory for corpus.jsonl (large; gitignored)")
    ap.add_argument("--write-results", action="store_true")
    ap.add_argument("--sweep", action="store_true", help="also run the battery over several seeds")
    a = ap.parse_args()
    res = grade(a.seed, a.cases, a.plants)
    rows = sweep() if a.sweep else None
    md = render(res, rows)
    print(md)
    if a.write_results:
        RESULTS_MD.write_text(md, encoding="utf-8", newline="\n")
        print(f"wrote {RESULTS_MD.relative_to(ROOT).as_posix()}")
    if a.out:
        d = Path(a.out)
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "corpus.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for row in res["rows"]:
                row = {k: v for k, v in row.items() if k != "base_record"}
                f.write(json.dumps(row) + "\n")
        print(f"wrote {d / 'corpus.jsonl'}")
    return 1 if res["kill"] else 0


if __name__ == "__main__":
    sys.exit(main())
