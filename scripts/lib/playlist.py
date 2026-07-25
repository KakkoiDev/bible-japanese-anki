"""The source playlist: which videos, in what order, under what titles.

Fifteen lessons from the Japanese Bible Study Club channel, each teaching a
themed set of biblical vocabulary. The channel publishes each lesson's wordlist
in the video description, which is what this project reads — the vocabulary
table (written form, reading, rōmaji, English gloss) and nothing else.

IDs are pinned rather than discovered from the playlist page so the build is
reproducible: a playlist can be reordered or added to, and a deck whose subdeck
numbering shifts under it would scramble every learner's progress.
"""

PLAYLIST_ID = "PLAo7ygGmnDLFnu5CcsBRO6GRrCZ5aUJfS"
PLAYLIST_URL = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"
CHANNEL = "Japanese Bible Study Club"

#: ``(lesson number, video id, theme)``, in playlist order.
#:
#: Themes come from the bracketed suffixes in the video titles. Ten of the
#: fifteen carry none, so those fall back to a bare lesson label — inventing
#: themes for them would be guessing at the channel's intent.
LESSONS: list[tuple[int, str, str | None]] = [
    (1, "zenDNwOcV8E", None),
    (2, "A43bZ47WlQg", None),
    (3, "CCr7hqhCKV0", None),
    (4, "hxfxpUQOTg4", None),
    (5, "V5d2lCv-SSc", None),
    (6, "6tAvhdHw_hU", None),
    (7, "lwcv-kTDkLs", None),
    (8, "jwOfLk-XdD8", None),
    (9, "5y-lo517Y6c", None),
    (10, "CVcJlLJERdY", "Christmas"),
    (11, "9nE_jj34r0Y", None),
    (12, "pq1WkW8DHVs", "The Beginning"),
    (13, "O4aNY4B2POE", "Adam and Eve"),
    (14, "xT_djWKzh9I", "The Fall, Cain and Abel"),
    (15, "7NDqFSWcmbs", "Noah, the Flood"),
]

BY_NUMBER = {number: (video_id, theme) for number, video_id, theme in LESSONS}


def label(number: int) -> str:
    """Human-readable subdeck label for a lesson."""
    _, theme = BY_NUMBER[number]
    return f"Lesson {number:02d} - {theme}" if theme else f"Lesson {number:02d}"


def video_url(number: int) -> str:
    video_id, _ = BY_NUMBER[number]
    return f"https://www.youtube.com/watch?v={video_id}&list={PLAYLIST_ID}"


def source_path(number: int) -> str:
    return f"sources/lesson{number:02d}.txt"
