from dataclasses import dataclass
from cal import _core

@dataclass
class event_t:
    title: str
    start_ts: int
    end_ts: int
    all_day: bool = False
    notes: str = ""
    rrule: str | None = None
    id: int | None = None
    created_at: int = 0
    updated_at: int = 0

def to_core(ev: event_t) -> _core.event_t:
    return _core.event_t(
        title=ev.title, start_ts=ev.start_ts, end_ts=ev.end_ts,
        all_day=ev.all_day, notes=ev.notes, rrule=ev.rrule,
        id=ev.id, created_at=ev.created_at, updated_at=ev.updated_at,
    )

def from_core(ce: _core.event_t) -> event_t:
    return event_t(
        title=ce.title, start_ts=ce.start_ts, end_ts=ce.end_ts,
        all_day=ce.all_day, notes=ce.notes, rrule=ce.rrule,
        id=ce.id, created_at=ce.created_at, updated_at=ce.updated_at,
    )