# <pep8-80 compliant>
# -*- coding: utf-8 -*-

__author__ = "Martijn Berger"

import platform
from distutils.core import setup
from distutils.extension import Extension

from Cython.Distutils import build_ext

if platform.system() == "Linux":
    libraries = ["SketchUpAPI"]
    extra_compile_args = []
    extra_link_args = ["-Lbinaries/sketchup/x86-64"]

elif platform.system() == "Darwin":  # OS X
    libraries = []
    extra_compile_args = ["-mmacosx-version-min=11.0", "-F."]
    extra_link_args = [
        "-mmacosx-version-min=11.0",
        "-F",
        ".",
        "-framework",
        "SketchUpAPI",
    ]

else:
    libraries = ["SketchUpAPI"]
    extra_compile_args = ["/Zp8"]
    extra_link_args = ["/LIBPATH:binaries/sketchup/x64/"]

ext_modules = [
    Extension(
        "sketchup",  # name of extension
        ["sketchup.pyx"],  # filename of our Pyrex/Cython source
        language="c++",  # this causes Pyrex/Cython to create C++ source
        include_dirs=["headers"],  # usual stuff
        libraries=libraries,  # ditto
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        #   embedsignature=True,
    )
]

for e in ext_modules:
    e.cython_directives = {"language_level": "3"}  # all are Python-3

setup(name="Sketchup", cmdclass={"build_ext": build_ext}, ext_modules=ext_modules)

# install_name_tool -change "@rpath/SketchUpAPI.framework/Versions/Current/SketchUpAPI" "@loader_path/SketchUpAPI.framework/Versions/Current/SketchUpAPI" sketchup.so
# install_name_tool -change "@rpath/SketchUpAPI.framework/Versions/A/SketchUpAPI" "@loader_path/SketchUpAPI.framework/Versions/A/SketchUpAPI" sketchup.cpython-35m-darwin.so
