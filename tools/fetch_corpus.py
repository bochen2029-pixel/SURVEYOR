#!/usr/bin/env python3
"""tools/fetch_corpus.py - rebuild the pinned regulatory corpus from crosswalk/sources.yml.

The corpus is not in this repository: regulatory documents belong to their publishers.
What IS committed is the registry - urls, sha256 digests, byte counts, dates - and the
claim that follows from it: fetch your own copies and you can prove you are reading the
same bytes every citation was checked against, or discover that you are not.

This script makes that claim executable. It reads the registry, fetches each source it
knows how to rebuild, renders it, and compares the sha256 with the pin:

    MATCH     the bytes are the ones the crosswalk was verified against
    DRIFT     the publisher has changed the text - every quote resting on it is re-checked
              by `python crosswalk/pins.py --check`, which is exactly the intended alarm
    MANUAL    the source cannot be rebuilt mechanically (a PDF extraction someone did by
              hand); the registry says where it came from and the operator supplies it

It lives in tools/ rather than crosswalk/ deliberately: it reaches the network, and the
crosswalk, floor, clocks and ledger are scanned for network imports (law B2). The organ
that verifies citations must not be able to fetch what it verifies against.

    python tools/fetch_corpus.py --check           what is present, and does it match?
    python tools/fetch_corpus.py --fetch [ID ...]  rebuild (default: everything rebuildable)
Stdlib only.
"""
from __future__ import annotations

import gzip
import hashlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "crosswalk"))
import pins  # noqa: E402   (registry reader; it does no fetching of its own)

HEADERS = {"Accept": "application/xml, text/xml, */*",
           "Accept-Encoding": "gzip, deflate",     # the eCFR endpoint REQUIRES compression
           "User-Agent": "SURVEYOR-crosswalk/0.1 (regulatory corpus pin)"}


def http_get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=180) as r:
        body, enc = r.read(), (r.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        return gzip.decompress(body)
    if enc == "deflate":
        return zlib.decompress(body, -zlib.MAX_WBITS)
    return body


def render_ecfr_xml(raw: str) -> str:
    """The eCFR full-text XML rendered to the plain text the citations are matched
    against. Deterministic: the same XML always yields the same bytes, which is what
    makes the sha256 in the registry meaningful."""
    root = ET.fromstring(raw)
    lines: list[str] = []
    for el in root.iter():
        tag = el.tag.upper()
        if tag not in ("HEAD", "P", "FP", "CITA"):
            continue
        t = re.sub(r"\s+", " ", "".join(el.itertext())).strip()
        if not t:
            continue
        if tag == "HEAD":
            lines += ["", t, ""]
        else:
            lines += [t, ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"


def rebuild(sid: str, src: dict) -> tuple[str, bytes | None]:
    url = str(src.get("url", ""))
    if "ecfr.gov/api/versioner" in url and url.endswith(tuple(f"part={n}" for n in ("121", "486", "1271"))) or \
       ("ecfr.gov/api/versioner" in url and ".xml?" in url):
        raw = http_get(url).decode("utf-8")
        return "ok", render_ecfr_xml(raw).encode("utf-8")
    return "MANUAL", None


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(argv: list[str]) -> int:
    sources = pins.load_sources()
    roots, how = pins.corpus_roots()
    target = roots[-1] if roots else (ROOT / "crosswalk" / "corpus")
    do_fetch = "--fetch" in argv
    only = [a for a in argv[1:] if not a.startswith("--")]
    print(f"registry: {len(sources)} sources | corpus roots: {how} | writing to {target}")
    bad = 0
    for sid, src in sorted(sources.items()):
        if only and sid not in only:
            continue
        have = pins.find_source_file(str(src["file"]))
        if have and sha256(have.read_bytes()) == src.get("sha256"):
            print(f"  MATCH   {sid:<24} {have}")
            continue
        if have:
            print(f"  DRIFT   {sid:<24} {have} - present but the bytes are not the pinned ones")
            bad += 1
            if not do_fetch:
                continue
        if not do_fetch:
            print(f"  ABSENT  {sid:<24} run with --fetch, or place {src['file']} in a corpus root")
            bad += 1
            continue
        try:
            status, body = rebuild(sid, src)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR   {sid:<24} {type(e).__name__}: {e}")
            bad += 1
            continue
        if body is None:
            print(f"  MANUAL  {sid:<24} not mechanically rebuildable; source: {src.get('url')}")
            bad += 1
            continue
        got = sha256(body)
        target.mkdir(parents=True, exist_ok=True)
        (target / str(src["file"])).write_bytes(body)
        if got == src.get("sha256"):
            print(f"  MATCH   {sid:<24} rebuilt, {len(body):,} B, sha matches the pin")
        else:
            print(f"  DRIFT   {sid:<24} rebuilt, {len(body):,} B, sha {got[:16]}... != pinned "
                  f"{str(src.get('sha256'))[:16]}...")
            print(f"          The publisher's text has changed since it was pinned. That is the alarm,")
            print(f"          not the failure: run `python crosswalk/pins.py --check` to see which")
            print(f"          citations no longer hold, and `--diff` to see which checks need review.")
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
