# SURVEYOR — THE SPEC
### Quality, rebuilt into the record. The verification half of the estate, promoted to a product.
**v0.1 · 2026-08-26 · REV 0 — NOTHING HAS RUN.** Claim grammar, binding on every statement in this repository: `[M]` measured, dated receipt · `[H]` harvested — line-referenced from the local passport corpus (`_local/harvest/`, never ships) · `[D]` derived, chain shown · `[SPEC]` designed, unbuilt · `[BET]` kill condition named · `[NULL]` the baseline it must beat. A number without grain, denominator, and source is not a number. Funerals print. Where this spec and a receipt disagree, the receipt wins and the spec is the defect.

---

## §0 · One breath

Every OPO is federally required to run a QAPI program (42 CFR 486.348) and staffs it as a **department** that audits a *sample* of records, *weeks* after the cases, and becomes survey-ready as an *event*. The harvest proved what the profession already suspects: nearly everything that department checks is deterministic, precisely specified, and performed by hand `[H]`. SURVEYOR moves those checks into the record itself — **census, at the keystroke, as a standing property** — keeps the crosswalk the quality manager asked for by name `[H]`, makes corrective actions grade their own effectiveness, and reserves human judgment for the part that is judgment. The #1 headache (the EDR) and the #2 headache (quality) are two costs of one missing object: **a record that verifies itself.** REGISTRAR ships the record; SURVEYOR is its verification machinery, given its own name, able to run beside *any* record system.

## §1 · The headline design decision — a check is a patch

SURVEYOR introduces **no new algebra**. A floor check is a **patch row in the REGISTRAR/Cordis algebra**: typed, sourced, hash-pinned, **expiring by default**, carrying its **inverse**, mounted only under signature, unwound by disposer. Consequences, inherited rather than re-proven:

- **T1–T3 (lift, composition, retirement)** apply to check sets: a site's quality fit is a monoid product of check rows; retiring a check provably unwinds it; a wrong check is reversible, not scar tissue.
- **Theorem 80 (confluence)** applies to fit evolution: whatever order checks are mounted, revised, and retired, the settled fit is the one a from-scratch load would produce — reconfiguration is schedule-independent.
- **T4 (agent-independent reachability)** applies to completion: whatever harness authors a site's checks, only states that retire to the seed are reachable; safety is a property of the fence, not the author.
- The **gate battery, L-SIGN, the state switch, and the two-model split** are inherited from REGISTRAR unchanged (§10, §11).

One sentence for the whole section: **SURVEYOR is REGISTRAR's gate battery given a standing life, generalized to any record, with quality-profession semantics.**

## §2 · Scope and non-goals

**In scope:** deterministic verification of operational records at entry and continuously (the Floor); deadline arithmetic (the Clocks); regulation↔policy mapping with pinned citations (the Crosswalk — **day one, by operator ruling**); the append-only quality ledger and its generated documents (the Ledger & Folds); CAPA lifecycle with automatic effectiveness grading; variance intake and triage *as an investigation aid*; historical inheritance (SCRIPTORIUM-class intake); cited memory (CORTEX-class). **Gated, opt-in, separately pre-registered:** the present-tense Watch (§8) and the Field tier (§9).

**Non-goals, permanent:** grading/ranking/scoring people · filing regulatory reports or contacting any agency, registry, or surveyor · writing the quality record (findings enter under a human name) · auto-applying any change (policy diff, CAPA, configuration — everything mounts under signature) · clinical decisions of any kind · replacing the record system (SURVEYOR reads **beside** incumbents via adapters; it reads REGISTRAR natively) · any egress of site data.

## §3 · Architecture — five organs, one tape, one inheritance

```
                       ┌─────────────────────────────────────────────┐
  incumbent record ─┐  │  02 CROSSWALK   public regs ⇄ site policy   │←─ frontier (public side only)
  (adapters/)       │  ├─────────────────────────────────────────────┤
  REGISTRAR native ─┼─▶│  01 FLOOR    checks-as-patches, at entry    │
  SCRIPTORIUM       │  │  03 CLOCKS   the SLA lattice (tropical STN) │──▶ THE TAPE (append-only,
  (inheritance) ────┘  │  04 LEDGER   CAPA · variance · folds        │    hash-chained, local)
                       │  05 WATCH    present-tense (gated, off)     │──▶ FOLDS: line-of-sight ·
                       │  ·· FIELD    PARALLAX tier (gated, off)     │    committee packet ·
                       └─────────────────────────────────────────────┘    survey binder
        body: dsh/Cordis — every organ, check, adapter, and fold is a plugin with a disposer
        heart (watch tier only): FUSOR resident loop · memory: CORTEX (every answer cites)
```

