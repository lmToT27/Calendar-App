"""DateParser V1 (Vietnamese): turns a quick-add sentence into title + time."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

DEFAULT_DURATION = timedelta(minutes=60)

_BYDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
_WD_MAP = {"2": 0, "hai": 0, "3": 1, "ba": 1, "4": 2, "tu": 2, "5": 3,
           "nam": 3, "6": 4, "sau": 4, "7": 5, "bay": 5}
_FREQ_MAP = {"ngay": "DAILY", "tuan": "WEEKLY", "thang": "MONTHLY", "nam": "YEARLY"}
_EDGE_WORDS = {"vao", "luc"}
_PUNCT = " ,;:-–—"


@dataclass(frozen=True)
class Span:
    kind: str   # "range" | "time" | "date" | "allday" | "recur"
    start: int  # index into ParseResult.text
    end: int


@dataclass
class ParseResult:
    text: str                       # NFC-normalized original input
    title: str
    start: datetime | None = None   # naive local time
    end: datetime | None = None     # all-day: midnight of the day AFTER the last day
    all_day: bool = False
    rrule: str | None = None
    spans: list[Span] = field(default_factory=list)


def normalize(text: str) -> tuple[str, str]:
    """Return (orig, norm): orig is NFC; norm is lowercase without diacritics.
    len(norm) == len(orig), so indices are interchangeable."""
    orig = unicodedata.normalize("NFC", text)
    out: list[str] = []
    for ch in orig:
        if ch in "đĐ":
            out.append("d")
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch)
                       if not unicodedata.combining(c)).lower()
        out.append(base if len(base) == 1 else " ")
    norm = "".join(out)
    assert len(norm) == len(orig)
    return orig, norm


_L = r"(?<![a-z0-9])"
_R = r"(?![a-z0-9])"
_PRE = r"(?:(?:vao\s+luc|vao|luc)\s+)?"
_T = r"(\d{1,2})(?::(\d{2})|h(\d{2})?)"
_NEXT_WEEK = r"tuan\s+(?:sau|toi)"
_WD = r"(?:thu\s+(2|3|4|5|6|7|hai|ba|tu|nam|sau|bay)|chu\s*nhat)"

_RANGE_RE = re.compile(
    _L + r"(?:(?:tu|vao\s+luc|vao|luc)\s+)?" + _T + r"\s*(?:-|–|—|den)\s*" + _T + _R)
_TIME_RE = re.compile(_L + _PRE + _T + _R)
_ALLDAY_RE = re.compile(_L + r"ca\s+ngay" + _R)
_RECUR_WD_RE = re.compile(_L + r"moi\s+" + _WD + _R)
_RECUR_RE = re.compile(_L + r"(?:hang|moi)\s+(ngay|tuan|thang|nam)" + _R)
_DATE_RE = re.compile(
    _L + r"(?:(?:vao\s+)?ngay\s+)?(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?" + _R)
_REL_RE = re.compile(_L + _PRE + r"(hom\s+nay|ngay\s+mai|ngay\s+mot|mai|mot)" + _R)
_WD_RE = re.compile(
    _L + _PRE + r"(?:(" + _NEXT_WEEK + r")\s+)?" + _WD
    + r"(?:\s+(" + _NEXT_WEEK + r"))?" + _R)
_NEXTWEEK_RE = re.compile(_L + _NEXT_WEEK + _R)


def _hm(h: str, m1: str | None, m2: str | None) -> time | None:
    hh, mm = int(h), int(m1 or m2 or 0)
    if hh > 23 or mm > 59:
        return None
    return time(hh, mm)


def _wd_index(token: str | None) -> int:
    return 6 if token is None else _WD_MAP[token]  # None -> "chủ nhật"


def _make_date(d: str, m: str, y: str | None, today: date) -> date | None:
    try:
        if y is None:
            cand = date(today.year, int(m), int(d))
            return cand if cand >= today else date(today.year + 1, int(m), int(d))
        yy = int(y) + (2000 if len(y) == 2 else 0)
        return date(yy, int(m), int(d))
    except ValueError:
        return None


def _clean_title(orig: str, taken: list[bool]) -> str:
    chars = [" " if t else c for c, t in zip(orig, taken)]
    title = " ".join("".join(chars).split()).strip(_PUNCT)
    words = title.split(" ") if title else []
    while words and normalize(words[-1])[1] in _EDGE_WORDS:
        words.pop()
    while words and normalize(words[0])[1] in _EDGE_WORDS:
        words.pop(0)
    return " ".join(words).strip(_PUNCT)


def parse(text: str, now: datetime | None = None) -> ParseResult:
    now = now or datetime.now()
    today = now.date()
    orig, norm = normalize(text)
    taken = [False] * len(norm)
    spans: list[Span] = []

    def free(m: re.Match) -> bool:
        return not any(taken[m.start():m.end()])

    def take(kind: str, m: re.Match) -> None:
        s, e = m.span()
        taken[s:e] = [True] * (e - s)
        spans.append(Span(kind, s, e))

    t_start: time | None = None
    t_end: time | None = None
    all_day_flag = False
    freq: str | None = None
    recur_wd: int | None = None
    dsrc: tuple | None = None  # ("fixed", date) | ("wd", weekday, next_week)

    # --- recognition, in priority order; first match of each category wins ---
    for m in _RANGE_RE.finditer(norm):
        a, b = _hm(*m.group(1, 2, 3)), _hm(*m.group(4, 5, 6))
        if t_start is None and a is not None and b is not None and free(m):
            t_start, t_end = a, b
            take("range", m)

    for m in _ALLDAY_RE.finditer(norm):
        if free(m):
            all_day_flag = True
            take("allday", m)
            break

    for m in _RECUR_WD_RE.finditer(norm):
        if freq is None and free(m):
            recur_wd, freq = _wd_index(m.group(1)), "WEEKLY"
            take("recur", m)

    for m in _RECUR_RE.finditer(norm):
        if freq is None and free(m):
            freq = _FREQ_MAP[m.group(1)]
            take("recur", m)

    for m in _DATE_RE.finditer(norm):
        if dsrc is None and free(m):
            d = _make_date(m.group(1), m.group(2), m.group(3), today)
            if d is not None:
                dsrc = ("fixed", d)
                take("date", m)

    for m in _REL_RE.finditer(norm):
        if dsrc is not None or not free(m):
            continue
        g, (gs, ge) = m.group(1), m.span(1)
        if g == "mai" and not orig[gs].islower():
            continue  # likely the name "Mai"
        if g in ("mot", "ngay mot") and "ố" not in orig[gs:ge].lower():
            continue  # "một" (one), not "mốt"
        offset = 0 if g.startswith("hom") else 1 if g.endswith("mai") else 2
        dsrc = ("fixed", today + timedelta(days=offset))
        take("date", m)

    for m in _WD_RE.finditer(norm):
        if dsrc is None and free(m):
            dsrc = ("wd", _wd_index(m.group(2)), bool(m.group(1) or m.group(3)))
            take("date", m)

    for m in _NEXTWEEK_RE.finditer(norm):
        if dsrc is None and free(m):
            dsrc = ("fixed", today + timedelta(days=7))
            take("date", m)

    for m in _TIME_RE.finditer(norm):
        t = _hm(*m.group(1, 2, 3))
        if t_start is None and t is not None and free(m):
            t_start = t
            take("time", m)

    # --- resolution ---
    if dsrc is None and recur_wd is not None:
        dsrc = ("wd", recur_wd, False)

    d: date | None = None
    if dsrc is not None:
        if dsrc[0] == "fixed":
            d = dsrc[1]
        else:
            _, wd, next_week = dsrc
            if next_week:
                d = today - timedelta(days=today.weekday()) + timedelta(days=7 + wd)
            else:
                d = today + timedelta(days=(wd - today.weekday()) % 7)
                if (d == today and t_start is not None
                        and datetime.combine(d, t_start) <= now):
                    d += timedelta(days=7)
    elif t_start is not None and not all_day_flag:
        d = today
        if datetime.combine(d, t_start) <= now:
            d += timedelta(days=1)
    elif all_day_flag or freq is not None:
        d = today

    start: datetime | None = None
    end: datetime | None = None
    all_day = False
    if d is not None:
        if all_day_flag or t_start is None:
            all_day = True
            start = datetime.combine(d, time.min)
            end = start + timedelta(days=1)
        else:
            start = datetime.combine(d, t_start)
            if t_end is None or t_end == t_start:
                end = start + DEFAULT_DURATION
            else:
                end = datetime.combine(d, t_end)
                if end < start:
                    end += timedelta(days=1)

    rrule: str | None = None
    if freq is not None and d is not None:
        if freq == "WEEKLY":
            byday = recur_wd if recur_wd is not None else d.weekday()
            rrule = f"FREQ=WEEKLY;BYDAY={_BYDAY[byday]}"
        else:
            rrule = f"FREQ={freq}"

    spans.sort(key=lambda s: s.start)
    return ParseResult(text=orig, title=_clean_title(orig, taken), start=start,
                       end=end, all_day=all_day, rrule=rrule, spans=spans)