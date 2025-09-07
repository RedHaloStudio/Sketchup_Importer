# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.model.environment cimport SUEnvironmentRef

cdef extern from "SketchUpAPI/model/environments.h":
    SU_RESULT SUModelGetEnvironments(SUModelRef model, SUEnvironmentsRef* environments)
    SU_RESULT SUEnvironmentsGetNumEnvironments(SUEnvironmentsRef environments, size_t* count)
    SU_RESULT SUEnvironmentsGetEnvironments(SUEnvironmentsRef environments, size_t len, SUEnvironmentRef C_environments[], size_t* count)
    SU_RESULT SUEnvironmentsGetCurrent(SUEnvironmentsRef environments, SUEnvironmentRef* environment)
    SU_RESULT SUEnvironmentsSetCurrent(SUEnvironmentsRef environments, SUEnvironmentRef environment)
