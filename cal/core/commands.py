"""Command Registry và lịch sử undo/redo."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from . import keybinds as kb
from .keybinds import KeyParseError, parse_key

log = logging.getLogger(__name__)


# ---- undo / redo --------------------------------------------------------
class Action(Protocol):
    label: str

    def do(self) -> None: ...
    def undo(self) -> None: ...


@dataclass
class CallableAction:
    label: str
    do_fn: Callable[[], None]
    undo_fn: Callable[[], None]

    def do(self) -> None:
        self.do_fn()

    def undo(self) -> None:
        self.undo_fn()


class History:
    def __init__(self, limit: int = 200) -> None:
        self._undo: list[Action] = []
        self._redo: list[Action] = []
        self._limit = limit

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def perform(self, action: Action) -> None:
        action.do()  # nếu lỗi: không vào ngăn xếp
        self._undo.append(action)
        self._redo.clear()
        if len(self._undo) > self._limit:
            self._undo.pop(0)

    def undo(self) -> Action | None:
        if not self._undo:
            return None
        action = self._undo[-1]
        action.undo()  # nếu lỗi: giữ nguyên ngăn xếp
        self._undo.pop()
        self._redo.append(action)
        return action

    def redo(self) -> Action | None:
        if not self._redo:
            return None
        action = self._redo[-1]
        action.do()
        self._redo.pop()
        self._undo.append(action)
        return action

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()


# ---- registry -----------------------------------------------------------
@dataclass(frozen=True)
class Command:
    id: str                          # ổn định, dùng trong keybinds.json: "event.new"
    title: str                       # tên hiển thị trong palette
    run: Callable[[], None]          # Python hoặc hàm C++ bound
    keys: tuple[str, ...] = ()       # phím mặc định


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._defaults: dict[str, tuple[str, ...]] = {}
        self._bindings: dict[str, tuple[str, ...]] = {}
        self._by_key: dict[str, str] = {}
        self.on_error: Callable[[Command, Exception], None] | None = None

    def register(self, cmd: Command) -> None:
        if cmd.id in self._commands:
            raise ValueError(f"Lệnh trùng id: {cmd.id}")
        keys = tuple(dict.fromkeys(parse_key(k) for k in cmd.keys))
        for key in keys:
            if key in self._by_key:
                raise ValueError(
                    f"Phím mặc định {key} của '{cmd.id}' trùng với '{self._by_key[key]}'")
        self._commands[cmd.id] = replace(cmd, keys=keys)
        self._defaults[cmd.id] = keys
        self._bindings[cmd.id] = keys
        for key in keys:
            self._by_key[key] = cmd.id

    def get(self, command_id: str) -> Command:
        return self._commands[command_id]

    def commands(self) -> list[Command]:
        return list(self._commands.values())

    def defaults(self) -> dict[str, tuple[str, ...]]:
        return dict(self._defaults)

    def keys_for(self, command_id: str) -> tuple[str, ...]:
        return self._bindings[command_id]

    def find_by_key(self, spec: str) -> Command | None:
        try:
            key = parse_key(spec)
        except KeyParseError:
            return None
        cid = self._by_key.get(key)
        return self._commands[cid] if cid else None

    def apply_keybinds(self, bindings: Mapping[str, Sequence[str]]) -> None:
        new = dict(self._defaults)
        for cid, keys in bindings.items():
            if cid not in self._commands:
                raise KeyError(cid)
            new[cid] = tuple(parse_key(k) for k in keys)
        by_key: dict[str, str] = {}
        for cid, keys in new.items():
            for key in keys:
                if key in by_key:
                    raise ValueError(
                        f"Phím {key} bị gán cho cả '{by_key[key]}' và '{cid}'")
                by_key[key] = cid
        self._bindings, self._by_key = new, by_key

    def load_keybinds_file(self, path: Path) -> kb.KeybindResult:
        result = kb.load_keybinds(path, self._defaults)
        self.apply_keybinds(result.bindings)
        for msg in result.errors:
            log.warning("keybinds: %s", msg)
        return result

    def run(self, command_id: str) -> bool:
        cmd = self._commands[command_id]  # id sai = lỗi lập trình -> KeyError
        try:
            cmd.run()
        except Exception as exc:
            log.exception("Command '%s' failed", command_id)
            if self.on_error is not None:
                self.on_error(cmd, exc)
            return False
        return True