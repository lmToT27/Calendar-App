import pytest

from cal.core.keybinds import (KeyParseError, load_keybinds, parse_key,
                               resolve_keybinds, to_tk_sequence)

DEFAULTS = {
    "event.new": ("N",),
    "event.delete": ("Delete",),
    "palette.open": ("Ctrl+Shift+P",),
    "edit.undo": ("Ctrl+Z",),
}


@pytest.mark.parametrize("spec,expected", [
    ("n", "N"), ("N", "N"), ("ctrl+shift+p", "Ctrl+Shift+P"),
    ("Shift+Ctrl+P", "Ctrl+Shift+P"), ("control+z", "Ctrl+Z"),
    ("Del", "Delete"), ("esc", "Escape"), ("return", "Enter"), ("f5", "F5"),
    ("alt+left", "Alt+Left"), ("1", "1"), (" Ctrl + P ", "Ctrl+P"),
    ("Ctrl+Alt+Delete", "Ctrl+Alt+Delete"), ("pagedown", "PageDown"),
])
def test_parse_key_ok(spec, expected):
    assert parse_key(spec) == expected


@pytest.mark.parametrize("spec", [
    "", "  ", "+", "Ctrl+", "Ctrl++", "Ctrl+Ctrl+P", "Foo+P", "Ctrl", "Shift",
    "Ctrl+Shift", "F13", "F0", "ctrl+é", "é", 123, None,
])
def test_parse_key_bad(spec):
    with pytest.raises(KeyParseError):
        parse_key(spec)


@pytest.mark.parametrize("canonical,tk", [
    ("N", "<n>"), ("Shift+N", "<Shift-N>"), ("Ctrl+Shift+P", "<Control-Shift-P>"),
    ("Ctrl+Z", "<Control-z>"), ("Delete", "<Delete>"), ("Enter", "<Return>"),
    ("Alt+Left", "<Alt-Left>"), ("Space", "<space>"), ("PageUp", "<Prior>"),
    ("F5", "<F5>"), ("1", "<1>"), ("Ctrl+Alt+Delete", "<Control-Alt-Delete>"),
])
def test_to_tk(canonical, tk):
    assert to_tk_sequence(canonical) == tk


def test_no_file_gives_defaults():
    r = resolve_keybinds(DEFAULTS, None)
    assert r.bindings == DEFAULTS and r.errors == []


def test_override_ok_and_case_insensitive():
    r = resolve_keybinds(DEFAULTS, {"event.new": "a", "palette.open": "ctrl+p"})
    assert r.bindings["event.new"] == ("A",)
    assert r.bindings["palette.open"] == ("Ctrl+P",)
    assert r.errors == []


def test_list_null_and_dedupe():
    r = resolve_keybinds(DEFAULTS, {
        "event.delete": ["Delete", "Backspace"], "edit.undo": None,
        "event.new": ["n", "N"]})
    assert r.bindings["event.delete"] == ("Delete", "Backspace")
    assert r.bindings["edit.undo"] == ()
    assert r.bindings["event.new"] == ("N",)
    assert r.errors == []


def test_unknown_command_ignored():
    r = resolve_keybinds(DEFAULTS, {"nope": "X"})
    assert r.bindings == DEFAULTS
    assert len(r.errors) == 1 and "nope" in r.errors[0]


@pytest.mark.parametrize("bad", ["Ctrl+", 5, {"a": 1}, ["N", "???"], ""])
def test_bad_value_keeps_default(bad):
    r = resolve_keybinds(DEFAULTS, {"event.new": bad})
    assert r.bindings == DEFAULTS
    assert len(r.errors) == 1 and "event.new" in r.errors[0]


def test_conflict_with_default_rejects_override():
    r = resolve_keybinds(DEFAULTS, {"event.new": "Delete"})
    assert r.bindings == DEFAULTS
    assert any("Trùng phím Delete" in e for e in r.errors)
    assert any("event.new" in e for e in r.errors)


def test_conflict_between_overrides_rejects_both():
    r = resolve_keybinds(DEFAULTS, {"event.new": "X", "edit.undo": "X"})
    assert r.bindings == DEFAULTS
    assert any("Trùng phím X" in e for e in r.errors)


def test_swap_is_valid():
    r = resolve_keybinds(DEFAULTS, {"event.new": "Delete", "event.delete": "N"})
    assert r.bindings["event.new"] == ("Delete",)
    assert r.bindings["event.delete"] == ("N",)
    assert r.errors == []


def test_cascading_conflicts():
    d = {"a": ("1",), "b": ("2",), "c": ("3",)}
    r = resolve_keybinds(d, {"b": "1", "c": "2"})
    assert r.bindings == d
    assert sum("Trùng phím" in e for e in r.errors) >= 2


def test_top_level_not_object():
    r = resolve_keybinds(DEFAULTS, ["x"])
    assert r.bindings == DEFAULTS and len(r.errors) == 1


def test_load_missing_file(tmp_path):
    r = load_keybinds(tmp_path / "keybinds.json", DEFAULTS)
    assert r.bindings == DEFAULTS and r.errors == []


def test_load_valid_file(tmp_path):
    p = tmp_path / "keybinds.json"
    p.write_text('{"event.new": "A"}', encoding="utf-8")
    r = load_keybinds(p, DEFAULTS)
    assert r.bindings["event.new"] == ("A",) and r.errors == []


@pytest.mark.parametrize("content", ["", "{bad json", "[1,2]", "null"])
def test_load_broken_file_falls_back(tmp_path, content):
    p = tmp_path / "keybinds.json"
    p.write_text(content, encoding="utf-8")
    r = load_keybinds(p, DEFAULTS)
    assert r.bindings == DEFAULTS
    assert len(r.errors) == 1


def test_load_invalid_utf8(tmp_path):
    p = tmp_path / "keybinds.json"
    p.write_bytes(b"\xff\xfe\x00bad")
    r = load_keybinds(p, DEFAULTS)
    assert r.bindings == DEFAULTS and len(r.errors) == 1