from setuptools import Extension, setup
setup(ext_modules=[Extension("offline_probe", ["probe.c"])])
