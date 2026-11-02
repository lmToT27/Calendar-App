#include "search.hpp"

#include <algorithm>
#include <cctype>
#include <climits>
#include <string>
#include <vector>

namespace cal {
namespace {

constexpr int START_WORD_POINT = 10;
constexpr int CONSECUTIVE_POINT = 8;
constexpr int MAX_PENALTY = 3;
constexpr int NEG_INF = INT_MIN / 2;

bool is_separator(char c) {
    return c == ' ' || c == '_' || c == '-' || c == '/' || c == '.' || c == ':';
}

bool is_word_start(const std::string &s, int p) {
    return p == 0 || is_separator(s[p - 1]);
}

bool is_subsequence(const std::string &q, const std::string &c) {
    size_t i = 0;
    for (size_t j = 0; j < c.size() && i < q.size(); ++j)
        if (c[j] == q[i]) ++i;
    return i == q.size();
}

int best_alignment(const std::string &q, const std::string &c,
                   std::vector <int> &positions) {
    const int k = static_cast<int>(q.size());
    const int n = static_cast<int>(c.size());

    std::vector <std::vector <int>> dp(k, std::vector <int> (n, NEG_INF));
    std::vector <std::vector <int>> parent(k, std::vector <int> (n, -1));

    for (int j = 0; j < n; ++j) {
        if (c[j] != q[0]) continue;
        dp[0][j] = (is_word_start(c, j) ? START_WORD_POINT : 0) - std::min(j, MAX_PENALTY);
    }

    for (int i = 1; i < k; ++i) {
        for (int j = i; j < n; ++j) {
            if (c[j] != q[i]) continue;
            const int ws = is_word_start(c, j) ? START_WORD_POINT : 0;
            int best = NEG_INF, best_prev = -1;
            for (int jp = i - 1; jp < j; ++jp) {
                if (dp[i - 1][jp] == NEG_INF) continue;
                const int gap = j - jp - 1;
                const int cand = dp[i - 1][jp] + (gap == 0 ? CONSECUTIVE_POINT : -gap);
                if (cand > best) {
                    best = cand;
                    best_prev = jp;
                }
            }
            if (best_prev != -1) {
                dp[i][j] = best + ws;
                parent[i][j] = best_prev;
            }
        }
    }

    int best = NEG_INF, best_j = -1;
    for (int j = 0; j < n; ++j) {
        if (dp[k - 1][j] > best) {
            best = dp[k - 1][j];
            best_j = j;
        }
    }

    positions.assign(k, 0);
    for (int i = k - 1, j = best_j; i >= 0; --i) {
        positions[i] = j;
        j = parent[i][j];
    }
    return best;
}

}  // namespace

std::vector <Match> fuzzy_search(const std::string &query,
                                const std::vector <std::string> &candidates,
                                int limit) {
    if (limit <= 0) return {};

    std::string q;
    for (unsigned char ch : query)
        if (!std::isspace(ch)) q.push_back(static_cast <char> (ch));

    std::vector <Match> result;

    if (q.empty()) {
        const size_t take = std::min(candidates.size(), static_cast <size_t> (limit));
        result.reserve(take);
        for (size_t i = 0; i < take; ++i)
            result.push_back(Match{static_cast <int> (i), 0, {}});
        return result;
    }

    for (size_t i = 0; i < candidates.size(); ++i) {
        const std::string &c = candidates[i];
        if (q.size() > c.size() || !is_subsequence(q, c)) continue;
        Match m;
        m.index = static_cast <int> (i);
        m.score = best_alignment(q, c, m.positions);
        result.push_back(std::move(m));
    }

    std::sort(result.begin(), result.end(), [&](const Match &a, const Match &b) {
        if (a.score != b.score) return a.score > b.score;
        const size_t la = candidates[a.index].size();
        const size_t lb = candidates[b.index].size();
        if (la != lb) return la < lb;
        return a.index < b.index;
    });

    if (result.size() > static_cast <size_t> (limit)) result.resize(limit);
    return result;
}

}  // namespace cal