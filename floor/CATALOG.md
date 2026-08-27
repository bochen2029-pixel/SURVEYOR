# THE FLOOR CATALOG — v0.1
**Status: RECEIPTED `[H]`, UNENCODED.** Every check below was harvested from a working OPO quality program's own audit walkthrough (local corpus, line-referenced in `_local/harvest/`, which never ships). Layer tags are provisional until a second site's practice is compared: **L0** = mandated (citation pinned via crosswalk) · **L1** = quality-science invariant · **L2** = site-variant (the reference program's own rule; each site signs its own). Trigger: `W` on-write · `C` on-close-attempt · `K` continuous clock. Action: `hold` blocks close · `flag` annotates · `alarm` pre-breach.
**The R1-gate for this file: a quality director reads it cold and recognizes their own audit checklist.** Encoding order = the order below. Every check ships with passing AND failing fixtures before it counts as done.

## A · Identity & cross-document
- **SV-001** `L1·C·hold` Name/DOB agree across authorization ↔ DRE ↔ record ↔ document-of-gift.
- **SV-002** `L1·W·hold` Serology report identity (DOB, donor ID, draw time) matches the record entry.
- **SV-003** `L1·C·hold` Donor-band number matches recovery paperwork.
- **SV-004** `L0·C·hold` Two-identifier donor verification present (bedside nurse + hospital wristband + donor band).
- **SV-005** `L1·C·flag` Body-diagram annotations consistent with narrative notes (deterministic subset; semantic remainder → watch tier).

## B · Signatures, roster & attribution
- **SV-010** `L0·C·hold` ≥2 coordinator signatures + lab signature before HLA/ABO pages complete.
- **SV-011** `L0·C·hold` Donor-ID verification carries two distinct staff, both on the team-worksheet roster.
- **SV-012** `L0·C·hold` OR roster role requirements by donor type (anesthesiologist for brain-dead; circulator for DCD); every recovering physician signs.
- **SV-013** `L1·W·hold` Any late/second signature or post-completion edit requires a linked explanatory case note.
- **SV-014** `L1·system` True editor + timestamp recorded on every edit (attribution never freezes to the original author).
- **SV-015** `L0·C·hold` Authorization witness is hospital care-team, never recovering-organization staff.

## C · The clock lattice (all `K·alarm` unless noted; every clock declares its anchor field + citation)
- **SV-020** `L2` Chart audit begins ≤7 days post-recovery.
- **SV-021** `L2` Chart to processor ≤30 days (5–10 for fresh/OC).
- **SV-022** `L0` Potential disease-transmission notification ≤24h from receipt.
- **SV-023** `L0` Reactive serology to county epidemiology ≤24h.
- **SV-024** `L0` COVID test within 72h of cross-clamp (all donors); BAL for every lung donor.
- **SV-025** `L0` PT/INR within 12h of allocation start (liver).
- **SV-026** `L0` Hemodilution lookback windows: blood products 48h, crystalloids 1h; auto-computed from logged volumes/timestamps.
- **SV-027** `L1` Prep-to-incision interval ≤1h15m (cross-contamination flag).
- **SV-028** `L0` Refrigeration clocks: recovery-start 24h/15h rule by initial-cooling timing; cumulative out-of-refrigeration ≤15h, auto-summed from in/out events.
- **SV-029** `L0` TFO serology reuse only within 7 days, else redraw required.
- **SV-030** `L0` Donor feedback due 5 business days **anchored to organ-recovery time, not cross-clamp** (anchor-declaration is the check).
- **SV-031** `L0/L2` DDR due 60 days (OPTN) / 30 days (site buffer — L2 tightening of an L0 clock).
- **SV-032** `L0` DNR due month-end following referral month.
- **SV-033** `L0` Onsite response ≤1.5h of referral (CMS-linked; site-tightened from 2h).
- **SV-034** `L2` Offer cadence ≤30 min between offers, or a logged unstable-donor exception.
- **SV-035** `L2` Contract/license notice-deadline lookahead ≥120 days (generalized from a harvested near-miss).

## D · Revision & document control
- **SV-040** `L1·W·hold` Form revision in use equals current controlled revision at time of use (stale local copies blocked).
- **SV-041** `L1·W·hold` Quality documents held in draft until required approvals recorded.
- **SV-042** `L1·K·alarm` Regulator edition-change monitor: effective date vs audit window, with lead time (the audited-to-the-new-edition trap).
- **SV-043** `L0·W·hold` Training/competency current for the role performing the action, at action time.

## E · Sequence, logic & vocabulary
- **SV-050** `L0·C·hold` DRE branching completeness: parent=yes ⇒ required children non-blank.
- **SV-051** `L1·C·flag` Correction method: single line-through + initials + date; no overwrite/white-out (deterministic on structured data; image attachments → assist).
- **SV-052** `L0·W·hold` Controlled-vocabulary exact match on authorized categories (no paraphrase, no abbreviation).
- **SV-053** `L1·W·hold` No duplicate recovery sequence numbers (paired tib/fib exception).
- **SV-054** `L0·C·hold` Recovered tissue ⊆ authorized tissue.
- **SV-055** `L1·W·hold` Inspection timestamp ordering: pre-inspection precedes donor prep.
- **SV-056** `L1·W·hold` No backdating past a signoff (audit-trail sequence legality).
- **SV-057** `L1·C·hold` Flow-sheet continuity: segment start = prior end + 1 min; every vital field non-blank including explicit zero.
- **SV-058** `L0·C·hold` Donor ≤18 months ⇒ two DREs (donor + birth mother).
- **SV-059** `L0·W·hold` ABO type A/AB ⇒ subtype present or reason code.
- **SV-060** `L1·W·flag` ABO and serology draws must not share a timestamp (independence of draws).
- **SV-061** `L0·W·hold` Injection-site findings tagged medical vs non-medical (eligibility-relevant).
- **SV-062** `L1·design-law` No check's verification channel may be the field under correction.

## F · Reconciliation & allocation
- **SV-070** `L0·W·hold` **Single-active-primary-offer guard** — a second primary on an organ with an active primary cannot be recorded. *(The flagship: a reportable violation with no system check today, recovered by phone `[H]`.)*
- **SV-071** `L0·C·hold` Authorization record field-complete before allocation starts.
- **SV-072** `L0·C·hold` Phone authorization requires the attached voice recording before completion.
- **SV-073** `L1·C·flag` Cross-role specimen reconciliation: research-tab entries ↔ post-OR donor summary.
- **SV-074** `L2·W·flag` Centers on the perfusion-screening list present in the match run, or flagged.
- **SV-075** `L2·W·hold` Decline reasons structured, pre-classified disqualifying/non-disqualifying, auto-gating list status.
- **SV-076** `L2·W·flag` Bypassed centers suppressed until primary list exhausted.
- **SV-077** `L0·C·hold` Organ disposition code matches across organ-data page ↔ donor-summary page (feeds the registry).
- **SV-078** `L1·C·hold` Cross-processor result redistribution complete on shared cases (every processor on the case received every result).

## G · Release, CAPA & reporting hygiene
- **SV-080** `L0·C·hold` Tissue release gate: contamination = 0% and screening/recovery documentation complete before release record closes.
- **SV-081** `L1·W·hold` CAPA row completeness: owner, falsifiable expectation, horizon, expiry, inverse.
- **SV-082** `L1·K·auto` CAPA effectiveness check runs at horizon; unmet ⇒ auto-return to committee with data attached.
- **SV-083** `L1·W·hold` Risk-register entries at/above priority threshold carry owner + review date.
- **SV-084** `L0·K·alarm` QAPI plan annual governing-board presentation clock.
- **SV-085** `L1·C·flag` Reports mixing metric variants (e.g., "organ donor" vs "CMS organ donor") without naming the denominator are flagged.

---
*59 checks (count enforced by `_build/gates.py` G-CATALOG — the first number in this repo a machine corrected). Deterministic, every one currently performed by a person, weeks later, on a sample. Encoding order is this order; SV-070 is first among equals. A check without fixtures is a sentence, not a check.*
