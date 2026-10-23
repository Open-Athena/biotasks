#include <Python.h>
static PyObject *answer(PyObject *self, PyObject *args) {
    return PyLong_FromLong(42);
}
static PyMethodDef methods[] = {
    {"answer", answer, METH_NOARGS, "Return fixture constant."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "offline_probe", NULL, -1, methods
};
PyMODINIT_FUNC PyInit_offline_probe(void) { return PyModule_Create(&module); }
