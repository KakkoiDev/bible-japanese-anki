#!/usr/bin/env python3
"""Validate data/words.csv before building.

Errors block the build. Warnings do not — several are inherent to the source
data (the channel's rōmaji is inconsistent by hand) and normalising them away
would misrepresent what the channel wrote.

    uv run python scripts/validate.py [--strict]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jp_core import furigana, romaji, validate

sys.path.insert(0, str(Path(__file__).parent))
from lib import playlist  # noqa: E402

ROOT = Path(__file__).parent.parent
WORDS = ROOT / "data" / "words.csv"
AUDIO = ROOT / "audio"

COLUMNS = [
    "id", "lesson", "sort_order", "japanese", "reading", "romaji",
    "english", "audio_word",
]

#: The playlist teaches 361 words. Pinned so an accidental re-parse that loses
#: or duplicates rows fails loudly instead of quietly shipping a different deck.
EXPECTED_WORDS = 361


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()

    rows = validate.load_rows(WORDS)
    report = validate.Report()

    report.extend(validate.check_columns(rows, COLUMNS, where="words.csv"))
    report.extend(validate.check_required(
        rows, ["id", "lesson", "sort_order", "japanese", "english", "romaji"],
        where="words.csv", id_column="id"))
    report.extend(validate.check_unique(rows, "id", where="words.csv"))
    report.extend(validate.check_unique(rows, "audio_word", where="words.csv"))
    report.extend(validate.check_media(rows, "audio_word", AUDIO, where="words.csv"))

    if len(rows) != EXPECTED_WORDS:
        report.error(
            f"expected {EXPECTED_WORDS} words, found {len(rows)}. If the change "
            f"is intended, update EXPECTED_WORDS and say why in the commit."
        )

    lessons = {int(r["lesson"]) for r in rows}
    for number, _video_id, _theme in playlist.LESSONS:
        if number not in lessons:
            report.error(f"lesson {number} contributed no words")

    for index, row in enumerate(rows, start=2):
        label = f"words.csv:{index} ({row['id']})"
        reading = row["reading"]

        if reading:
            # 、 is legitimate inside a reading when the headword has one.
            if not furigana.is_kana(reading.replace("、", "")):
                report.error(f"{label}: reading {reading!r} is not all kana")
            if "、" in reading and "、" not in row["japanese"]:
                report.warn(f"{label}: reading has 、 but the headword does not")
        else:
            report.warn(f"{label}: no reading — no ruby, and TTS must guess")

        if reading and row["romaji"] and not romaji.matches(
            reading.replace("、", ""), row["romaji"]
        ):
            # Expected: the channel romanises by hand and inconsistently.
            report.warn(
                f"{label}: rōmaji {row['romaji']!r} does not match reading "
                f"{reading!r} (derived {romaji.from_kana(reading.replace('、', ''))!r})"
            )

        if not furigana.NOTATION_RE.search(row["japanese"]) and "【" in row["japanese"]:
            report.error(f"{label}: headword has a malformed furigana bracket")

    duplicates: dict[str, list[str]] = {}
    for row in rows:
        duplicates.setdefault(row["japanese"], []).append(row["id"])
    for word, matching in sorted(duplicates.items()):
        if len(matching) > 1:
            report.warn(f"{word!r} appears in several lessons: {matching}")

    print(report.render())
    print(f"\n{len(rows)} words, {len(lessons)} lessons, "
          f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")

    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
