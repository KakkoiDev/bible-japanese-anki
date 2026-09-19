#!/usr/bin/env python3
"""Turn the saved lesson descriptions into data/words.csv.

Runs the parser over ``sources/`` and writes one reviewable CSV. Intended to run
rarely: once the CSV exists it is the source of truth, hand-editable, and
tracked in git. Re-running overwrites it, so check the diff.

Every line that looks like an entry but cannot be parsed is reported and the
command fails. A vocabulary extractor that drops rows quietly just produces a
short deck, and nobody can tell which word went missing.

    uv run python scripts/parse_wordlists.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import overrides, parser, playlist  # noqa: E402

ROOT = Path(__file__).parent.parent
OUTPUT = ROOT / "data" / "words.csv"

COLUMNS = [
    "id",
    "lesson",
    "sort_order",
    "japanese",
    "reading",
    "romaji",
    "english",
    "audio_word",
]


def collect() -> tuple[list[dict[str, str]], list[parser.Problem]]:
    from jp_core import romaji as romaji_lib

    rows: list[dict[str, str]] = []
    problems: list[parser.Problem] = []

    for number, _video_id, _theme in playlist.LESSONS:
        source = ROOT / playlist.source_path(number)
        if not source.exists():
            raise SystemExit(
                f"{source} is missing — run scripts/fetch_wordlists.py first"
            )
        entries, lesson_problems = parser.parse_lesson(
            number, source.read_text(encoding="utf-8")
        )
        problems.extend(lesson_problems)

        for entry in entries:
            reading = overrides.reading(entry.japanese, entry.reading)
            word_romaji = overrides.romaji(entry.japanese, entry.romaji)
            # Audio filenames are derived from the reading, so they stay stable
            # when rows move; positional names would rebind clips on every edit.
            basename = romaji_lib.from_kana(reading.replace("、", "")) or word_romaji
            basename = "".join(c for c in basename.lower() if c.isalnum() or c == "_")
            rows.append({
                "id": entry.id,
                "lesson": str(entry.lesson),
                "sort_order": str(entry.position),
                "japanese": entry.japanese,
                "reading": reading,
                "romaji": word_romaji,
                "english": entry.english,
                "audio_word": f"w_{basename[:40]}.mp3" if basename else "",
            })

    return rows, problems


def resolve_audio_collisions(rows: list[dict[str, str]]) -> int:
    """Suffix duplicate audio filenames so no two words share a clip.

    Homophones are common here — 光 and 光る物 both gloss as "light", and several
    of God's names share readings — and two rows claiming one filename would
    silently give both the same audio.
    """
    seen: dict[str, int] = {}
    collisions = 0
    for row in rows:
        name = row["audio_word"]
        if not name:
            continue
        if name in seen:
            seen[name] += 1
            stem, _, extension = name.rpartition(".")
            row["audio_word"] = f"{stem}_{seen[name]}.{extension}"
            collisions += 1
        else:
            seen[name] = 1
    return collisions


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument(
        "--check", action="store_true",
        help="parse and report without writing the CSV",
    )
    args = argument_parser.parse_args()

    rows, problems = collect()
    collisions = resolve_audio_collisions(rows)

    by_lesson: dict[str, int] = {}
    for row in rows:
        by_lesson[row["lesson"]] = by_lesson.get(row["lesson"], 0) + 1
    for number, _video_id, _theme in playlist.LESSONS:
        print(f"  lesson {number:02d}  {by_lesson.get(str(number), 0):3d} words  "
              f"{playlist.label(number)}")

    print(f"\n{len(rows)} words across {len(playlist.LESSONS)} lessons")
    if collisions:
        print(f"{collisions} audio filename collision(s) resolved by suffixing")
    missing_reading = [r["id"] for r in rows if not r["reading"]]
    if missing_reading:
        print(f"{len(missing_reading)} without a reading: {missing_reading}")

    if problems:
        print(f"\n{len(problems)} line(s) could not be parsed:", file=sys.stderr)
        for problem in problems:
            print(f"  lesson {problem.lesson:02d} line {problem.line_number}: "
                  f"{problem.reason}\n    {problem.text}", file=sys.stderr)
        return 1

    if args.check:
        print("\n--check: nothing written")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
