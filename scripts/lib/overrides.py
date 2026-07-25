"""Corrections to gaps and slips in the source wordlists.

The descriptions are hand-written, and a handful of entries have a missing
reading or a rōmaji field that clearly holds something other than a
transliteration. Each correction below is derivable from the source itself —
usually from the rōmaji or reading the channel gave alongside — and cites what
it was derived from.

This is not a place to second-guess the channel's teaching choices. If an entry
merely looks unusual, leave it: the deck should teach the vocabulary as taught.
Only demonstrable slips belong here, and each needs a reason.
"""

#: ``japanese -> (reading, derivation)``
#:
#: Entries whose kana reading the source omitted or gave only partially.
READINGS: dict[str, tuple[str, str]] = {
    # No reading given at all; both unambiguous from the rōmaji supplied.
    "第七日": ("だいななにち", 'rōmaji "dai nana nichi" (not だいしちにち)'),
    "炎の剣": ("ほのおのつるぎ", 'rōmaji "honoo no tsurugi"'),
    # Reading covers only the first word of the headword.
    "オリーブの若葉": (
        "おりーぶのわかば",
        'source reading "おりーぶ" stops after オリーブ; rōmaji "oriibu no wakaba" '
        "supplies the rest",
    ),
}

#: ``japanese -> (romaji, derivation)``
#:
#: Entries whose rōmaji field does not hold a transliteration of the headword.
ROMAJI: dict[str, tuple[str, str]] = {
    # The line reads "悪魔 (あくま akurei) demon", with あくれい's rōmaji from the
    # 悪霊 entry immediately below it — a copy-paste, since the reading given on
    # the same line is あくま.
    "悪魔": ("akuma", 'source rōmaji "akurei" belongs to 悪霊 on the next line; '
                     "reading あくま given on the same line"),
    # The line reads "mother 母 (はは, mother)": the English gloss was repeated
    # into the rōmaji slot.
    "母": ("haha", 'source rōmaji "mother" repeats the gloss; reading はは given'),
}


def reading(japanese: str, parsed: str) -> str:
    """The reading to use, preferring a recorded correction where one exists."""
    override = READINGS.get(japanese)
    if override and (not parsed or len(override[0]) > len(parsed)):
        return override[0]
    return parsed


def romaji(japanese: str, parsed: str) -> str:
    """The rōmaji to use, preferring a recorded correction where one exists."""
    override = ROMAJI.get(japanese)
    return override[0] if override else parsed
