# -*- coding: utf-8 -*-
from slapi.model.defs cimport *
from slapi.geometry cimport *

cdef extern from "SketchUpAPI/geometry/point2d.h":
    SU_RESULT SUPoint2DToSUPoint2D(const SUPoint2D* point1, const SUPoint2D* point2, SUVector2D* vector)
    SU_RESULT SUPoint2DGetEqual(const SUPoint2D* point1, const SUPoint2D* point2, bool* equal)
    SU_RESULT SUPoint2DOffset(const SUPoint2D* point1, const SUVector2D* vector, SUPoint2D* point2)
    SU_RESULT SUPoint2DDistanceToSUPoint2D(const SUPoint2D* point1,  const SUPoint2D* point2, double* distance)
