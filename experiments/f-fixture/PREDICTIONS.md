# F-FIXTURE arm A — PREDICTIONS (banked 2026-09-03, before any run)
**The synthetic OPO world vs. the encoded floor. This file is written before `generate.py` or `run.py`
has been executed once; its sha256 is recorded on the tape as a `mount` in the same breath. Amendments
append below the line; nothing above it is edited after the first run. Where a prediction and the printed
result disagree, the result wins and the prediction is the defect.**

## What is being tested
- **Subject:** the 59 encoded checks (`floor/checks/`, catalog hash on the tape at the run) evaluated by the
  deterministic floor engine, with every learned component off (there are none).
- **Instrument:** `experiments/f-fixture/generate.py` — a seeded, stdlib-only generator of an OPO case
  world in the `floor/FIELDS.md` vocabulary: donor cases (organ, tissue, both; brain-dead and DCD; completed
  and in-progress snapshots), referrals, and the registers the release/CAPA family reads. Every record it
  emits as `clean` is authored to satisfy every applicable check; every record it emits as a `plant` is a
  clean record with exactly one authored nonconformity and the check that should catch it named as ground
  truth. The generator owns the truth; the floor does not see it.
- **Grader:** `experiments/f-fixture/run.py` — runs all 59 checks over every record, compares with ground
  truth, prints the tables, writes `RESULTS.md`, exits non-zero on a kill condition.

## Grains (named before the numbers exist)
- **Plants:** one planted record per (check, variant), K variants per check; N_p = 59 × K.
- **Clean pairs:** every (clean record, check) pair where the check is *evaluable* (verdict is not
  CANNOT-EVALUATE); a check that does not apply to a record kind abstains and is not a pair.
- **False hold:** a clean pair whose verdict is HOLD, FLAG or ALARM.
- **Caught:** a plant whose named check returns its declared action. **Abstained:** returns
  CANNOT-EVALUATE. **Missed:** returns PASS.
- **Collateral:** on a planted record, any *other* check whose verdict moved from PASS on the base clean
  record to HOLD/FLAG/ALARM on the plant.

## Predictions (one line each, with the falsifier)
| # | Claim | Predicted | Falsified if |
|---|---|---|---|
| P1 | Missed plants (a planted defect the floor PASSES) | **0** | any plant PASSes — the SPEC §12 kill |
| P2 | Caught plants | ≥ 97% of N_p | < 97% |
| P3 | Abstained plants | ≤ 3% of N_p, all of them cases where the plant blanks a field the predicate reads before it reaches the defect | any abstain that is not of that shape |
| P4 | False-hold rate on clean pairs | ≤ 0.2% | > 1% — the SPEC §12 kill; > 0.2% is a funeral for this prediction only |
| P5 | Where false holds come from, if any | calendar edges: business days across weekends (SV-030), month-end plus 30 days (SV-032), minute-granularity ordering (SV-055, SV-057) | a false hold anywhere else |
| P6 | Collateral firings | mean ≤ 0.10 per plant; at most 3 distinct (plant check, collateral check) pairs | > 0.25 per plant or > 5 pairs |
| P7 | Evaluable coverage on a complete organ+tissue donor case | 70–85% of the 59 checks are evaluable (the rest are registers, referral-only or event-conditional) | < 60% or > 90% |
| P8 | Runtime, N = 200 donor cases + registers + 59×5 plants, stdlib, one core | < 30 s | ≥ 60 s |
| P9 | The number nobody predicted | there will be at least one check whose *clean* verdict depends on the generator's interpretation of an anchor the catalog leaves implicit (the modelling already found one: SV-028's refrigeration clock starts at asystole, which for a brain-dead donor is cross-clamp, not the declaration of death) | the run finds none besides SV-028 |

## Kill conditions (from SPEC §12, restated)
- Any planted deterministic defect PASSes → the catalog encoding is defective; the funeral prints the check
  and the record.
- Clean-record false-hold rate > 1% → the floor holds clean work; the funeral prints the checks.

## What is NOT tested here
Customers 2–5 of the estate roadmap (PARALLAX F-JACOBIAN-LITE, F-TWIN, F-BETA, oracle-v2) need an org layer
(seats, handoffs, testimony) this repo does not specify; no PARALLAX checkout exists on this machine. This
generator emits the *case stream*; an org layer can be built on it later, and its predictions belong to it.

---
*Amendments append below this line, dated, never above.*
