# F-RETRO — PRE-REGISTRATION (v0.1 · FROZEN BEFORE BUILD)
**The flagship decider: the retro-audit race.** Run the floor against historical closed charts and
score it against the quality team's own findings log. Publishes whatever it prints — including the
funeral. **Thresholds below are frozen with the site's quality director BEFORE the run; blanks are
filled at freeze time, then this file is hash-pinned and never edited (amendments append).**

## Design
- **Dataset:** N = ___ quarters of closed charts (target ≥4), on site, local hardware, zero egress.
  PHI never leaves the building; this file reports only aggregates.
- **Arms:** (A) the encoded floor catalog (`floor/*.check.yml`, hash-pinned set listed at freeze);
  (B) `[NULL-1]` the site's existing sampled human audit (the historical findings log itself);
  (C) `[NULL-2]` a naive checklist cron (same checks, no hold semantics, no anchors, end-of-week batch).
- **Ground truth:** the historical findings log, plus a blinded adjudication panel (quality staff)
  for surplus candidates and precision sampling.

## Metrics (grain named)
1. **Recall** — fraction of historical findings (per finding, deterministic-eligible subset declared
   at freeze) reproduced by the floor at entry-time. Threshold: ≥ ____ %.
2. **Precision** — fraction of floor holds/flags adjudicated as real on a random sample of ____ .
   Threshold: ≥ ____ %.
3. **Surplus** — adjudicated-real findings from the census that the sampled audit never saw
   (count + rate per 100 charts). No threshold — reported; this is the census dividend.
4. **Hours per case** — audit labor before vs. after, measured by the site's own accounting.
   Reported; no threshold.
5. **False-hold burden** — holds on clean records per 100 charts. Threshold: ≤ ____ .

## Kill conditions
- Recall or precision below frozen thresholds → **the catalog encoding is defective or the thesis
  is wrong; funeral prints with the per-check breakdown.**
- NULL-2 (naive cron) matches arm A within ____ % on all metrics → the hold-semantics and anchor
  machinery are decoration; strip to the cron and say so.
- Deterministic-eligible subset < ____ % of the historical findings log → the "mostly mechanical"
  premise `[H]` is wrong at this site; report the true split.

## Preconditions
- G-CLOCK registrability battery passes on the export (clock jitter masquerades as findings).
- Anchor-field inventory signed off by quality staff (the feedback-clock anchor error is a known
  historical mode — it must not be reproduced in the fixture).
- Adjudication panel blinded to which arm produced each candidate.

## Publication
Aggregates, per-check families, and the funerals (if any) publish on the SURVEYOR page and in
`docs/receipts/` with dates. Per-chart and per-person data never leave the site. The page's
number-boxes remain "illustrative" until this file's results section is appended.

*Freeze signature (quality director): ____________  Date: ________  Catalog hash: ________*
