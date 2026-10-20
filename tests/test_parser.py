import unicodedata
from datetime import datetime, timedelta

import pytest

from cal.core.dateparser import parse

NOW = datetime(2026, 10, 20, 10, 0)  # Tuesday
NONE = (None, None)


def at(m, d, h, mi=0, y=2026, dur=60):
    s = datetime(y, m, d, h, mi)
    return s, s + timedelta(minutes=dur)


def day(m, d, y=2026):
    s = datetime(y, m, d)
    return s, s + timedelta(days=1)


CASES = [
    # --- relative days
    ("Meeting với Tuấn thứ 6 15:00", "Meeting với Tuấn", at(10, 23, 15), False, None),
    ("Họp mai 9h", "Họp", at(10, 21, 9), False, None),
    ("Họp ngày mai 9h30", "Họp", at(10, 21, 9, 30), False, None),
    ("Họp hôm nay 15h", "Họp", at(10, 20, 15), False, None),
    ("Ăn tối mốt 19:00", "Ăn tối", at(10, 22, 19), False, None),
    ("Học bài ngày mốt", "Học bài", day(10, 22), True, None),
    ("Họp ngày một", "Họp ngày một", NONE, False, None),
    ("Họp với Mai", "Họp với Mai", NONE, False, None),
    ("Họp với Mai mai 9h", "Họp với Mai", at(10, 21, 9), False, None),
    # --- weekdays
    ("Họp thứ 2", "Họp", day(10, 26), True, None),
    ("Họp thứ hai 8h", "Họp", at(10, 26, 8), False, None),
    ("Họp thứ 3 8h", "Họp", at(10, 27, 8), False, None),
    ("Họp thứ 3 11h", "Họp", at(10, 20, 11), False, None),
    ("Họp thứ 3", "Họp", day(10, 20), True, None),
    ("Họp chủ nhật 10h", "Họp", at(10, 25, 10), False, None),
    ("HỌP THỨ 6 15H", "HỌP", at(10, 23, 15), False, None),
    ("Họp vào thứ 6", "Họp", day(10, 23), True, None),
    ("Họp thứ 6 lúc", "Họp", day(10, 23), True, None),
    # --- next week
    ("Họp thứ 6 tuần sau 14h", "Họp", at(10, 30, 14), False, None),
    ("Họp tuần sau thứ 5", "Họp", day(10, 29), True, None),
    ("Họp tuần sau", "Họp", day(10, 27), True, None),
    ("Họp tuần tới 9h", "Họp", at(10, 27, 9), False, None),
    # --- explicit dates
    ("Nộp bài ngày 25/10", "Nộp bài", day(10, 25), True, None),
    ("Nộp bài 25/10 23:59", "Nộp bài",
     (datetime(2026, 10, 25, 23, 59), datetime(2026, 10, 26, 0, 59)), False, None),
    ("Sinh nhật 5/1", "Sinh nhật", day(1, 5, 2027), True, None),
    ("Sinh nhật 20/10", "Sinh nhật", day(10, 20), True, None),
    ("Sinh nhật 19/10", "Sinh nhật", day(10, 19, 2027), True, None),
    ("Họp 20/10/2025", "Họp", day(10, 20, 2025), True, None),
    ("Họp 20/10/27", "Họp", day(10, 20, 2027), True, None),
    ("Họp 31/2", "Họp 31/2", NONE, False, None),
    # --- times and ranges
    ("Họp 15:00", "Họp", at(10, 20, 15), False, None),
    ("Họp 9:00", "Họp", at(10, 21, 9), False, None),
    ("Họp 15h", "Họp", at(10, 20, 15), False, None),
    ("Họp 15h30", "Họp", at(10, 20, 15, 30), False, None),
    ("Họp lúc 15h30", "Họp", at(10, 20, 15, 30), False, None),
    ("Họp 15:00-16:30", "Họp", at(10, 20, 15, dur=90), False, None),
    ("Họp 15:00 - 16:30", "Họp", at(10, 20, 15, dur=90), False, None),
    ("Họp 15h-16h30", "Họp", at(10, 20, 15, dur=90), False, None),
    ("Họp từ 9h đến 11h", "Họp", at(10, 21, 9, dur=120), False, None),
    ("Họp 23:00-01:00", "Họp", at(10, 20, 23, dur=120), False, None),
    ("Họp 15:00-15:00", "Họp", at(10, 20, 15), False, None),
    ("Họp 25:00", "Họp 25:00", NONE, False, None),
    ("Họp 15:60", "Họp 15:60", NONE, False, None),
    # --- all-day
    ("Họp cả ngày thứ 6", "Họp", day(10, 23), True, None),
    ("Họp cả ngày", "Họp", day(10, 20), True, None),
    ("Họp cả ngày 15:00", "Họp", day(10, 20), True, None),
    # --- recurrence
    ("Tập gym hàng ngày 18h", "Tập gym", at(10, 20, 18), False, "FREQ=DAILY"),
    ("Họp hàng tuần thứ 6 15h", "Họp", at(10, 23, 15), False, "FREQ=WEEKLY;BYDAY=FR"),
    ("Họp hàng tuần 9h", "Họp", at(10, 21, 9), False, "FREQ=WEEKLY;BYDAY=WE"),
    ("Họp mỗi thứ 2 9h", "Họp", at(10, 26, 9), False, "FREQ=WEEKLY;BYDAY=MO"),
    ("Họp mỗi chủ nhật", "Họp", day(10, 25), True, "FREQ=WEEKLY;BYDAY=SU"),
    ("Họp hàng tháng 5/11", "Họp", day(11, 5), True, "FREQ=MONTHLY"),
    ("Sinh nhật hàng năm 5/1", "Sinh nhật", day(1, 5, 2027), True, "FREQ=YEARLY"),
    ("Họp mỗi ngày 8h", "Họp", at(10, 21, 8), False, "FREQ=DAILY"),
    ("Họp mỗi tuần", "Họp", day(10, 20), True, "FREQ=WEEKLY;BYDAY=TU"),
    # --- misc
    ("   Họp   với   Tuấn   mai   9h  ", "Họp với Tuấn", at(10, 21, 9), False, None),
    ("", "", NONE, False, None),
    ("   ", "", NONE, False, None),
    ("Mua sữa", "Mua sữa", NONE, False, None),
]


