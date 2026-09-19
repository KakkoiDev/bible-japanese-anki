#!/usr/bin/env python3
"""Generate one audio clip per word with Edge TTS.

Synthesises from the kana reading rather than the written form, so the engine
cannot pick the wrong reading for an ambiguous compound — and this deck has
several, mostly among God's names (造り主, 救い主, 助け主, 贖い主 all end in 主 but
read ぬし, not しゅ).

Filenames come from the reading, not the row position, so re-ordering or
inserting words never rebinds a clip to the wrong entry.

    uv run python scripts/generate_audio.py [--force] [--female] [--limit N]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from jp_core import tts, validate

ROOT = Path(__file__).parent.parent
WORDS = ROOT / "data" / "words.csv"
AUDIO = ROOT / "audio"


def build_jobs(rows: list[dict[str, str]], voice: str, directory: Path) -> list[tts.Job]:
    jobs: list[tts.Job] = []
    skipped: list[str] = []
    for row in rows:
        if not row["audio_word"]:
            skipped.append(row["id"])
            continue
        # Prefer the reading; fall back to the written form, which Edge TTS
        # handles well for standard readings.
        text = row["reading"].replace("、", "、") or row["japanese"]
        if not text:
            skipped.append(row["id"])
            continue
        jobs.append(tts.Job(text=text, output=directory / row["audio_word"], voice=voice))
    if skipped:
        print(f"  skipping {len(skipped)} row(s) with nothing to synthesise: {skipped}")
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="regenerate existing clips")
    parser.add_argument("--female", action="store_true",
                        help=f"use {tts.VOICE_FEMALE} instead of {tts.VOICE_MALE}")
    parser.add_argument("--limit", type=int, help="only the first N words (for a smoke test)")
    args = parser.parse_args()

    rows = validate.load_rows(WORDS)
    if args.limit:
        rows = rows[: args.limit]

    voice = tts.VOICE_FEMALE if args.female else tts.VOICE_MALE
    directory = AUDIO if not args.female else AUDIO.with_name("audio-female")
    jobs = build_jobs(rows, voice, directory)

    print(f"{len(jobs)} clip(s) with {voice} into {directory.name}/")

    def progress(index: int, total: int, job: tts.Job, was_skipped: bool) -> None:
        if was_skipped:
            return
        print(f"  [{index:3d}/{total}] {job.output.name}")

    written = asyncio.run(tts.synthesize_all(jobs, force=args.force, on_progress=progress))
    existing = len(jobs) - len(written)
    print(f"\n{len(written)} generated, {existing} already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
