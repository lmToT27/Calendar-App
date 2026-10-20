#pragma once
#include <cstdint>
#include <optional>
#include <string>

namespace cal {

struct Event {
    std::optional <int64_t> id;
    std::string title;
    int64_t start_ts = 0;
    int64_t end_ts = 0;
    bool all_day = false;
    std::string notes;
    std::optional <std::string> rrule;
    int64_t created_at = 0;
    int64_t updated_at = 0;

    bool operator == (const Event& other) const {
        if (id != other.id) return false;
        if (title != other.title) return false;
        if (start_ts != other.start_ts) return false;
        if (end_ts != other.end_ts) return false;
        if (all_day != other.all_day) return false;
        if (notes != other.notes) return false;
        if (rrule != other.rrule) return false;
        if (created_at != other.created_at) return false;
        if (updated_at != other.updated_at) return false;
        return true;
    }
};

}