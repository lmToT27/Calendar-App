#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <optional>
#include <string>
#include <vector>

#include "event.hpp"

namespace py = pybind11;

static int add(int a, int b) { return a + b; }

static std::vector<cal::event_t> sort_events(std::vector<cal::event_t> v) {
    std::stable_sort(v.begin(), v.end(),
                     [](const cal::event_t& a, const cal::event_t& b) {
                         if (a.start_ts != b.start_ts) return a.start_ts < b.start_ts;
                         return a.id.value_or(0) < b.id.value_or(0);
                     });
    return v;
}

PYBIND11_MODULE(_core, m) {
    m.doc() = "CAL core engine";
    m.def("add", &add, "Smoke-test function");
    m.def("sort_events", &sort_events, py::arg("events"));

    py::class_<cal::event_t>(m, "event_t")
        .def(py::init([](std::string title, int64_t start_ts, int64_t end_ts,
                         bool all_day, std::string notes,
                         std::optional<std::string> rrule,
                         std::optional<int64_t> id, int64_t created_at,
                         int64_t updated_at) {
                 cal::event_t e;
                 e.id = id;
                 e.title = std::move(title);
                 e.start_ts = start_ts;
                 e.end_ts = end_ts;
                 e.all_day = all_day;
                 e.notes = std::move(notes);
                 e.rrule = std::move(rrule);
                 e.created_at = created_at;
                 e.updated_at = updated_at;
                 return e;
             }),
             py::arg("title"), py::arg("start_ts"), py::arg("end_ts"),
             py::arg("all_day") = false, py::arg("notes") = std::string(),
             py::arg("rrule") = py::none(), py::arg("id") = py::none(),
             py::arg("created_at") = 0, py::arg("updated_at") = 0)
        .def_readwrite("id", &cal::event_t::id)
        .def_readwrite("title", &cal::event_t::title)
        .def_readwrite("start_ts", &cal::event_t::start_ts)
        .def_readwrite("end_ts", &cal::event_t::end_ts)
        .def_readwrite("all_day", &cal::event_t::all_day)
        .def_readwrite("notes", &cal::event_t::notes)
        .def_readwrite("rrule", &cal::event_t::rrule)
        .def_readwrite("created_at", &cal::event_t::created_at)
        .def_readwrite("updated_at", &cal::event_t::updated_at)
        .def(py::self == py::self)
        .def("__repr__", [](const cal::event_t& e) {
            return "<_core.event_t " + py::repr(py::cast(e.title)).cast<std::string>() +
                   " " + std::to_string(e.start_ts) + ".." +
                   std::to_string(e.end_ts) + ">";
        });
}