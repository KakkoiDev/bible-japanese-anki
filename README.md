# Bible Japanese Anki

An Anki deck of the **361 Japanese words** taught across the 15-lesson
[*Bible Japanese vocabulary* playlist](https://www.youtube.com/playlist?list=PLAo7ygGmnDLFnu5CcsBRO6GRrCZ5aUJfS)
by **[Japanese Bible Study Club](https://www.youtube.com/channel/UClw34zInEmug1BIJB4xKebQ)** —
vocabulary that turns up constantly in the Japanese Bible and in Japanese
Christian life, and almost never in a general textbook.

All credit for the vocabulary selection and teaching goes to that channel. This
repository only rearranges their published wordlists into spaced repetition;
please watch the lessons, where the words are actually explained.

361 words × 2 cards = **722 cards**, in 15 subdecks.

| | |
|---|---|
| Lessons 1–6 | Core faith vocabulary — God, worship, sin, salvation, the church |
| Lessons 7–11 | Contrasts, relationships, God's names and attributes, Christmas |
| Lessons 12–15 | Genesis narrative — Creation, Adam and Eve, the Fall, the Flood |

## Cards

Two cards per word, no example sentences.

**Recognition** — the Japanese word and its audio; recall the meaning.
**Recall** — the English gloss; produce the Japanese.

Answers show the reading as ruby, the English gloss, and the channel's rōmaji.
There are deliberately no example sentences: the source wordlists contain none,
and 361 invented sentences would each need pronunciation and grammar review.
An unreviewed example sentence teaches mistakes convincingly.

## Where the content comes from

The channel publishes each lesson's wordlist in the **video description**, so
nothing has to be transcribed — the written forms, readings, rōmaji and English
glosses are already written down. `scripts/fetch_wordlists.py` saves those
descriptions to `sources/`, and only the vocabulary table is extracted from
them. No transcript and no scripture text is reproduced here.

`sources/` is committed on purpose: after the first fetch the build never
touches the network, so it keeps working if a description is edited or a video
goes private.

## Build

```bash
uv sync

uv run python scripts/fetch_wordlists.py      # already done; --force to re-sync
uv run python scripts/parse_wordlists.py      # sources/ -> data/words.csv
uv run python scripts/validate.py             # schema, readings, rōmaji audit
uv run python scripts/generate_audio.py       # 361 Edge TTS clips -> audio/
uv run python scripts/create_deck.py          # -> bible-japanese.apkg
```

`ffmpeg` is optional but recommended. Without it, clips keep Edge TTS's variable
sample rate and loudness — reviewable, but noticeably uneven across a session.
With it, they are levelled to a consistent −20 dB. Install it and re-run with
`--force` to upgrade existing audio.

## Data

`data/words.csv` is the source of truth once generated, and is meant to be
hand-edited — the parser runs once, people own the result afterwards.

| Column | |
|---|---|
| `id` | `l07-003`, stable across edits |
| `lesson`, `sort_order` | position in the playlist and within the lesson |
| `japanese` | the written form, as the channel writes it |
| `reading` | kana reading; drives ruby and TTS |
| `romaji` | the channel's own transliteration, kept as given |
| `english` | the channel's gloss |
| `audio_word` | clip filename, derived from the reading |

Two entries (`第七日`, `炎の剣`) had no kana reading in the source; both are
recorded in `scripts/lib/reading_overrides.py`, derived from the rōmaji the
channel gave alongside them.

The channel's rōmaji is inconsistent by hand — `hukuin` and `fukuin`, `jyuujika`
and `jūjika` — and is preserved as written rather than normalised, since it is
their transliteration. `scripts/validate.py` cross-checks it against the kana
and reports divergences as warnings.

## Notes on the parsing

The descriptions are hand-written across a couple of years and drift in format.
Two arrangements dominate, and lines are classified individually rather than by
lesson:

```
Lessons 1–6     神 (かみ kami) God              Japanese first
Lessons 7–15    light 光 (ひかり, hikari)         English first
```

On top of that: entries wrapped across two lines, words written only in kana,
rōmaji given twice in wāpuro and macron forms, full-width parentheses and
spaces, glosses several words long, and readings containing their own commas.
`scripts/lib/parser.py` documents each case. Any line that looks like an entry
but does not parse fails the build rather than being skipped — a vocabulary
extractor that drops rows silently just produces a short deck, and nobody can
tell which word went missing.

## Built on

[jpanki](https://github.com/KakkoiDev/jpanki) — shared Japanese Anki deck
machinery (furigana, card CSS, Edge TTS, stable IDs), extracted from
[minihongo](https://github.com/KakkoiDev/minihongo) and
[nihongo-it-anki](https://github.com/KakkoiDev/nihongo-it-anki). This deck was
its first consumer.
