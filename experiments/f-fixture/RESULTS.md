# F-FIXTURE arm A - RESULTS (generated fold; regenerate with run.py --write-results)
seed 20260903 | cases 200 | plants per check 5 | catalog 24ffe1087e04b010 | predictions bd867f554bb3330b | 0.94 s

## Verdict
**ALIVE:** no planted defect passed; false-hold rate within the 1% kill line.

## Numbers (grain named)
| measure | value | grain |
|---|---|---|
| plants | 295 | one planted record per (check, variant), 5 per check |
| caught | 295 (100.0%) | named check returned its declared action |
| abstained | 0 (0.0%) | named check returned CANNOT-EVALUATE |
| missed | 0 | named check returned PASS - the kill |
| clean records | 400 | donor cases, referrals, registers |
| clean pairs | 8967 | (clean record, evaluable check) |
| false holds | 0 (0.00%) | clean pairs with HOLD/FLAG/ALARM |
| collateral | 5 (0.02 per plant) | other checks flipped PASS -> non-PASS on a plant |

## Evaluable coverage by record variant
| variant | records | evaluable checks per record (of 59) |
|---|---|---|
| both/brain_dead/complete | 51 | 48.3 (82%) |
| both/brain_dead/snapshot | 8 | 47.1 (80%) |
| both/dcd/complete | 34 | 48.2 (82%) |
| both/dcd/snapshot | 7 | 47.0 (80%) |
| capa | 20 | 3.0 (5%) |
| check_definition | 20 | 2.0 (3%) |
| contracts | 20 | 2.0 (3%) |
| document | 20 | 2.0 (3%) |
| organ/brain_dead/complete | 30 | 42.1 (71%) |
| organ/brain_dead/snapshot | 5 | 41.0 (69%) |
| organ/dcd/complete | 10 | 42.0 (71%) |
| organ/dcd/snapshot | 5 | 41.0 (69%) |
| qapi | 20 | 2.0 (3%) |
| referral | 40 | 3.0 (5%) |
| report | 20 | 2.0 (3%) |
| risk | 20 | 2.0 (3%) |
| standards | 20 | 2.0 (3%) |
| tissue/tissue/complete | 45 | 32.1 (54%) |
| tissue/tissue/snapshot | 5 | 32.0 (54%) |

## Plants by check
| check | expect | caught | abstained | missed |
|---|---|---|---|---|
| SV-001 | HOLD | 5 | 0 | 0 |
| SV-002 | HOLD | 5 | 0 | 0 |
| SV-003 | HOLD | 5 | 0 | 0 |
| SV-004 | HOLD | 5 | 0 | 0 |
| SV-005 | FLAG | 5 | 0 | 0 |
| SV-010 | HOLD | 5 | 0 | 0 |
| SV-011 | HOLD | 5 | 0 | 0 |
| SV-012 | HOLD | 5 | 0 | 0 |
| SV-013 | HOLD | 5 | 0 | 0 |
| SV-014 | FLAG | 5 | 0 | 0 |
| SV-015 | HOLD | 5 | 0 | 0 |
| SV-020 | ALARM | 5 | 0 | 0 |
| SV-021 | ALARM | 5 | 0 | 0 |
| SV-022 | ALARM | 5 | 0 | 0 |
| SV-023 | ALARM | 5 | 0 | 0 |
| SV-024 | ALARM | 5 | 0 | 0 |
| SV-025 | ALARM | 5 | 0 | 0 |
| SV-026 | HOLD | 5 | 0 | 0 |
| SV-027 | ALARM | 5 | 0 | 0 |
| SV-028 | ALARM | 5 | 0 | 0 |
| SV-029 | ALARM | 5 | 0 | 0 |
| SV-030 | ALARM | 5 | 0 | 0 |
| SV-031 | ALARM | 5 | 0 | 0 |
| SV-032 | ALARM | 5 | 0 | 0 |
| SV-033 | ALARM | 5 | 0 | 0 |
| SV-034 | ALARM | 5 | 0 | 0 |
| SV-035 | ALARM | 5 | 0 | 0 |
| SV-040 | HOLD | 5 | 0 | 0 |
| SV-041 | HOLD | 5 | 0 | 0 |
| SV-042 | ALARM | 5 | 0 | 0 |
| SV-043 | HOLD | 5 | 0 | 0 |
| SV-050 | HOLD | 5 | 0 | 0 |
| SV-051 | FLAG | 5 | 0 | 0 |
| SV-052 | HOLD | 5 | 0 | 0 |
| SV-053 | HOLD | 5 | 0 | 0 |
| SV-054 | HOLD | 5 | 0 | 0 |
| SV-055 | HOLD | 5 | 0 | 0 |
| SV-056 | HOLD | 5 | 0 | 0 |
| SV-057 | HOLD | 5 | 0 | 0 |
| SV-058 | HOLD | 5 | 0 | 0 |
| SV-059 | HOLD | 5 | 0 | 0 |
| SV-060 | HOLD | 5 | 0 | 0 |
| SV-061 | HOLD | 5 | 0 | 0 |
| SV-062 | HOLD | 5 | 0 | 0 |
| SV-070 | HOLD | 5 | 0 | 0 |
| SV-071 | HOLD | 5 | 0 | 0 |
| SV-072 | HOLD | 5 | 0 | 0 |
| SV-073 | FLAG | 5 | 0 | 0 |
| SV-074 | FLAG | 5 | 0 | 0 |
| SV-075 | HOLD | 5 | 0 | 0 |
| SV-076 | FLAG | 5 | 0 | 0 |
| SV-077 | HOLD | 5 | 0 | 0 |
| SV-078 | HOLD | 5 | 0 | 0 |
| SV-080 | HOLD | 5 | 0 | 0 |
| SV-081 | HOLD | 5 | 0 | 0 |
| SV-082 | ALARM | 5 | 0 | 0 |
| SV-083 | HOLD | 5 | 0 | 0 |
| SV-084 | ALARM | 5 | 0 | 0 |
| SV-085 | FLAG | 5 | 0 | 0 |

## Collateral firings (plant check -> other check), distinct pairs
| plant | other check | count |
|---|---|---|
| SV-071 | SV-015 | 5 |

## The sweep - the same battery over several worlds

*One seed establishes that the floor caught THAT world's plants. The robustness claim needs more than one, so it is computed here rather than remembered.*

| seed | plants | caught | missed | clean pairs | false holds | rate | verdict |
|---|---|---|---|---|---|---|---|
| 20260903 | 177 | 177 | 0 | 5,493 | 0 | 0.00% | alive |
| 7 | 177 | 177 | 0 | 5,484 | 0 | 0.00% | alive |
| 991 | 177 | 177 | 0 | 5,484 | 0 | 0.00% | alive |
| 4242 | 177 | 177 | 0 | 5,485 | 0 | 0.00% | alive |
| 13 | 177 | 177 | 0 | 5,492 | 0 | 0.00% | alive |
| 20261231 | 177 | 177 | 0 | 5,490 | 0 | 0.00% | alive |
| 555 | 177 | 177 | 0 | 5,486 | 0 | 0.00% | alive |
| 88 | 177 | 177 | 0 | 5,492 | 0 | 0.00% | alive |
| **8 seeds** | **1416** | **1416** | **0** | **43,906** | **0** | **0.00%** | **alive** |


## Checks that never evaluate on a clean record (registers or event-conditional)
none