@pytest.mark.parametrize("text,title,when,all_day,rrule", CASES)
def test_parse(text, title, when, all_day, rrule):
    r = parse(text, now=NOW)
    assert r.title == title
    assert (r.start, r.end) == when
    assert r.all_day is all_day
    assert r.rrule == rrule


def _spans(text):
    r = parse(text, now=NOW)
    return [(s.kind, r.text[s.start:s.end]) for s in r.spans]


def test_spans_slices():
    assert _spans("Meeting với Tuấn thứ 6 15:00") == [("date", "thứ 6"), ("time", "15:00")]


def test_spans_include_prefix():
    assert _spans("Họp lúc 9h") == [("time", "lúc 9h")]


def test_spans_range():
    assert _spans("Họp 15:00-16:30") == [("range", "15:00-16:30")]


def test_spans_sorted_by_position():
    r = parse("15:00 thứ 6 họp", now=NOW)
    assert [(s.kind) for s in r.spans] == ["time", "date"]
    assert r.title == "họp"
    assert r.start == datetime(2026, 10, 23, 15, 0)


def test_decomposed_unicode_input():
    nfd = unicodedata.normalize("NFD", "Họp với Tuấn thứ 6 15:00")
    r = parse(nfd, now=NOW)
    assert r.title == unicodedata.normalize("NFC", "Họp với Tuấn")
    assert r.start == datetime(2026, 10, 23, 15, 0)


@pytest.mark.parametrize("junk", [
    "thứ", "thứ 9", "15:", "h30", "20/", "/10", "ngày", "hàng", "mỗi thứ",
    "tuần", "từ 9h đến", "9h-", "-", "cả", "!!!@@@ ###", "0/0", "99/99/9999",
    "x" * 5000,
])
def test_never_crashes(junk):
    r = parse(junk, now=NOW)
    assert isinstance(r.title, str)