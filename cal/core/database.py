from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from .models import Event

log = logging.getLogger(__name__)

MIGRATIONS: list[str] = [
    """
    CREATE TABLE events (
        id         INTEGER PRIMARY KEY,
        title      TEXT NOT NULL,
        start_ts   INTEGER NOT NULL,
        end_ts     INTEGER NOT NULL,
        all_day    INTEGER NOT NULL DEFAULT 0,
        notes      TEXT NOT NULL DEFAULT '',
        rrule      TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        CHECK (end_ts >= start_ts)
    );
    CREATE INDEX idx_events_start ON events(start_ts);

    CREATE TABLE reminders (
        id         INTEGER PRIMARY KEY,
        event_id   INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
        offset_min INTEGER NOT NULL,
        fired_at   INTEGER
    );

    CREATE TABLE exceptions (
        event_id       INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
        occurrence_ts  INTEGER NOT NULL,
        kind           TEXT NOT NULL CHECK (kind IN ('skip', 'override')),
        override_event TEXT,
        PRIMARY KEY (event_id, occurrence_ts)
    );
    """,
]


class Database:
    def __init__(self, path: Path | str, backup_dir: Path | str | None = None):
        self.path = Path(path)
        self.backup_dir = (
            Path(backup_dir) if backup_dir else self.path.parent / "backups"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    # ---- migration -------------------------------------------------------
    def _migrate(self) -> None:
        current = self.conn.execute("PRAGMA user_version").fetchone()[0]
        target = len(MIGRATIONS)
        if current > target:
            raise RuntimeError(
                f"DB version {current} is newer than this app ({target})"
            )
        if current == target:
            return
        if current > 0:
            self._backup(current)
        for version in range(current, target):
            script = (
                "BEGIN;\n"
                f"{MIGRATIONS[version]}\n"
                f"PRAGMA user_version = {version + 1};\n"
                "COMMIT;"
            )
            try:
                self.conn.executescript(script)
            except sqlite3.Error:
                if self.conn.in_transaction:
                    self.conn.rollback()
                log.exception("Migration to v%d failed", version + 1)
                raise
            log.info("Migrated DB to v%d", version + 1)

    def _backup(self, version: int) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        dest = self.backup_dir / f"{self.path.stem}-v{version}-{stamp}.db"
        dst = sqlite3.connect(dest)
        try:
            self.conn.backup(dst)
        finally:
            dst.close()
        log.info("Backup written: %s", dest)
        return dest

    # ---- CRUD ------------------------------------------------------------
    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> Event:
        return Event(
            id=row["id"],
            title=row["title"],
            start_ts=row["start_ts"],
            end_ts=row["end_ts"],
            all_day=bool(row["all_day"]),
            notes=row["notes"],
            rrule=row["rrule"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_event(self, ev: Event) -> int:
        now = int(time.time())
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO events (title, start_ts, end_ts, all_day, notes,"
                " rrule, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (ev.title, ev.start_ts, ev.end_ts, int(ev.all_day), ev.notes,
                 ev.rrule, now, now),
            )
        new_id = cur.lastrowid
        assert new_id is not None
        ev.id, ev.created_at, ev.updated_at = new_id, now, now
        return new_id

    def get_event(self, event_id: int) -> Event | None:
        row = self.conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def update_event(self, ev: Event) -> None:
        if ev.id is None:
            raise ValueError("Event has no id")
        now = int(time.time())
        with self.conn:
            cur = self.conn.execute(
                "UPDATE events SET title=?, start_ts=?, end_ts=?, all_day=?,"
                " notes=?, rrule=?, updated_at=? WHERE id=?",
                (ev.title, ev.start_ts, ev.end_ts, int(ev.all_day), ev.notes,
                 ev.rrule, now, ev.id),
            )
        if cur.rowcount == 0:
            raise KeyError(ev.id)
        ev.updated_at = now

    def delete_event(self, event_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM events WHERE id = ?", (event_id,)
            )
        return cur.rowcount > 0

    def events_in_range(self, start_ts: int, end_ts: int) -> list[Event]:
        """Event giao với [start_ts, end_ts), cộng mọi event lặp bắt đầu
        trước end_ts (việc mở rộng các lần lặp làm ở recurrence, M5)."""
        rows = self.conn.execute(
            "SELECT * FROM events WHERE start_ts < :e AND"
            " (rrule IS NOT NULL OR end_ts > :s OR start_ts >= :s)"
            " ORDER BY start_ts, id",
            {"s": start_ts, "e": end_ts},
        ).fetchall()
        return [self._row_to_event(r) for r in rows]