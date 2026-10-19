#include <pybind11/pybind11.h>
namespace py = pybind11;

static int add(int a, int b) { return a + b; }

PYBIND11_MODULE(_core, m) {
    m.doc() = "CAL core engine";
    m.def("add", &add, "Smoke-test function");
}