# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.unicodestring cimport *

cdef extern from "SketchUpAPI/model/environment.h":
    SUEntityRef SUEnvironmentToEntity(SUEnvironmentRef environment)
    SUEnvironmentRef SUEnvironmentFromEntity(SUEntityRef entity)

    SU_RESULT SUEnvironmentGetName(SUEnvironmentRef environment, SUStringRef* name)
