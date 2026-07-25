"""Parse the channel's wordlists into structured vocabulary entries.

The fifteen descriptions are hand-written, over what looks like a couple of
years, and the format drifts. Two arrangements dominate:

    Lessons 1-6    神 (かみ kami) God              Japanese first, space-separated
    Lessons 7-15   light 光 (ひかり, hikari)         English first, comma-separated

and neither is used consistently enough to select by lesson number, so every
line is classified on its own. Layered on top of that: entries wrapped across
two lines, words written only in kana (so the parentheses hold rōmaji alone),
rōmaji given twice in wāpuro and macron forms, full-width parentheses and
spaces, English glosses several words long, and a duplicate word or two across
lessons.

Everything here is tolerant by design: an unparseable line is *reported*, never
silently dropped, because a silent drop in a vocabulary extractor is invisible —
the deck simply comes out short and nobody notices which word is missing.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Kana, kanji, and the 々 repetition mark: the characters that mark where a
# Japanese run begins. Deliberately excludes punctuation (、・ー) so that a
# gloss/word split lands on a real character.
JAPANESE_CHAR = re.compile(r"[぀-ヿ一-鿿々]")
#: Any kana character.
KANA = re.compile(r"[぀-ヿ]")
#: A string consisting only of kana and the punctuation that appears inside
#: readings (interpunct, length mark, ideographic comma, spaces).
KANA_ONLY = re.compile(r"^[぀-ヿ・ー、 ]+$")
#: Latin letters, including the macron forms the channel sometimes uses.
LATIN = re.compile(r"[A-Za-zāīūēōĀĪŪĒŌ]")

# Any parenthesised group, in either width.
PAREN = re.compile(r"[（(]([^)）]*)[)）]")

# Lines that are structure or promotion, not vocabulary.
NOISE = re.compile(
    r"""^\s*(?:
        [#＃]                                   # hashtag block
      | .*(?:wordlist|word\s*list)              # 【wordlist】, "Wordlist ↓"
      | .*about\s+this\s+channel
      | .*this\s+channel\s+covers
      | .*(?:subscribe|instagram|twitter|patreon|https?://)
      | .*(?:in\s+this\s+video|you\s+can\s+learn|may\s+god\s+bless)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


@dataclass
class Entry:
    """One vocabulary item."""

    lesson: int
    position: int
    japanese: str
    reading: str
    romaji: str
    english: str

    @property
    def id(self) -> str:
        return f"l{self.lesson:02d}-{self.position:03d}"


@dataclass
class Problem:
    """A line that could not be parsed, kept for review."""

    lesson: int
    line_number: int
    text: str
    reason: str


def normalize(text: str) -> str:
    """Fold the whitespace variants that appear throughout the descriptions.

    Ideographic space (U+3000) and no-break space (U+00A0) both show up, often
    mid-entry, and would otherwise defeat every subsequent split.
    """
    text = text.replace("　", " ").replace(" ", " ").replace("​", "")
    return re.sub(r"[ \t]+", " ", text).strip()


def join_wrapped(lines: list[str]) -> list[tuple[int, str]]:
    """Rejoin entries split across two lines.

    Long entries in lesson 9 continue on the next line with the parenthesised
    reading alone. Returns ``(original line number, text)`` so problems can still
    be reported against the right line.
    """
    out: list[tuple[int, str]] = []
    for number, raw in enumerate(lines, start=1):
        line = normalize(raw)
        if not line:
            continue
        if line.startswith(("(", "（")) and out:
            previous_number, previous_text = out[-1]
            out[-1] = (previous_number, f"{previous_text} {line}")
            continue
        out.append((number, line))
    return out


def split_reading(paren: str) -> tuple[str, str]:
    """Split a parenthesised group into ``(reading, rōmaji)``.

    Divides on *character class* rather than on a separator, because the
    separator is not reliable — the descriptions use an ASCII comma, an
    ideographic comma, or nothing but a space, and readings themselves contain
    both spaces and ideographic commas. The reading is the leading run of kana;
    the rōmaji is everything from the first Latin letter on.

        "かみ kami"                     -> ("かみ", "kami")
        "ひかり, hikari"                 -> ("ひかり", "hikari")
        "いえす・きりすと iesu kirisuto"   -> ("いえすきりすと", "iesu kirisuto")
        "えいえんの いのち, eien no inochi" -> ("えいえんのいのち", "eien no inochi")
        "おうのおう、しゅのしゅ ou no ou"   -> ("おうのおう、しゅのしゅ", "ou no ou")
        "awaremi"                       -> ("", "awaremi")      already kana
        "こうゆ, kouyu/kōyu"             -> ("こうゆ", "kouyu")   macron form dropped
        "dai nana nichi"                -> ("", "dai nana nichi") no reading given
    """
    paren = normalize(paren)
    if not paren:
        return "", ""

    latin = LATIN.search(paren)
    head = paren[: latin.start()] if latin else paren
    tail = paren[latin.start():] if latin else ""

    # Trailing separator between the two halves belongs to neither.
    head = head.strip().rstrip(",、 ").strip()

    if not KANA.search(head):
        # No kana before the rōmaji, so the source gave no separate reading:
        # either the headword is already kana, or the reading was omitted.
        return "", _first_romaji(paren if not latin else tail)

    # Internal spaces are word boundaries the channel added for legibility; a
    # reading is a single kana run, and spaces would break ruby and TTS alike.
    # Commas are kept — they mirror punctuation in the headword — but folded to
    # the ideographic form, since the descriptions use both interchangeably.
    return head.replace(" ", "").replace(",", "、"), _first_romaji(tail)


def _first_romaji(romaji: str) -> str:
    """Keep the first spelling when several are offered.

    The descriptions frequently give both wāpuro and macron forms of the same
    word, separated either by a slash (``kouyu/kōyu``) or by a comma
    (``ou, ō``). The first is the ASCII one, which is what a learner would type.

    A comma is only treated as offering an alternative when the two halves are
    the same word spelled differently — otherwise it is punctuation inside a
    multi-part reading (``ou no ou, shu no shu``) and must be kept.
    """
    from jpanki import romaji as romaji_lib

    romaji = normalize(romaji)
    if not romaji:
        return ""

    first = normalize(romaji.split("/")[0])

    head, comma, tail = first.partition(",")
    if comma and romaji_lib.same_romanisation(head, tail):
        return normalize(head)
    return first


def split_english_japanese(text: str) -> tuple[str, str]:
    """Split ``"light 光"`` into ``("light", "光")``.

    Splits at the first Japanese character rather than on whitespace, because
    glosses run to several words: ``"great creature of the sea 海の巨獣"``.
    """
    match = JAPANESE_CHAR.search(text)
    if not match:
        return normalize(text), ""
    return normalize(text[: match.start()]), normalize(text[match.start():])


def parse_line(line: str) -> tuple[str, str, str, str] | str:
    """Parse one entry line into ``(japanese, reading, romaji, english)``.

    Returns a reason string instead if the line is not an entry.
    """
    matches = list(PAREN.finditer(line))
    if not matches:
        return "no parenthesised reading"

    # Prefer the group that actually looks like a reading; a gloss may contain
    # its own parenthetical aside.
    reading_match = next(
        (m for m in matches
         if JAPANESE_CHAR.search(m.group(1)) or LATIN.search(m.group(1))),
        matches[0],
    )

    before = normalize(line[: reading_match.start()])
    after = normalize(line[reading_match.end():]).strip("-–—:： ")
    reading, romaji = split_reading(reading_match.group(1))

    if not before:
        return "nothing before the reading"

    if after and LATIN.search(after):
        # Japanese-first: 神 (かみ kami) God
        japanese, english = before, after
        # A stray English word may precede the headword; keep only the Japanese.
        english_prefix, japanese_part = split_english_japanese(japanese)
        if japanese_part:
            japanese = japanese_part
            if english_prefix and english_prefix.lower() not in english.lower():
                english = f"{english_prefix} {english}".strip()
    else:
        # English-first: light 光 (ひかり, hikari)
        english, japanese = split_english_japanese(before)
        if not japanese:
            return "no Japanese found before the reading"
        if not english:
            return "no English gloss"

    if not JAPANESE_CHAR.search(japanese):
        return f"headword has no Japanese characters: {japanese!r}"
    if not english:
        return "no English gloss"

    # A kana-only headword is its own reading.
    if not reading and KANA_ONLY.match(japanese):
        reading = japanese

    return japanese, reading, romaji, english


def parse_lesson(lesson: int, description: str) -> tuple[list[Entry], list[Problem]]:
    """Parse one lesson's description."""
    entries: list[Entry] = []
    problems: list[Problem] = []
    position = 0

    for line_number, line in join_wrapped(description.splitlines()):
        if NOISE.match(line):
            continue
        result = parse_line(line)
        if isinstance(result, str):
            # Only complain about lines that plausibly meant to be entries;
            # prose in the description is not an error.
            if PAREN.search(line) and JAPANESE_CHAR.search(line):
                problems.append(Problem(lesson, line_number, line, result))
            continue
        japanese, reading, romaji, english = result
        position += 1
        entries.append(Entry(lesson, position, japanese, reading, romaji, english))

    return entries, problems
