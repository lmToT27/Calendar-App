import itertools
import random
import time

import pytest

from cal import _core

CONSEC = 8
WORD_START = 10
LEAD_CAP = 3
SEPS = " _-/.:"


def score_positions(c, pos):
    s = 0
    for i, p in enumerate(pos):
        if p == 0 or c[p - 1] in SEPS:
            s += WORD_START
        if i == 0:
            s -= min(p, LEAD_CAP)
        else:
            gap = p - pos[i - 1] - 1
            s += CONSEC if gap == 0 else -gap
    return s


def brute(query, c):
    q = query.replace(" ", "")
    if len(q) > len(c):
        return None
    best = None
    for pos in itertools.combinations(range(len(c)), len(q)):
        if all(c[p] == ch for p, ch in zip(pos, q)):
            s = score_positions(c, pos)
            if best is None or s > best:
                best = s
    return best


def run(query, cands, limit=1000):
    return _core.fuzzy_search(query, cands, limit)


@pytest.mark.parametrize("q", ["", "   "])
def test_empty_query_returns_all_in_order(q):
    cands = ["b", "a", "c"]
    res = run(q, cands)
    assert [(m.index, m.score, list(m.positions)) for m in res] == [
        (0, 0, []), (1, 0, []), (2, 0, [])]


def test_limit():
    cands = ["a", "ab", "abc"]
    assert len(run("a", cands, 2)) == 2
    assert run("a", cands, 0) == []
    assert run("a", cands, -5) == []
    assert len(run("", cands, 2)) == 2
    assert run("", cands, 0) == []


def test_no_match_cases():
    assert run("d", ["abc"]) == []
    assert run("ba", ["ab"]) == []          # sai thứ tự
    assert run("abcd", ["abc"]) == []       # query dài hơn candidate
    assert run("aaa", ["aa"]) == []         # ký tự lặp không đủ
    assert run("a", [""]) == []             # candidate rỗng
    assert run("a", []) == []               # không có candidate


def test_word_start_beats_inner_match():
    res = run("nt", ["interstellar", "new task"])
    assert [m.index for m in res] == [1, 0]


def test_spaces_in_query_ignored():
    cands = ["new task", "next tab", "interstellar"]
    a = [(m.index, m.score) for m in run("n t", cands)]
    b = [(m.index, m.score) for m in run("nt", cands)]
    assert a == b and a


def test_deterministic():
    cands = ["abab", "aabb", "baba", "ab ab"]
    first = [(m.index, m.score, list(m.positions)) for m in run("ab", cands)]
    for _ in range(5):
        again = [(m.index, m.score, list(m.positions)) for m in run("ab", cands)]
        assert again == first


def test_tie_break_shorter_then_index():
    res = run("a", ["xa", "a", "ya"])
    # "a" có điểm cao nhất (khớp đầu từ); "xa" và "ya" hoà điểm và độ dài -> index tăng
    assert [m.index for m in res] == [1, 0, 2]


def test_matches_bruteforce_random():
    rng = random.Random(12345)
    alphabet = "ab _-"
    for _ in range(300):
        cands = ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
                 for _ in range(25)]
        q = "".join(rng.choice("ab_") for _ in range(rng.randint(1, 4)))
        expected = []
        for i, c in enumerate(cands):
            s = brute(q, c)
            if s is not None:
                expected.append((-s, len(c), i))
        expected.sort()
        res = run(q, cands)
        assert [(m.index, m.score) for m in res] == [(i, -ns) for ns, _, i in expected], (q, cands)
        for m in res:
            pos = list(m.positions)
            c = cands[m.index]
            assert len(pos) == len(q.replace(" ", ""))
            assert all(a < b for a, b in zip(pos, pos[1:]))
            assert all(c[p] == ch for p, ch in zip(pos, q))
            assert score_positions(c, pos) == m.score


def test_limit_takes_top_results():
    rng = random.Random(7)
    cands = ["".join(rng.choice("abc _") for _ in range(rng.randint(1, 10)))
             for _ in range(60)]
    full = [(m.index, m.score) for m in run("ab", cands)]
    top = [(m.index, m.score) for m in run("ab", cands, 5)]
    assert top == full[:5]


def test_large_list_is_fast():
    rng = random.Random(1)
    cands = ["".join(rng.choice("abcdefgh _") for _ in range(30)) for _ in range(10000)]
    t = time.perf_counter()
    res = run("abc", cands, 20)
    assert time.perf_counter() - t < 2.0
    assert len(res) <= 20


def test_non_ascii_bytes_do_not_crash():
    res = run("t", ["tạo", "sự kiện"])
    assert isinstance(res, list)