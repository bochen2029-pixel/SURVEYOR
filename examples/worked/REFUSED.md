# The drafts that were refused

**This is the most useful file in the kit, and it is the one most projects would delete.**

A worked example that shows only the finished artifact teaches a harness to produce something that
*looks* finished. What actually transfers is the shape of the refusals — what was wrong, what the
gate said about it, and why the fix is not "phrase it better."

Everything here is fictional. **The refusals are real, and re-run on every gate pass:**

```bash
python conformance/run.py
```

Each draft declares the class it must be refused as, in its own `refusal:` field.
`conformance/run.py` re-derives the refusal from the check and compares. A narration nobody
re-runs decays into fiction, so this file is graded against the engine rather than trusted.

**Read the last section first if you read only one.** Five of these six are mechanical. The sixth
is the one a competent harness produces most confidently, and the kit catches it only because the
draft *declared* enough for it to be caught.

---

## 01 · Restating a rule the mandated seed already carries

`rejected/01-restates-the-mandate.check.yml` — refused as **`duplicates-a-mandated-check`**

A site-authored check asserting that the two ABO determinations must come from separately drawn
samples. It is well-formed. It is *true*. Its predicate is byte-identical to SV-060's.

**Why it is wrong.** OPTN Policy 2.6.A already requires it, SV-060 already encodes it, and the
crosswalk already pins the clause. Mounting this creates **a second, divergent copy of the law** —
one that lives in your L2 layer, drifts when the policy moves, and disagrees with the seed without
anyone noticing which copy is stale. The mandated half ships identical to everyone precisely so
that it can be corrected in one place.

**The fix is not to reword it.** It is to delete it and, if your programme adds something the
policy does not require (a tighter interval between the two draws, say), write *that* difference as
the check, tagged `L2`, with the mandated clause named in its `authority` as the floor it sits on.

## 02 · A check that fires where it does not apply

`rejected/02-fires-on-the-empty-record.check.yml` — refused as **`fires-on-the-empty-record`**

```
fires (HOLD) on an empty record - the check needs an applicability gate:
a leading path read that raises when its subject is absent
```

A transport cooler-log check whose every condition is an `exists()`. On a record with no transport
block at all — an organ case that never shipped, a register, a referral — `exists()` reads absence
as False and the check **holds every record in the building.**

**Why it is wrong.** A check whose subject is absent must ABSTAIN, never fire. This is not a style
preference: it is the difference between a census floor and alert fatigue, and it is invisible to
hand-written fixtures because a fixture is always written *for* its check. This project shipped two
such defects and found them only when a generator produced records the checks had never seen.

**The fix.** Lead with a path read that raises when the subject is missing —
`transport.mode != '' and exists(transport.cooler_log_ref) and ...`. `transport.mode` on a record
with no transport raises, the verdict is CANNOT-EVALUATE, and the check is silent where it does not
belong.

## 03 · A predicate that does not parse

`rejected/03-unparseable-predicate.check.yml` — refused as **`predicate-does-not-parse`**

```
predicate does not parse: expected a field name, got 'by' (reserved words cannot name fields)
```

`exists(transport.handoff.by)`. The DSL has a `by()` clock primitive, so `by` cannot name a field.

**Why this is in the list at all.** It is the least interesting failure and the most common, and it
is here to make a point about the parser: it refuses rather than guesses. A DSL that quietly
accepted `handoff.by` would have to decide what it meant, and a rule engine that decides what you
meant is a rule engine you cannot audit. Rename the field `signed_by` — which is what every other
check in the catalog already calls it, and the vocabulary is in `floor/FIELDS.md`.

## 04 · Authoring the mandated layer

`rejected/04-authors-a-mandated-element.check.yml` — refused as **`authors-a-mandated-layer`**

A donor-eligibility check, tagged `L0`, quoting 21 CFR 1271.50 correctly.

**Why it is wrong, and it is not the citation.** The citation is fine. The *layer* is not yours.
L0 is mandated policy and L1 is quality-science invariant; both ship identical to every site, from
the seed, cited and reviewed. **This kit authors L2 and L3 only** (SPEC §10). A completion that
needs an L0 element is a completion this kit refuses — and the refusal is the feature, because the
alternative is fifty programmes each holding a slightly different private copy of federal law.

**What to do instead.** If the seed is genuinely missing a mandated element, that is a finding
against the seed. Say so, name the clause, and stop. Do not fill it locally. (This draft also fires
on the empty record, so it fails twice — the engine reports every objection, not the first.)

## 05 · Verifying a correction through the field being corrected

`rejected/05-verifies-through-the-corrected-field.check.yml` — refused as
**`verification-channel-is-the-corrected-field`**

A contact-number correction, confirmed by contacting the corrected number.

**Why it is wrong.** This is the authentication deadlock, abstracted from a harvested anti-pattern:
the bank that texts the *old* number to authorise changing the number. If the field is wrong, the
channel is wrong, and the check confirms the error against itself. Law B5 exists for exactly this,
and the catalog encodes it as SV-062 — a floor check whose *subject is a check definition*.

**How it was caught, which is the part worth noticing.** `conformance/run.py` runs **SV-062 against
this draft**, using the same engine that runs every other check. The floor refuses the check with a
check. But it can only do that because the draft **declared** `corrects_field:` and
`verification_fields:`. A draft that declares neither passes here unexamined, and the conformance
report says so rather than implying coverage it does not have. **Declare them.** The cost is two
lines; the alternative is a deadlock nobody can unlock from inside.

## 06 · A check with no failing fixture

`rejected/06-no-failing-fixture.check.yml` — refused as **`no-failing-fixture`**

A specimen-count reconciliation with one passing fixture and nothing else.

**Why it is wrong.** A check without a fixture that *fails* has never been shown to catch anything.
It may be inverted, it may reference a field that is always absent, it may be a tautology — a
passing fixture distinguishes none of those. **A check without fixtures is a sentence, not a
check.** Ship at least one `pass_*` and one `fail_*`, and a `cannot_*` if the check can encounter a
record it cannot judge, which is most of them.

Note that **all five drafts above also fail this one.** That is not padding: it is what the first
draft of a check looks like, and it is why the rule is mechanical rather than advisory.

---

## What the refusals have in common

Four of the six are *well-formed, true, and wrong* — and that is the whole lesson. A harness
producing plausible artifacts is the expected condition, not a malfunction, so the containment has
to be mechanical:

| the draft was refused by | and it is enforced by |
|---|---|
| duplicating a mandated check | comparing the predicate against the whole seed |
| firing where it does not apply | evaluating every check against the empty record |
| a predicate that does not parse | a parser that refuses rather than guesses |
| authoring L0 | a layer tag the kit will not accept |
| verifying through the corrected field | **a floor check run against the check** |
| shipping without a failing fixture | the battery's naming law |

**And GREEN still mounts nothing.** Every one of these could pass every gate and still not enter
your floor, because mounting is a human signature and there is no code path around it.
