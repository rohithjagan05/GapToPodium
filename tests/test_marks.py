import pytest

from src.marks import parse_mark


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("9.58", 9.58),  # ss.xx
        ("10.62", 10.62),
        ("1:43.03", 103.03),  # m:ss.xx
        ("3:26.00", 206.0),
        ("27:43.22", 1663.22),
        ("2:06:26", 7586.0),  # h:mm:ss
        ("1:59:40.2", 7180.2),  # h:mm:ss.x
        ("2-07:00", 7620.0),  # Olympedia's h-mm:ss style
        ("1-22:36", 4956.0),
        ("2-06:26 (1)", 7586.0),
        ("8.34", 8.34),  # metres
        ("8.34m", 8.34),
        ("89.45", 89.45),
        ("8,909", 8909.0),  # points with a thousands comma
        ("6,880", 6880.0),
        ("  10.62  ", 10.62),  # extra spaces
        ("10.62\xa0", 10.62),  # non-breaking space from HTML
        ("9.63 OR", 9.63),  # record labels
        ("1:40.91 WR", 100.91),
        ("2.39 =OR", 2.39),
        ("10.62 (+0.4)", 10.62),  # wind reading in brackets
        ("9.9h", 9.9),  # hand-timed
        ("8.90A", 8.9),  # altitude
    ],
)
def test_valid_marks(text, expected):
    assert parse_mark(text) == pytest.approx(expected)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "   ",
        "DNF",
        "DNS",
        "DQ",
        "NM",
        "-",
        "–",  # en dash
        "—",  # em dash
        "1:75.00",  # seconds cannot be 60 or more
        "1:2:3:4",  # too many parts
        "10,62",  # comma decimal is ambiguous, so rejected
        "abc",
        "10.62 9.88",  # two numbers: unclear which is the mark
        ":43.03",  # missing minutes
        "2-7:00",  # one-digit minutes is not a valid time
    ],
)
def test_invalid_marks_return_none(text):
    assert parse_mark(text) is None


def test_points_are_returned_as_float():
    assert isinstance(parse_mark("8,909"), float)