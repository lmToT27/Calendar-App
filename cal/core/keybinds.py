"""Phân tích phím tắt và nạp keybinds.json."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

log = logging.getLogger(__name__)


class KeyParseError(ValueError):
    pass


_MOD_ORDER = ("Ctrl", "Alt", "Shift")
_MOD_ALIASES = {"ctrl": "Ctrl", "control": "Ctrl", "alt": "Alt", "shift": "Shift"}
_NAMED = {
    "enter": "Enter", "return": "Enter", "escape": "Escape", "esc": "Escape",
    "delete": "Delete", "del": "Delete", "backspace": "Backspace", "tab": "Tab",
    "space": "Space", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "PageUp", "pagedown": "PageDown",
}
_TK_KEYSYM = {
    "Enter": "Return", "Escape": "Escape", "Delete": "Delete",
    "Backspace": "BackSpace", "Tab": "Tab", "Space": "space", "Up": "Up",
    "Down": "Down", "Left": "Left", "Right": "Right", "Home": "Home",
    "End": "End", "PageUp": "Prior", "PageDown": "Next",
}
_TK_MOD = {"Ctrl": "Control", "Alt": "Alt", "Shift": "Shift"}
_FKEY = re.compile(r"f(?:[1-9]|1[0-2])$")


def _parse_base_key(key: str, spec: str) -> str:
    if len(key) == 1:
        if key.isascii() and key.isalnum():
            return key.upper()
        raise KeyParseError(f"'{spec}': phím '{key}' chưa được hỗ trợ")
    low = key.lower()
    if low in _NAMED:
        return _NAMED[low]
    if _FKEY.match(low):
        return low.upper()
    raise KeyParseError(f"'{spec}': không biết phím '{key}'")


def parse_key(spec: str) -> str:
    """'ctrl+shift+p' -> 'Ctrl+Shift+P'. Ném KeyParseError nếu sai."""
    if not isinstance(spec, str):
        raise KeyParseError(f"giá trị phím phải là chuỗi, nhận được {spec!r}")
    text = spec.strip()
    if not text:
        raise KeyParseError("phím rỗng (dùng null để bỏ gán phím)")
    parts = [p.strip() for p in text.split("+")]
    if any(not p for p in parts):
        raise KeyParseError(
            f"'{spec}': cú pháp sai (thiếu tên phím, hoặc dùng dấu '+' làm phím)")
    *mod_parts, key_part = parts
    mods: set[str] = set()
    for p in mod_parts:
        mod = _MOD_ALIASES.get(p.lower())
        if mod is None:
            raise KeyParseError(
                f"'{spec}': '{p}' không phải phím bổ trợ (Ctrl, Alt, Shift)")
        if mod in mods:
            raise KeyParseError(f"'{spec}': '{mod}' bị lặp")
        mods.add(mod)
    key = _parse_base_key(key_part, spec)
    return "+".join([m for m in _MOD_ORDER if m in mods] + [key])


def to_tk_sequence(canonical: str) -> str:
    """'Ctrl+Shift+P' -> '<Control-Shift-P>' (đầu vào phải là dạng chuẩn)."""
    *mods, key = canonical.split("+")
    if len(key) == 1 and key.isalpha():
        keysym = key if "Shift" in mods else key.lower()
    elif len(key) == 1:
        keysym = key
    else:
        keysym = _TK_KEYSYM.get(key, key)
    return "<" + "-".join([_TK_MOD[m] for m in mods] + [keysym]) + ">"


@dataclass
class KeybindResult:
    bindings: dict[str, tuple[str, ...]]  # command_id -> các phím chuẩn
    errors: list[str] = field(default_factory=list)


def _parse_value(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items: list[Any] = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise KeyParseError("giá trị phải là chuỗi, danh sách chuỗi hoặc null")
    out: list[str] = []
    for item in items:
        key = parse_key(item)
        if key not in out:
            out.append(key)
    return tuple(out)


def resolve_keybinds(defaults: Mapping[str, Sequence[str]], raw: Any) -> KeybindResult:
    """Trộn cấu hình người dùng (raw, đã json.loads; None = không có file)
    lên phím mặc định. Không bao giờ ném lỗi vì dữ liệu người dùng."""
    errors: list[str] = []
    base = {cid: tuple(keys) for cid, keys in defaults.items()}
    if raw is None:
        return KeybindResult(base, errors)
    if not isinstance(raw, dict):
        return KeybindResult(
            base, ['keybinds.json phải là một object {"lệnh": "phím"}; dùng phím mặc định'])

    overrides: dict[str, tuple[str, ...]] = {}
    for cid, value in raw.items():
        if cid not in base:
            errors.append(f"Lệnh không tồn tại: '{cid}' (bỏ qua)")
            continue
        try:
            overrides[cid] = _parse_value(value)
        except KeyParseError as e:
            errors.append(f"{cid}: {e} (giữ phím mặc định)")

    effective = {**base, **overrides}
    while True:
        owners: dict[str, list[str]] = {}
        for cid, keys in effective.items():
            for key in keys:
                owners.setdefault(key, []).append(cid)
        clashes = {k: c for k, c in owners.items() if len(c) > 1}
        if not clashes:
            break
        reverted: set[str] = set()
        for key, cids in clashes.items():
            errors.append(f"Trùng phím {key}: " + ", ".join(sorted(cids)))
            reverted.update(c for c in cids if c in overrides)
        if not reverted:
            raise ValueError("Phím mặc định bị trùng nhau (lỗi lập trình)")
        for cid in sorted(reverted):
            del overrides[cid]
            effective[cid] = base[cid]
            errors.append(f"{cid}: bỏ cấu hình tuỳ chỉnh, dùng phím mặc định")
    return KeybindResult(effective, errors)


def load_keybinds(path: Path, defaults: Mapping[str, Sequence[str]]) -> KeybindResult:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return resolve_keybinds(defaults, None)
    except (OSError, UnicodeDecodeError) as e:
        result = resolve_keybinds(defaults, None)
        result.errors.append(f"Không đọc được {path.name}: {e}; dùng phím mặc định")
        return result
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as e:
        result = resolve_keybinds(defaults, None)
        result.errors.append(
            f"{path.name}: JSON sai cú pháp (dòng {e.lineno}, cột {e.colno}): "
            f"{e.msg}; dùng phím mặc định")
        return result
    if raw is None:
        raw = "null"
    return resolve_keybinds(defaults, raw)