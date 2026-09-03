#!/usr/bin/env python3
"""tools/publish_board.py - render the Morning Board into the product page, and deploy.

Lives in the repository, not in a scratch directory, because the S10 cold-start audit made
the point: the gate could only check the SHAPE of the published board (markers present,
rows carry an evidence element) and never that the board on the page was the one this tape
produces. It could not have detected the very staleness S8 recorded fixing — the live file
sat a week behind, still claiming zero of fifty-nine checks encoded. A gate can only
byte-compare against a renderer it can call, with parameters it shares.

BOARD_SEED and BOARD_CASES are those shared parameters. `_build/gates.py` imports them and
re-renders; the block between the markers must match byte for byte.

    python tools/publish_board.py            render, write the page, deploy with backups
    python tools/publish_board.py --check     report whether the page matches, write nothing

Every website file is backed up first, in the site's own convention
(`_backups/<name>.<date>_<time>_pre-<reason>.bak`).
"""
from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site" / "surveyor.html"
DEPLOY = (Path("C:/Websites/aorta-site/_upload/surveyor.html"),
          Path("C:/Websites/aorta-site/_staging-from-claude/surveyor.html"))

BOARD_SEED, BOARD_CASES = 20260903, 60
START, END = "2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z"
PROVENANCE = "SYNTHETIC TAPE - real reads of a generated record; F-RETRO has not run"

BEGIN = "<!-- BOARD:GENERATED begin - rendered by ledger/board.py; do not hand-edit -->"
END_MARK = "<!-- BOARD:GENERATED end -->"


def render() -> tuple[str, int, int, str]:
    """(fragment, lines, refused, tape id). Deterministic in the constants above."""
    for d in ("ledger", "floor", "crosswalk", "clocks", "experiments/f-fixture"):
        sys.path.insert(0, str(ROOT / d))
    import board as B
    import make_tape
    evs = make_tape.build(BOARD_SEED, BOARD_CASES)
    lines, dropped = B.build(evs, START, END)
    return (B.render_html(lines, dropped, evs, START, END, PROVENANCE),
            len(lines), len(dropped), B.tape_id(evs))


def block(fragment: str) -> str:
    return BEGIN + "\n" + fragment + "            " + END_MARK


def published(page: str) -> str | None:
    if BEGIN not in page or END_MARK not in page:
        return None
    return page[page.index(BEGIN): page.index(END_MARK) + len(END_MARK)]


def inject(page: str, fragment: str, tape: str) -> str:
    # the chrome's tape id is rewritten every run, or the chrome and the banner disagree
    page = page.replace("Tue &middot; 06:45", f"tape {tape}").replace("Tue \u00b7 06:45", f"tape {tape}")
    page = re.sub(r"<span>tape [0-9a-f]{8,32}</span>", f"<span>tape {tape}</span>", page)
    blk = block(fragment)
    if BEGIN in page:
        return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END_MARK), lambda _: blk, page, flags=re.S)
    m = re.search(r'( *<div class="board-note">.*?</div>\n)( *<div class="board-grid">.*?\n *</div>\n)'
                  r'( *<div class="board-foot">)', page, re.S)
    if not m:
        raise SystemExit("could not locate the hand-written board block to replace")
    return page[:m.start(1)] + "            " + blk + "\n" + page[m.start(3):]


def backup(p: Path, reason: str, stamp: str) -> None:
    if not p.exists():
        return
    d = p.parent / "_backups"
    d.mkdir(exist_ok=True)
    shutil.copy2(p, d / f"{p.name}.{stamp}_pre-{reason}.bak")


def main() -> int:
    fragment, n, refused, tape = render()
    page = SITE.read_text(encoding="utf-8")
    if "--check" in sys.argv:
        have = published(page)
        if have is None:
            print("the page carries no generated board")
            return 1
        if have.strip() == block(fragment).strip():
            print(f"page matches this tape ({n} lines, {refused} refused, tape {tape})")
            # The DEPLOYED copies live outside the repository, so no gate can reach them on
            # a stranger's machine - this is the honest half of the check, reported here
            # rather than pretended at by a gate. It is how the week-stale live file was
            # missed: the repository was right and the served file was not.
            for t in DEPLOY:
                if not t.exists():
                    print(f"  deploy target absent: {t}")
                elif t.read_text(encoding="utf-8") != SITE.read_text(encoding="utf-8"):
                    print(f"  DEPLOYED COPY IS STALE: {t} - run without --check to deploy")
                else:
                    print(f"  deployed copy matches: {t}")
            return 0
        print(f"page does NOT match this tape ({tape}) - run: python tools/publish_board.py")
        return 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    out = inject(page, fragment, tape)
    backup(SITE, "generated-board", stamp)
    SITE.write_text(out, encoding="utf-8", newline="\n")
    print(f"site/surveyor.html: {n} lines, {refused} refused, tape {tape}")
    for target in DEPLOY:
        backup(target, "generated-board", stamp)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(out, encoding="utf-8", newline="\n")
        print("deployed:", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