Everything is a plugin; there is no privileged core to patch; registrations are effects that unwind. Two profiles, one body: **forge** (completion machinery; strict-superset check keeps it out of production) and **steward** (the running system). One switch: `surveyor.state = off | shadow | live` — a file only the operator writes, per organ, failing toward inert. At `off`, SURVEYOR is still a very good deterministic audit engine and a crosswalk; every ambitious surface degrades to a useful ordinary one.

## §4 · The data plane — tape, registration, preconditions

- **The tape:** append-only, hash-chained event log (SQLite WAL or JSONL, local). Event types: `record_event` (normalized from the source system), `check_result`, `hold`, `release`, `finding` (human-authored), `variance`, `capa`, `capa_check`, `crosswalk_change`, `surfacing`, `silence` (a held emission, with margin — silence is auditable), `mount`, `retire`, `signature`. Every event carries provenance (source system, extractor, timestamp authority).
- **Normalization:** adapters map incumbent exports to an object-centric event form (case, donor, chart-page, document, staff-role — roles, not names, wherever the check permits).
- **Precondition G-CLOCK `[D from the estate's measured registration results]`:** timestamp jitter masquerades as everything — sequence violations, SLA breaches, distortions. Before any organ runs against a source, SURVEYOR runs a clock-integrity battery (cross-system offset estimation, jitter bound, anchor-field inventory) and prints a registrability verdict. **Registration precedes verification, as a gate, not a footnote.**

## §5 · The Floor — checks as patches, at entry `[SPEC; catalog RECEIPTED [H]]`

**Rule form (`floor/*.check.yml`):**

```yaml
id: SV-070
title: single-active-primary-offer guard
family: reconciliation
layer: L1              # L0 mandated | L1 invariant | L2 site-variant
authority: "OPTN allocation policy (cite pinned in crosswalk map)"
trigger: on_write      # on_write | on_close_attempt | continuous
predicate: "count(active_primary_offers[organ_id]) <= 1"
action: hold           # hold (blocks close/act) | flag (annotates) | alarm (clock breach)
message: "A primary offer is already active on this organ (see {offer_ref})."
evidence: [offer_ref]  # every result links its evidence
expires: P2Y           # every check re-earns its place
inverse: retire        # unmount is total; disposer-unwound
tests: fixtures/sv-070/*.json   # every check ships with passing AND failing fixtures
```

