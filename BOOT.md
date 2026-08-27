# BOOT — read this first, every session, no exceptions
**You are a session in a weeks-long build. You inherit no memory. Everything you need is in this repo; everything you do must survive you. Total boot budget: ~10 minutes, ~15K tokens. Do not soak the whole repo.**

## The seven steps

1. **Read [`LAWS.md`](LAWS.md)** — all of it (one screen per law). These are binding. If you are about to violate one, stop and file a `question` on the tape instead.
2. **Read the folds:** [`_build/STATE.md`](_build/STATE.md) (next action, rung ladder, open items) and [`_build/BOARD.md`](_build/BOARD.md). If STATE shows an **open session** that isn't yours: STOP — single-writer law (D8). Reconcile: read that session's tape events, close it honestly (`session_end` with what the tape shows actually happened), then proceed.
3. **Verify reality:** run `python _build/gates.py` (no --record). If anything FAILs that STATE claimed green, reality wins — your first task is reconciliation, on the tape.
4. **Open your session:** append one line to `_build/TAPE.jsonl`:
   `{"ts": "<utc-iso>", "session": "S<n>", "type": "session_start", "goal": "<one sentence>"}`
   Then read ONLY what your rung needs (SPEC section via its §-map; the organ's directory; never the whole repo). The harvest (`_local/harvest/`) is reference — cite as [H] with line refs; names never leave `_local/` (C1).
5. **Work in bankable quanta** (D2): default = one catalog check fully encoded (`floor/checks/SV-xxx.check.yml` + `floor/fixtures/SV-xxx/pass*` + `fail*`), gate green after each. Decisions → tape `decision` events (what/why/revert). Uncertain-but-reversible → decide, log, tag. Uncertain-and-irreversible → `question`/`blocker` on tape, move to the next independent quantum.
6. **Close on the tape** (D4): append `mount` events for what you built, your `session_end` with a **specific** `next` (executable by a stranger), then — **in this order** —
   `python _build/fold.py` (folds catch up with your appends) → `python _build/gates.py --record` (verdicts append + refold) → `git add -A && git commit`.
7. **Never** hand-edit STATE.md/BOARD.md (A1), touch `golden/` (D6), write a name outside `_local/` (C1), or advance a rung whose executioner is red (D1).

## Where things are
`SPEC.md` (the spec; read by section) · `floor/CATALOG.md` (the 59 checks = the work queue) · `experiments/f-retro/PREREG.md` (the flagship test; thresholds freeze before it runs) · `site/surveyor.html` (the target; numbers illustrative until rung 04) · `_build/` (tape, folds, gates — the discipline itself) · `_local/` (harvest + denylist; NEVER ships).

## The one sentence to keep
**The tape is the truth, the folds are its face, the gates are its teeth, and your job is to leave one more check green than you found.**
