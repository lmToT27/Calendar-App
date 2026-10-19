from typing import Optional

class event_t:
    id: Optional[int]
    title: str
    start_ts: int
    end_ts: int
    all_day: bool
    notes: str
    rrule: Optional[str]
    created_at: int
    updated_at: int
    def __init__(
        self,
        title: str,
        start_ts: int,
        end_ts: int,
        all_day: bool = False,
        notes: str = "",
        rrule: Optional[str] = None,
        id: Optional[int] = None,
        created_at: int = 0,
        updated_at: int = 0,
    ) -> None: ...
    def __eq__(self, other: object) -> bool: ...

def add(a: int, b: int) -> int: ...
def sort_events(events: list[event_t]) -> list[event_t]: ...