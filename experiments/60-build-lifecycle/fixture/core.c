#include <Python.h>
#include "value.h"
static PyObject *answer(PyObject *self, PyObject *args) {
    return PyLong_FromLong(ANSWER);
}
static PyMethodDef methods[] = {{"answer", answer, METH_NOARGS, "Fixture answer"}, {NULL, NULL, 0, NULL}};
static struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "bt60_core", NULL, -1, methods};
PyMODINIT_FUNC PyInit_bt60_core(void) { return PyModule_Create(&module); }
