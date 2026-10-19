import pytest

from cal import _core
from cal.core.database import Database
from cal.core.models import event_t, from_core, to_core


def test_roundtrip_full():
    ev = event_t(
        title="Họp với Tuấn", start_ts=1_760_000_000, end_ts=1_760_003_600,
        all_day=False, notes="Phòng 3\nmang laptop 🙂",
        rrule="FREQ=WEEKLY;BYDAY=FR", id=42, created_at=1, updated_at=2,
    )
    assert from_core(to_core(ev)) == ev


def test_roundtrip_none_fields():
    ev = event_t(title = "x", start_ts = 0, end_ts = 0)
    ce = to_core(ev)
    assert ce.id is None and ce.rrule is None
    assert from_core(ce) == ev


def test_negative_and_large_timestamps():
    ev = event_t(title="old", start_ts=-86400, end_ts=2**40)
    assert from_core(to_core(ev)) == ev


def test_int64_overflow_rejected():
    with pytest.raises(TypeError):
        _core.event_t(title="x", start_ts=2**63, end_ts=2**63)


def test_core_equality_and_mutation():
    a = _core.event_t(title="a", start_ts=1, end_ts=2)
    b = _core.event_t(title="a", start_ts=1, end_ts=2)
    assert a == b
    b.title = "b"
    assert a != b


def test_sort_events_from_cpp():
    starts = [30, 10, 20, 10]
    evs = [_core.event_t(title=str(i), start_ts=s, end_ts=s + 1, id=i)
           for i, s in enumerate(starts)]
    out = _core.sort_events(evs)
    assert [(e.start_ts, e.id) for e in out] == [(10, 1), (10, 3), (20, 2), (30, 0)]


def test_db_to_core_and_back(tmp_path):
    db = Database(tmp_path / "cal.db")
    eid = db.add_event(event_t(title="Họp", start_ts=100, end_ts=200, rrule="FREQ=DAILY"))
    got = db.get_event(eid)
    assert got is not None
    assert from_core(to_core(got)) == got
    db.close()