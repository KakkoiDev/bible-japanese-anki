#!/usr/bin/env python3
"""Build the Anki deck from data/words.csv.

Two cards per word, which is the pairing minihongo settled on and the right one
for a bare vocabulary list:

    Recognition   see the Japanese, hear it, recall the meaning
    Recall        see the English, produce the Japanese

There are no example sentences, because the source has none. Inventing 361 of
them would mean 361 sentences needing pronunciation and grammar review, and an
unreviewed example sentence teaches errors confidently.

    uv run python scripts/create_deck.py [--force-style] [--output PATH]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import jpanki
from jpanki import furigana, ids, theme, validate

sys.path.insert(0, str(Path(__file__).parent))
from lib import playlist  # noqa: E402

ROOT = Path(__file__).parent.parent
WORDS = ROOT / "data" / "words.csv"
AUDIO = ROOT / "audio"

DECK_NAME = "Bible Japanese"
SLUG = "bible"

FIELDS = ["Japanese", "Reading", "Romaji", "English", "AudioWord", "Lesson"]


def build_css() -> str:
    """The shared design system plus this deck's one extra component."""
    return theme.compose(
        theme.base(),
        theme.headword(),
        theme.chip(".tags"),
        theme.ruby(),
        theme.replay(),
        theme.night(muted_selectors=(".card-type", ".hint", ".romaji")),
        extra="""
.romaji {
    font-size: 15px;
    color: #666666;
    letter-spacing: 0.5px;
    margin-top: 4px;
}
""",
    )


TEMPLATES = [
    {
        "name": "Recognition",
        "qfmt": """
<div class="card-type">Recognition</div>
<div class="word">{{Japanese}}</div>
<div class="audio">{{AudioWord}}</div>
""",
        "afmt": """
<div class="card-type">Recognition</div>
<div class="word">{{furigana:Reading}}</div>
<div class="audio">{{AudioWord}}</div>
<hr id="answer">
<div class="translation">{{English}}</div>
{{#Romaji}}<div class="romaji">{{Romaji}}</div>{{/Romaji}}
<div class="tags">{{Lesson}}</div>
""",
    },
    {
        "name": "Recall",
        "qfmt": """
<div class="card-type">Recall</div>
<div class="translation">{{English}}</div>
<div class="tags">{{Lesson}}</div>
""",
        "afmt": """
<div class="card-type">Recall</div>
<div class="translation">{{English}}</div>
<hr id="answer">
<div class="word">{{furigana:Reading}}</div>
<div class="audio">{{AudioWord}}</div>
{{#Romaji}}<div class="romaji">{{Romaji}}</div>{{/Romaji}}
""",
    },
]


def ruby_notation(japanese: str, reading: str) -> str:
    """Build Anki furigana notation, or plain text where ruby adds nothing.

    Anki's ``{{furigana:...}}`` filter reads ``漢字[かな]`` — square brackets,
    unlike the lenticular ``漢字【かな】`` used in the source projects' CSVs.

    A kana-only headword needs no ruby: いのち annotated with いのち is noise. Nor
    does a word whose reading matches it exactly.
    """
    if not reading or reading == japanese or not _has_kanji(japanese):
        return japanese
    # Whole-word annotation: the source gives one reading for the whole entry,
    # not per-character alignment, so guessing a finer split would be inventing.
    return f"{japanese}[{reading}]"


def _has_kanji(text: str) -> bool:
    return any("一" <= c <= "鿿" or c == "々" for c in text)


def check_data(rows: list[dict[str, str]]) -> validate.Report:
    report = validate.Report()
    report.extend(validate.check_columns(rows, [
        "id", "lesson", "sort_order", "japanese", "reading", "romaji",
        "english", "audio_word",
    ], where="words.csv"))
    report.extend(validate.check_required(
        rows, ["id", "lesson", "japanese", "english"], where="words.csv", id_column="id"))
    report.extend(validate.check_unique(rows, "id", where="words.csv"))
    report.extend(validate.check_unique(rows, "audio_word", where="words.csv"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "bible-japanese.apkg")
    parser.add_argument(
        "--force-style", action="store_true",
        help="mint a new model ID so Anki re-reads the CSS. RESETS REVIEW HISTORY.",
    )
    args = parser.parse_args()

    ids.assert_unique()
    registration = ids.for_deck(SLUG)

    rows = validate.load_rows(WORDS)
    check_data(rows).raise_if_failed()

    css = build_css()
    model_id = registration.model_id
    if args.force_style:
        model_id = jpanki.force_style(model_id, css)
        print(f"--force-style: model ID {registration.model_id} -> {model_id} "
              f"(this resets review history for every note)")

    spec = jpanki.NoteSpec(
        name=f"{DECK_NAME} Vocab",
        model_id=model_id,
        fields=FIELDS,
        templates=TEMPLATES,
        css=css,
    )
    model = jpanki.build_model(spec)

    package = jpanki.Package()
    decks: dict[int, object] = {}
    missing_audio = 0

    for row in sorted(rows, key=lambda r: (int(r["lesson"]), int(r["sort_order"]))):
        lesson = int(row["lesson"])
        if lesson not in decks:
            # "Lesson 01", "Lesson 10 - Christmas": already zero-padded, so
            # Anki's lexical sidebar sort follows the playlist without needing
            # jpanki.subdeck's separate numeric prefix.
            decks[lesson] = package.add_deck(jpanki.build_deck(
                registration.deck_id(lesson),
                f"{DECK_NAME}::{playlist.label(lesson)}",
            ))

        clip = AUDIO / row["audio_word"] if row["audio_word"] else None
        audio_field, media = jpanki.sound_ref(clip)
        if not audio_field:
            missing_audio += 1
        package.add_media(media)

        import genanki
        decks[lesson].add_note(genanki.Note(
            model=model,
            fields=[
                row["japanese"],
                ruby_notation(row["japanese"], row["reading"]),
                row["romaji"],
                row["english"],
                audio_field,
                playlist.label(lesson),
            ],
            # Keyed on lesson + written form: the gloss, reading and rōmaji can
            # all be corrected without orphaning a learner's review history.
            guid=jpanki.note_guid(SLUG, lesson, row["japanese"]),
            tags=[f"lesson{lesson:02d}"],
        ))

    output = package.write(args.output)
    notes = package.note_count()
    print(f"{output.name}: {notes} notes x {len(TEMPLATES)} cards = "
          f"{notes * len(TEMPLATES)} cards across {len(decks)} subdecks")
    if missing_audio:
        print(f"  {missing_audio} note(s) without audio — run scripts/generate_audio.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
