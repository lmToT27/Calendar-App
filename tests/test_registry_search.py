import unicodedata

import pytest

from cal.core.commands import (Command, CommandRegistry, merge_positions,
                               to_search_text)


def make_reg():
    reg = CommandRegistry()
    def noop(): return None
    for cid, title in [
        ("event.new", "Tạo sự kiện mới"),
        ("event.delete", "Xoá sự kiện"),
        ("nav.today", "Đi tới hôm nay"),
        ("edit.undo", "Hoàn tác"),
        ("view.week", "Xem theo tuần"),
    ]:
        reg.register(Command(cid, title, noop))
    return reg


def ids(hits):
    return [h.command.id for h in hits]


def test_search_ignores_diacritics_and_case():
    reg = make_reg()
    assert ids(reg.search("tao"))[0] == "event.new"
    assert ids(reg.search("xoa"))[0] == "event.delete"
    assert ids(reg.search("HOAN tac"))[0] == "edit.undo"
    assert ids(reg.search("di toi")) == ["nav.today"]  # Đ -> d


def test_empty_query_returns_all_in_registration_order():
    reg = make_reg()
    hits = reg.search("")
    assert ids(hits) == ["event.new", "event.delete", "nav.today", "edit.undo", "view.week"]
    assert all(h.score == 0 and h.positions == () for h in hits)


def test_limit():
    assert len(make_reg().search("", limit=2)) == 2
    assert make_reg().search("", limit=0) == []


def test_positions_index_into_original_title():
    reg = make_reg()
    hits = reg.search("sk")
    assert ids(hits) == ["event.delete", "event.new"]  # hoà điểm -> tiêu đề ngắn hơn trước
    for h in hits:
        assert h.positions == (4, 7)
        assert [h.command.title[p] for p in h.positions] == ["s", "k"]


def test_command_registered_later_is_searchable():
    reg = make_reg()
    reg.register(Command("app.quit", "Thoát ứng dụng", lambda: None))
    assert ids(reg.search("thoat")) == ["app.quit"]


def test_title_is_normalized_to_nfc():
    reg = CommandRegistry()
    nfd = unicodedata.normalize("NFD", "Tạo sự kiện mới")
    reg.register(Command("event.new", nfd, lambda: None))
    title = reg.get("event.new").title
    assert title == unicodedata.normalize("NFC", nfd)
    hit = reg.search("sk")[0]
    assert [title[p] for p in hit.positions] == ["s", "k"]


@pytest.mark.parametrize("text", ["Tạo sự kiện", "Đi tới", "🙂 ok", "日本語", "e\u0301", "İstanbul", "ß"])
def test_search_text_keeps_length(text):
    assert len(to_search_text(text)) == len(unicodedata.normalize("NFC", text))
    assert to_search_text(text).isascii()


def test_non_latin_query_does_not_crash():
    assert isinstance(make_reg().search("日本"), list)


@pytest.mark.parametrize("positions,expected", [
    ([], []), ([5], [(5, 6)]), ([1, 2, 3, 7], [(1, 4), (7, 8)]), ([0, 2, 4], [(0, 1), (2, 3), (4, 5)]),
])
def test_merge_positions(positions, expected):
    assert merge_positions(positions) == expected