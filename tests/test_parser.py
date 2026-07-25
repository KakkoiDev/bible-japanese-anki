"""The parser must handle every format the fifteen descriptions actually use.

Each case here was taken from the real sources, not invented — the descriptions
are hand-written and drift, and every quirk below cost a bug before it was
handled.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lib import overrides, parser, playlist  # noqa: E402

ROOT = Path(__file__).parent.parent


def parse_one(line: str):
    result = parser.parse_line(parser.normalize(line))
    assert not isinstance(result, str), f"failed to parse: {result}"
    return result


# ── the two dominant formats ────────────────────────────────────────


def test_japanese_first_format():
    """Lessons 1-6: 神 (かみ kami) God"""
    assert parse_one("神 (かみ kami) God") == ("神", "かみ", "kami", "God")


def test_english_first_format():
    """Lessons 7-15: light 光 (ひかり, hikari)"""
    assert parse_one("light 光 (ひかり, hikari)") == ("光", "ひかり", "hikari", "light")


def test_both_formats_coexist_within_one_lesson():
    """Format is decided per line, never per lesson."""
    a = parse_one("神 (かみ kami) God")
    b = parse_one("light 光 (ひかり, hikari)")
    assert a[0] == "神" and b[0] == "光"


# ── kana-only headwords ─────────────────────────────────────────────


def test_kana_only_headword_japanese_first():
    """あわれみ (awaremi) mercy — the parentheses hold rōmaji alone."""
    assert parse_one("あわれみ (awaremi) mercy") == ("あわれみ", "あわれみ", "awaremi", "mercy")


def test_kana_only_headword_english_first():
    assert parse_one("life いのち (inochi)") == ("いのち", "いのち", "inochi", "life")


# ── rōmaji variants ─────────────────────────────────────────────────


def test_slash_separated_variants_keep_the_ascii_form():
    assert parse_one("perfume 香油 (こうゆ, kouyu/kōyu)")[2] == "kouyu"


def test_stray_space_in_variant_list():
    """"chuukaisha/ chūkaisha" — note the space after the slash."""
    assert parse_one("mediator 仲介者 (ちゅうかいしゃ, chuukaisha/ chūkaisha)")[2] == "chuukaisha"


def test_comma_separated_variants_are_collapsed():
    """"ou, ō" is one word twice, unlike "ou no ou, shu no shu"."""
    assert parse_one("king 王 (おう, ou, ō)")[2] == "ou"


def test_comma_inside_a_genuine_multipart_romaji_is_kept():
    japanese, reading, romaji, _ = parse_one(
        "KING OF KINGS AND LORD OF LORDS 王の王、主の主 (おうのおう、しゅのしゅ, ou no ou, shu no shu)"
    )
    assert japanese == "王の王、主の主"
    assert reading == "おうのおう、しゅのしゅ"
    assert "shu no shu" in romaji


# ── readings ────────────────────────────────────────────────────────


def test_multiword_reading_loses_its_spaces():
    """"えいえんの いのち" is one kana run; spaces would break ruby and TTS."""
    assert parse_one("永遠のいのち (えいえんの いのち, eien no inochi) eternal life")[1] == "えいえんのいのち"


def test_reading_comma_is_folded_to_ideographic_form():
    reading = parse_one("あわれみ深く、なさけ深い神 (あわれみぶかく,なさけぶかいかみ, awaremibukaku) gracious God")[1]
    assert reading == "あわれみぶかく、なさけぶかいかみ"


def test_reading_keeps_interpunct():
    assert parse_one("イエス・キリスト (いえす・きりすと iesu kirisuto) Jesus Christ")[1] == "いえす・きりすと"


def test_missing_reading_is_reported_as_empty_not_guessed():
    """第七日 (dai nana nichi) gives no kana; the parser must not invent one."""
    assert parse_one("the seventh day 第七日 (dai nana nichi)")[1] == ""


def test_long_vowel_mark_survives_in_a_reading():
    assert parse_one("Euphrates ユーフラテス (ゆーふらてす, yuufuratesu)")[1] == "ゆーふらてす"


# ── multi-word glosses ──────────────────────────────────────────────


def test_gloss_with_many_words_splits_at_the_first_japanese_character():
    japanese, _, _, english = parse_one(
        "great creature of the sea 海の巨獣 (うみのきょじゅう, umi no kyojyuu)"
    )
    assert japanese == "海の巨獣"
    assert english == "great creature of the sea"


def test_gloss_containing_japanese_punctuation():
    japanese, _, _, english = parse_one(
        "compassionate and gracious God あわれみ深く、なさけ深い神 (あわれみぶかく, awaremibukaku)"
    )
    assert english == "compassionate and gracious God"
    assert japanese.startswith("あわれみ深く")


# ── width and whitespace ────────────────────────────────────────────


def test_full_width_parentheses():
    assert parse_one("全能者　（ぜんのうしゃ, zennousha）Almighty")[0] == "全能者"


def test_ideographic_space_is_normalised():
    assert parse_one("heaven 天 (てん、ten)　")[0] == "天"


def test_trailing_whitespace_is_stripped():
    assert parse_one("good 善 (ぜん, zen) ")[0] == "善"


# ── wrapped entries ─────────────────────────────────────────────────


def test_wrapped_entry_is_rejoined():
    """Long entries in lesson 9 put the reading on the next line."""
    lines = [
        "Lion of the tribe of Judah ユダ族から出た獅子",
        "    (ゆだぞくからでたしし, yudazoku kara deta shishi)",
    ]
    joined = parser.join_wrapped(lines)
    assert len(joined) == 1
    japanese, reading, _, english = parse_one(joined[0][1])
    assert japanese == "ユダ族から出た獅子"
    assert reading == "ゆだぞくからでたしし"
    assert english == "Lion of the tribe of Judah"


def test_wrapped_entry_reports_the_first_line_number():
    joined = parser.join_wrapped(["word 語 ", "  (ご, go)"])
    assert joined[0][0] == 1


def test_continuation_with_no_predecessor_is_not_dropped():
    assert parser.join_wrapped(["  (ご, go)"])[0][1] == "(ご, go)"


# ── noise ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("line", [
    "【wordlist】",
    "May God bless you all! 😊　Wordlist ↓",
    "【About this Channel】",
    "This Channel covers various topics related to Christianity in Japan.",
    "#learnjapanese #japanesebible",
    "In this video, you can learn Japanese words that are commonly used in the Bible",
])
def test_noise_lines_are_skipped(line):
    assert parser.NOISE.match(parser.normalize(line))


def test_prose_without_japanese_is_not_reported_as_a_problem():
    """Greetings and dividers are not failed entries."""
    _entries, problems = parser.parse_lesson(1, "Here is No.3! Ganbatte kudasai\n(^o^)/\n___\n")
    assert problems == []


def test_unparseable_entry_like_line_is_reported():
    """A line with Japanese and parentheses that still fails must not vanish."""
    _entries, problems = parser.parse_lesson(1, "（かみ kami）\n")
    assert len(problems) == 1


# ── whole-corpus invariants ─────────────────────────────────────────


def all_entries():
    entries = []
    for number, _video_id, _theme in playlist.LESSONS:
        source = ROOT / playlist.source_path(number)
        parsed, _problems = parser.parse_lesson(number, source.read_text(encoding="utf-8"))
        entries.extend(parsed)
    return entries


def test_every_lesson_parses_without_problems():
    for number, _video_id, _theme in playlist.LESSONS:
        source = ROOT / playlist.source_path(number)
        _entries, problems = parser.parse_lesson(number, source.read_text(encoding="utf-8"))
        assert problems == [], f"lesson {number}: {problems}"


def test_total_word_count():
    assert len(all_entries()) == 361


def test_every_entry_has_a_headword_and_a_gloss():
    for entry in all_entries():
        assert entry.japanese and entry.english, entry


def test_no_reading_contains_a_space():
    for entry in all_entries():
        assert " " not in entry.reading, entry


def test_no_romaji_contains_kana():
    """Kana leaking into the rōmaji field means the split went wrong."""
    for entry in all_entries():
        assert not parser.KANA.search(entry.romaji), entry


def test_no_gloss_contains_japanese():
    for entry in all_entries():
        assert not parser.JAPANESE_CHAR.search(entry.english), entry


def test_ids_are_unique():
    ids = [entry.id for entry in all_entries()]
    assert len(ids) == len(set(ids))


def test_overrides_all_apply_to_real_entries():
    """A stale override is dead weight and hides that the source changed."""
    headwords = {entry.japanese for entry in all_entries()}
    for word in {**overrides.READINGS, **overrides.ROMAJI}:
        assert word in headwords, f"override for {word!r} matches no entry"


def test_overrides_only_fill_or_extend_readings():
    for entry in all_entries():
        corrected = overrides.reading(entry.japanese, entry.reading)
        if entry.japanese in overrides.READINGS:
            assert len(corrected) >= len(entry.reading)