**Laws of the floor:** (1) **Deterministic and model-free** — the floor must pass its full battery with every learned component disabled; any learned tier must beat the floor or it does not ship. (2) **Feedback lands on the case, never on a person** — no check pings a coordinator; a check that punishes charting suppresses charting `[H: the Goodhart quote]`. (3) **Hold semantics:** a held record is open work, not a finding; it converts to a finding only if it survives to close-attempt. (4) **Every check declares its authority class** — mandated (L0, citation-pinned), invariant (L1, quality-science), or site-variant (L2, the site's own rule, signed by the site). (5) The verification channel of a check may never be the field under correction `[H: the deadlock anti-pattern]`. The initial catalog — **59 checks harvested from a working quality program's own audit walkthrough** (count verified mechanically by `_build/gates.py` G-CATALOG) — lives in [`floor/CATALOG.md`](floor/CATALOG.md); encoding it is build rung 02.

## §6 · The Clocks — the SLA lattice as a temporal network `[SPEC; engine exists in REGISTRAR [M]]`

Every deadline is a constraint between **anchored events**: `min/max interval(anchor_a, anchor_b)`. The lattice is a Simple Temporal Network; consistency ⟺ no negative cycle; closure computed in the (min,+) tropical semiring, integer minutes, exactly associative — bit-identical under parallel evaluation, which is the same property that makes the tape replayable. **The engine is REGISTRAR's floor, re-aimed.** Spec-level rule from a harvested failure mode: **every clock declares its anchor field with a citation** (the 5-business-day feedback clock anchors to *organ-recovery time*, not cross-clamp `[H]`); an SLA computed from the wrong anchor is a defect the fixture battery must catch. Alarms fire *before* breach with configurable lead; every alarm and every satisfied deadline lands on the tape.

## §7 · The Crosswalk — day one, by operator ruling `[SPEC]`

**The demand is receipted:** the reference site's quality leadership abandoned a manual policy↔regulation crosswalk as unmaintainable and asked, verbatim, for machinery that reads regulations against policies — with the PHI constraint stated in the same breath `[H]`.

- **Sources registry** (`crosswalk/sources.yml`): OPTN policies, 42 CFR (eCFR), FDA 21 CFR 1271, AATB standards, state additions — each with fetch cadence, version identity, and **byte-pinning**: every stored clause carries `sha256(source_bytes)`; a quoted span is admissible only if it byte-matches its pinned source. **A quote that doesn't match doesn't exist.**
- **Mapping objects:** `reg_clause ↔ site_document_section`, typed (`implements | constrains | reports-under | silent`), each mapping itself a patch row (signed, expiring, inverse).
- **Diff lifecycle:** new edition detected → affected mappings computed → **draft diffs** generated against the site's controlled documents → human review queue → mount under signature or reject with reason. Never auto-applied. Lead-time alarms ride the Clocks (the audited-to-the-new-edition trap: effective date vs audit window `[H: the AATB 15th→16th case]`).
- **The split:** the public side (regulation reading, seed material) may use a frontier model — no PHI, no BAA, because nothing protected ever reaches it. The site side (SOPs, records) runs on the local model only. The line is structural.

## §8 · The Ledger, CAPA, and the Folds `[SPEC]`

- **CAPA row:** `id · variance_class · owner · expectation {metric, baseline, target, horizon, resolve_by} · expiry · inverse · status`. **PDSA is the lifecycle:** Plan = draft+expectation · Do = shadow · Study = grade · Act = mount under signature or retire with the reason printed. At `horizon`, the effectiveness check runs automatically: expectation met → `sustained` `[H: the department's own phrase]`; not met → **auto-returned to committee with the data attached.** No CAPA closes by assertion.
- **Variance triage:** intake → the three-way discriminator (coverage / novelty / distortion — *was anyone in a position to know; did the world change; does one source systematically disagree*) → an **investigation packet**, drafted for humans. Output is an aid, never a verdict; system-vs-person separation is the mechanical content of Just Culture.
- **The folds:** the monthly line-of-sight report `[H]`, the QAPI committee packet, the annual governing-board review, and the **survey binder** are deterministic folds over the tape — generated, current, every claim linked to its evidence events. The books close continuously.

## §9 · The gated tiers

- **The Watch `[SPEC+BET]`:** a standing resident (FUSOR socket) over the case stream, judging at boundaries whether *this instant* deserves surfacing — the closing window, the cross-page contradiction, the silence where a lab should be. Condition-grain (birth–surface–resolve), refractory, with every hold written to the tape with its margin. Inherits the estate's measured impossibility result for threshold alerting and its measured repair (judgment in weights) — **transfer to this distribution is a BET with a pre-registered kill.** Ships `off`; must beat the floor-plus-cron `[NULL]` at matched catch to earn `shadow`.
- **The Field:** the PARALLAX tier — per-seat/per-handoff structure reading — is **out of scope for v0.x** except as pre-registered elsewhere; if it ever mounts here it inherits PARALLAX's entire consent architecture: subject reads their own number first; use-without-show; no machine path from a lens to a verdict about a person.

## §10 · Layers and completability — the REGISTRAR motion

| Layer | Content | Authored by | Machine path? |
|---|---|---|---|
| **L0** | Mandated QAPI spine: 486.348, OPTN performance monitoring, outcome measures **with denominators** (incl. the known external-source caveat) | Clean-room, cited, ships in seed | **No** |
| **L1** | Quality-science invariants: SPC, sampling, calibration; two-person verification (the first-corroborator law, already in OPTN policy); the check families | Seed | **No** |
| **L2/L3** | The site's fit: which checks mount, site-variant rules, thresholds, adapters, document mappings | **The site**, via its own harness reading the kit, under the gate battery | Authors L2/L3 **only**; L-SIGN to mount |
| **L4** | The quality record: findings, variances, CAPAs, signatures | **People** | **Never** |

**The kit:** `AGENTS.md` (boot contract for any foreign harness) · `elicit/` (the question set, seeded from the harvest's pain ledger, abstracted to role level — one question per variation point, each naming which artifact in the site's own building answers it) · `floor/CATALOG.md` + fixtures · worked examples **including the REFUSED half** (an elicitation the kit declines because it would require authoring L0/L1) · `adapters/` contracts. **The gate battery** (inherited, quality-tuned): schema, blast radius, citation byte-match, fixture pass/fail including planted-defect detection, denominator reconstruction, three-state honesty (a check reports PASS / FAIL / CANNOT-EVALUATE — never silence). RED names the defect in words; nothing mounts on RED; GREEN still mounts nothing — **a human signature is the only way across.**

## §11 · Security & privacy

Local model (9B–27B class, quantized) on one workstation-class machine; **zero egress; air-gapped supported**. Frontier touches public material only (§7). PHI never leaves the building; roles not names in every artifact the checks permit; the tape is exportable in full by the site (open formats, no license server, no vendor in the loop). The harvest corpus (`_local/`) is **git-ignored, never ships, and is the only place site-specific material may live.**

## §12 · The deciders `[BET — pre-registered before build]`

| ID | Test | Dies if |
|---|---|---|
| **F-FIXTURE** | Synthetic OPO world with planted nonconformities (shared machinery with the estate's fixture battery); floor must catch 100% of planted deterministic defects and hold nothing clean | any planted defect passes, or >1% clean-record false-hold rate on the fixture |
| **F-RETRO** — the flagship | Floor vs. the quality team's historical findings log on N quarters of closed charts, on site, zero egress. Metrics: **recall** (their findings reproduced at entry-time), **precision** (sampled adjudication), **surplus** (adjudicated-real census findings the sample missed), **hours/case**. Thresholds frozen with the quality director *before* the run: [`experiments/f-retro/PREREG.md`](experiments/f-retro/PREREG.md) | recall or precision below the frozen thresholds; publishes either way |
| **F-CROSSWALK** | One real edition change (the AATB edition transition is the natural fixture `[H]`) diffed against site policies, graded against quality staff's own manual reading | misses a material change, or floods immaterial ones past the frozen precision floor |
| **F-WATCH gate** | The watch vs. floor+cron `[NULL]` at matched catch on shadow data | the null matches it — the funeral is the watch's, **and the floor alone is the product** |
| **R1-gate** | A quality director reads `floor/CATALOG.md` cold and recognizes their own audit checklist | they don't — the spine is wrong and nothing above it matters |

Standing nulls: the existing sampled human audit; a naive checklist cron. Standing honesty: if the deterministic floor captures nearly everything retrospective review finds, that is not a failure of the product — **that is the product.**

## §13 · Build order — backwards from the mockup (`site/surveyor.html`)

| Rung | Deliverable | Executioner |
|---|---|---|
| 00 | This repo skeleton, spec, catalog, prereg stubs | G-COLDSTART (fresh-agent audit orients from repo alone; the human R1-gate stays in §12) |
| 01 | Tape + floor engine (check loader, hold/flag/alarm, fixtures runner) on synthetic data | F-FIXTURE |
| 02 | Catalog v1 encoded (59 checks as `*.check.yml` + fixtures) | F-FIXTURE, per check |
| 03 | Clocks engine (STN closure, anchor declarations) — port from REGISTRAR floor | fixture battery + anchor-defect plants |
| 04 | **F-RETRO on historical charts** (on site, local) | F-RETRO — the first real number |
| 05 | Crosswalk MVP (sources registry, pinning, mapping objects, one edition diff) | F-CROSSWALK |
| 06 | Ledger + CAPA lifecycle + the three folds | fold determinism (same tape → byte-identical documents) |
| 07 | The Morning Board (make `site/surveyor.html`'s mock real against the tape) | every line links to evidence, or the line doesn't render |
| 08 | Watch tier in `shadow` | F-WATCH gate |
| 09 | Kit hardening: `elicit/`, worked examples incl. REFUSED, adapters | gate battery on a foreign harness's completion |

**Nothing advances a rung while its executioner is red.** The public page (`site/surveyor.html`) updates only from receipts; its number-boxes stay illustrative-and-labeled until rung 04 prints.

## §14 · Repo layout

```
C:\SURVEYOR\
  SPEC.md              this file
  README.md            identity + pointers + the no-ask line
  .gitignore           excludes _local/
  floor/               CATALOG.md · *.check.yml · fixtures/
  clocks/              STN engine port · anchor registry
  crosswalk/           sources.yml · pins/ · mappings/ · diffs/
  ledger/              tape schema · folds/ (line-of-sight, packet, binder)
  watch/               gated tier (empty until rung 08)
  field/               pointer to PARALLAX prereg; empty by policy
  adapters/            incumbent-system contracts (REGISTRAR native)
  elicit/              the question set (from the pain ledger, role-level)
  experiments/f-retro/ PREREG.md · runner (rung 04)
  site/                surveyor.html — the end-product mockup, build target
  docs/                ONE-PAGER_v0.1.md · future receipts
  _local/              NEVER SHIPS: harvest corpus, site-specific notes
```

## §15 · Open questions, honest

1. **The denominator problem:** CMS outcome denominators derive from external death data — the one number no fold over the site's own tape can produce; the binder must import and mark it. 2. **Adapter friction:** incumbent vendors charge for change (`[H]` "every little change costs us money"); the adapter contract must survive export-only, read-only, worst-case CSV. 3. **L0/L1 vs L2 adjudication per check:** the catalog tags are provisional until a second site's practice is compared — the jurisdiction-rows economics (a check is worth little to its author, a great deal to the other 54) starts at check #1. 4. **Site-variant semantics drift:** the same check name may mean different predicates at different OPOs; the kit's elicitation must surface this, not paper over it. 5. **The watch's corpus:** condition-grain training data for OPO quality moments exists nowhere yet; the tape generates it — but only after rungs 01–04 run.

## §16 · The line

*The half that is law ships identical to everyone. The half that is yours is completed in your building, by your people and their own AI, and mounted only under your signature. A check is a patch; a CAPA is an expectation with a deadline; silence is on the record; the survey binder is a fold. Quality was never a department — it was the record's missing property. Ship the property; give the department back its judgment; be survey-ready every day.*
