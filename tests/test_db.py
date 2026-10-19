import pytest

from cal.core import database
from cal.core.database import Database
from cal.core.models import event_t

@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "cal.db")
    yield d
    d.close()

def test_fresh_db_is_latest_version(db):
    v = db.conn.execute("PRAGMA user_version").fetchone()[0]
    assert v == len(database.MIGRATIONS)

def test_crud_roundtrip(db):
    ev = event_t(title="Meeting", start_ts=1000, end_ts=2000, notes="x")
    eid = db.add_event(ev)
    got = db.get_event(eid)
    assert got is not None
    assert (got.title, got.start_ts, got.end_ts, got.notes) == ("Meeting", 1000, 2000, "x")
    assert got.all_day is False and got.rrule is None

    got.title = "Renamed"
    got.all_day = True
    db.update_event(got)
    again = db.get_event(eid)
    assert again.title == "Renamed" and again.all_day is True

    assert db.delete_event(eid) is True
    assert db.get_event(eid) is None
    assert db.delete_event(eid) is False

def test_update_missing_raises(db):
    with pytest.raises(KeyError):
        db.update_event(event_t(title="x", start_ts=1, end_ts=2, id=999))

def test_invalid_range_rejected(db):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        db.add_event(event_t(title="bad", start_ts=10, end_ts=5))

def test_events_in_range(db):
    db.add_event(event_t(title="before", start_ts=0, end_ts=100))
    db.add_event(event_t(title="ends_at_start", start_ts=150, end_ts=200))  # end == start khoảng: loại
    db.add_event(event_t(title="straddle", start_ts=190, end_ts=400))
    db.add_event(event_t(title="inside", start_ts=210, end_ts=250))
    db.add_event(event_t(title="point", start_ts=300, end_ts=300))
    db.add_event(event_t(title="starts_at_end", start_ts=450, end_ts=500))  # start == end khoảng: loại
    db.add_event(event_t(title="after", start_ts=500, end_ts=600))
    db.add_event(event_t(title="weekly", start_ts=0, end_ts=60, rrule="FREQ=WEEKLY"))
    titles = [e.title for e in db.events_in_range(200, 450)]
    assert titles == ["weekly", "straddle", "inside", "point"]

def test_reopen_keeps_data_and_no_backup(tmp_path):
    p = tmp_path / "cal.db"
    d1 = Database(p)
    d1.add_event(event_t(title="keep", start_ts=1, end_ts=2))
    d1.close()
    d2 = Database(p)
    assert len(d2.events_in_range(0, 10)) == 1
    d2.close()
    assert not (tmp_path / "backups").exists()

def test_migration_creates_backup(tmp_path, monkeypatch):
    p = tmp_path / "cal.db"
    d1 = Database(p)
    d1.add_event(event_t(title="keep", start_ts=1, end_ts=2))
    d1.close()

    monkeypatch.setattr(
        database, "MIGRATIONS",
        database.MIGRATIONS + ["ALTER TABLE events ADD COLUMN extra TEXT;"],
    )
    d2 = Database(p)
    assert d2.conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert len(list((tmp_path / "backups").glob("cal-v1-*.db"))) == 1
    assert len(d2.events_in_range(0, 10)) == 1
    d2.close()