from dataclasses import dataclass

@dataclass
class Event:
    title: str
    start_ts: int
    end_ts: int
    all_day: bool = False
    notes: str = ""
    rrule: str | None = None
    id: int | None = None
    created_at: int = 0
    updated_at: int = 0