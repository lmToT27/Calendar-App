#pragma once
#include <string>
#include <vector>

namespace cal {

struct Match {
    int index;
    int score;
    std::vector <int> positions;
};

std::vector<Match> fuzzy_search(const std::string &query,
                                const std::vector <std::string> &candidates,
                                int limit);

}  // namespace cal