# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.geometry cimport *

cdef extern from "SketchUpAPI/geometry/vector2d.h":
    SU_RESULT SUVector2DIsValid(const SUVector2D* vector, bool* valid)
    SU_RESULT SUVector2DIsParallelTo(const SUVector2D* vector1, const SUVector2D* vector2, bool* parallel)
    SU_RESULT SUVector2DIsPerpendicularTo(const SUVector2D* vector1, const SUVector2D* vector2, bool* perpendicular)
    SU_RESULT SUVector2DIsSameDirectionAs(const SUVector2D* vector1, const SUVector2D* vector2, bool* same_direction)
    SU_RESULT SUVector2DIsEqual(const SUVector2D* vector1, const SUVector2D* vector2, bool* equal)
    SU_RESULT SUVector2DNormalize(SUVector2D* vector)
    SU_RESULT SUVector2DReverse(SUVector2D* vector)
    SU_RESULT SUVector2DDot(const SUVector2D* vector1, const SUVector2D* vector2, double* dot)
    SU_RESULT SUVector2DCross(const SUVector2D* vector1, const SUVector2D* vector2, double* cross)
    SU_RESULT SUVector2DIsUnitVector(const SUVector2D* vector, bool* is_unit_vector)
    SU_RESULT SUVector2DGetLength(const SUVector2D* vector, double* length)
    SU_RESULT SUVector2DSetLength(SUVector2D* vector, double length)
    SU_RESULT SUVector2DAngleBetween(const SUVector2D* vector1, const SUVector2D* vector2, double* angle)
