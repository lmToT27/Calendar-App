import pytest

from cal.core.commands import (CallableAction, Command, CommandRegistry,
                               History)

def label_of(action):
    assert action is not None
    return action.label


def id_of(cmd):
    assert cmd is not None
    return cmd.id

def make_registry():
    calls = []
    reg = CommandRegistry()
    reg.register(Command("event.new", "Tạo sự kiện", lambda: calls.append("new"), ("n",)))
    reg.register(Command("event.delete", "Xoá sự kiện", lambda: calls.append("del"), ("Delete",)))
    return reg, calls


def test_register_run_and_canonical_keys():
    reg, calls = make_registry()
    assert reg.keys_for("event.new") == ("N",)
    assert reg.run("event.new") is True
    assert calls == ["new"]
    assert id_of(reg.find_by_key("n")) == "event.new"
    assert id_of(reg.find_by_key("del")) == "event.delete"
    assert reg.find_by_key("???") is None
    assert reg.find_by_key("X") is None


def test_duplicate_id_and_default_key_conflict():
    reg, _ = make_registry()
    with pytest.raises(ValueError):
        reg.register(Command("event.new", "x", lambda: None))
    with pytest.raises(ValueError):
        reg.register(Command("other", "x", lambda: None, ("N",)))


def test_run_unknown_raises():
    reg, _ = make_registry()
    with pytest.raises(KeyError):
        reg.run("nope")


def test_run_catches_errors_and_reports():
    reg = CommandRegistry()
    seen = []
    reg.on_error = lambda cmd, exc: seen.append((cmd.id, str(exc)))

    def boom():
        raise RuntimeError("hỏng")

    reg.register(Command("x", "X", boom))
    assert reg.run("x") is False
    assert seen == [("x", "hỏng")]


def test_apply_keybinds():
    reg, _ = make_registry()
    reg.apply_keybinds({"event.new": ["A"]})
    assert reg.find_by_key("n") is None
    assert id_of(reg.find_by_key("a")) == "event.new"
    assert reg.keys_for("event.delete") == ("Delete",)
    with pytest.raises(ValueError):
        reg.apply_keybinds({"event.new": ["Delete"]})
    with pytest.raises(KeyError):
        reg.apply_keybinds({"nope": ["A"]})
    assert id_of(reg.find_by_key("a")) == "event.new"  # lỗi không làm hỏng trạng thái


def test_load_keybinds_file(tmp_path):
    reg, _ = make_registry()
    p = tmp_path / "keybinds.json"
    p.write_text('{"event.new": "A", "event.delete": "A"}', encoding="utf-8")
    result = reg.load_keybinds_file(p)
    assert result.errors
    assert reg.keys_for("event.new") == ("N",)
    assert reg.keys_for("event.delete") == ("Delete",)


def test_history_undo_redo():
    log = []
    h = History()
    h.perform(CallableAction("a", lambda: log.append("do a"), lambda: log.append("undo a")))
    h.perform(CallableAction("b", lambda: log.append("do b"), lambda: log.append("undo b")))
    assert label_of(h.undo()) == "b"
    assert label_of(h.undo()) == "a"
    assert h.undo() is None
    assert label_of(h.redo()) == "a"
    assert log == ["do a", "do b", "undo b", "undo a", "do a"]


def test_new_action_clears_redo():
    h = History()
    def noop():
        return None
    h.perform(CallableAction("a", noop, noop))
    h.undo()
    assert h.can_redo
    h.perform(CallableAction("b", noop, noop))
    assert not h.can_redo and h.redo() is None


def test_history_limit():
    h = History(limit=2)
    def noop():
        return None
    for name in "abc":
        h.perform(CallableAction(name, noop, noop))
    assert [label_of(h.undo()), label_of(h.undo()), h.undo()] == ["c", "b", None]


def test_failed_do_not_recorded():
    h = History()

    def bad():
        raise RuntimeError

    with pytest.raises(RuntimeError):
        h.perform(CallableAction("a", bad, lambda: None))
    assert not h.can_undo


def test_failed_undo_keeps_stack():
    h = History()
    state = {"fail": True}

    def undo():
        if state["fail"]:
            raise RuntimeError

    h.perform(CallableAction("a", lambda: None, undo))
    with pytest.raises(RuntimeError):
        h.undo()
    assert h.can_undo and not h.can_redo
    state["fail"] = False
    assert label_of(h.undo()) == "a"