# AGENTS.md — the boot contract

**You are an AI harness. This file is addressed to you.**

It is also read by the people who will review what you were told, so it is written to be defensible
to both. Read it completely before you read anything else here, and before you write anything at
all.

This repository assumes you are **competent, well-intentioned, and sometimes confidently wrong** —
and that the third property cannot be trained away, so it has to be contained. Nothing here is a
slight. The containment is the product, and most of it is aimed at failures this project has
already committed and caught, which are listed rather than hidden.

---

## §0 · Run this before you believe anything below

```bash
python conformance/run.py
```

It reports what is actually here. **Trust its output over this file**, which was reconciled at one
commit and will drift. If it disagrees with a sentence below, the sentence is the defect.

## §1 · What state this is in

Six of ten build rungs are green, graded by twelve gates that run on every session close
(`python _build/gates.py`). Established, and you may rely on it:

- **59 of 59 catalog checks encoded**, 283 fixtures, every check carrying a pass, a fail and —
  where it can meet a record it cannot judge — a `cannot` fixture.
- **The floor is model-free and it is checked**, not asserted: `floor/`, `clocks/`, `ledger/` and
  `crosswalk/` are scanned for network and model imports on every gate run.
- **F-FIXTURE has printed** `[M 2026-09-03]`: 295 planted nonconformities, 295 caught, 0 missed,
  0 false holds in 8,967 clean (record, check) pairs, across 8 seeds. Pre-registered in
  `experiments/f-fixture/PREDICTIONS.md` **before** the first run; receipt in `RESULTS.md`. The
  first run **failed** on a 4.01% false-hold rate and printed two real defects. Read that file.
- **46 citations byte-match sha256-pinned public sources**, covering 39 of 59 checks
  (`python crosswalk/pins.py --check`). A quote that does not match does not exist.
- **The three folds and the Morning Board are deterministic**: the same tape renders byte-identical
  documents, including under reordering of simultaneous events.

**Not established, and the reasons are not equivalent — read this twice.** Two rungs cannot be run
here at all: **F-RETRO** needs a real programme's historical charts, and **F-CROSSWALK** needs a
real regulatory edition transition plus that site's controlled documents. Their mechanical halves
are green and recorded; the deciders are NOT-RUN and the ladder says so rather than flattering us.
**Every number on `site/surveyor.html` is a real read of a SYNTHETIC tape** and the page says so in
generated text. Do not quote it as a site's numbers.

Six checks rest on AATB standards, which are licensed and cannot be pinned or redistributed. Their
authority is honestly unpinned; the survey binder prints "not pinned" rather than a paraphrase.

## §2 · Which job you are here to do

| If your operator asked you to… | Go to |
|---|---|
| **complete the fit** for a specific programme | §3–§6. This is the normal case. |
| **extend the seed itself** — encode a catalog check, add a gate, port an organ | §7 |

## §3 · What you may author, and what you may not

| Layer | Content | May you write it? |
|---|---|---|
| **L0** | Mandated: federal rule, OPTN policy, state statute | **No.** Ships from the seed, cited. |
| **L1** | Quality-science invariants | **No.** Ships from the seed. |
| **L2 / L3** | This programme's fit: its numbers, its variants, its adapters | **Yes. Only this.** |
| **L4** | The quality record — findings, variances, signatures | **Never.** People write it. |

A completion that requires an L0 or L1 element is a completion this kit **refuses**. Say so, name
the clause, and stop. See `examples/worked/REFUSED.md` §04, which is that refusal run against the
real gate.

## §4 · The four laws you are most likely to break

These are not the whole constitution — that is `LAWS.md`, twenty-seven laws, one screen each, and
you should read it. These four are the ones a competent harness breaks anyway.

1. **A check whose subject is absent must ABSTAIN, never fire.** Lead a family-specific check with
   a path read that raises when its subject is missing. This project shipped two checks that
   violated it and found them only when a generator produced records they had never seen.
   Enforced: every check is evaluated against the empty record.
2. **A quote that does not byte-match its pinned source does not exist.** And a claim that a
   regulation is *silent* is checked the same way: `crosswalk/pins.py` runs every search term you
   record. This project recorded five terms it had run one of, and was wrong about the regulation.
   Search **phrases**, not words.
3. **Feedback lands on the case, never on a person.** There is no notify-person primitive in the
   floor and no field for one in the record vocabulary. Do not add either. Roles, never names —
   names live only in `_local/`, which never ships.
4. **A check without a failing fixture is a sentence, not a check.** Ship `pass_*`, `fail_*`, and
   `cannot_*` where the check can meet a record it cannot judge.

## §5 · How to complete a fit

1. Read `elicit/method.md`, then work `elicit/questions.yml`. One question per variation point,
   keyed to the checks tagged `L2`, `L0/L2` or `L1/L2` — conformance fails if the catalog grows one
   and the question set does not. **Interview the material, not the coordinators.**
2. Read `examples/worked/REFUSED.md` before you write a check. It is the half that transfers.
3. Write `floor/checks/SV-xxx.check.yml` plus its fixtures. `floor/FIELDS.md` is the exact record
   vocabulary the encoded checks read — a generated fold, not a maintained document. If your answer
   needs a field that is not there, **that gap is the finding**, and it belongs in the conversation
   rather than in a guess.
4. Run `python conformance/run.py` and `python _build/gates.py`. Both green, or you are not done.
5. **Stop.** GREEN mounts nothing. A human signature is the only way across, and there is no code
   path around it.

## §6 · What you must not do

- **Fill a blank.** A missing field arrives missing. The third state exists for this: a check that
  cannot judge says CANNOT-EVALUATE. Substituting a default converts an honest silence into a false
  pass, and it always looks like helpfulness.
- **Weaken a gate to make it pass.** Nothing currently stops you (law D11 names this openly). Any
  diff touching `_build/gates.py` requires a tape `decision` event saying why. If a gate is wrong,
  say so on the tape with the evidence — that has happened, and the gate was corrected.
- **Hand-edit a fold.** `_build/STATE.md`, `_build/BOARD.md`, `floor/FIELDS.md`,
  `experiments/f-fixture/RESULTS.md` and the board block in `site/surveyor.html` are generated.
  Editing them is a build error and G-FOLD will catch it.
- **Write a name, a site identity, or a vendor product name outside `_local/`.**

## §7 · If you are extending the seed

Read `BOOT.md` — the seven-step session ritual — then `LAWS.md` in full, then `_build/STATE.md` for
the next action and the open questions. The tape is the truth, the folds are its face, the gates
are its teeth, and your job is to leave one more check green than you found.

Two habits this project learned the hard way and you should inherit: **bank your predictions before
you run the test** (`experiments/f-fixture/PREDICTIONS.md` was written before the generator existed,
and the first run falsified it — which is the outcome that taught us the most), and **when a
document and a dated receipt disagree, the receipt wins and the document is the defect.** Several
files here carry corrections that were made that way, including corrections to corrections.
