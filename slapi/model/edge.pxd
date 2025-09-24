# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.color cimport *
from slapi.model.defs cimport *
from slapi.geometry cimport *
from slapi.transformation cimport SUTransformation
from slapi.unicodestring cimport *
from slapi.model.geometry_input cimport *

cdef extern from "SketchUpAPI/model/edge.h":
    SUEntityRef SUEdgeToEntity(SUEdgeRef edge)
    SUEdgeRef SUEdgeFromEntity(SUEntityRef entity)
    SUDrawingElementRef SUEdgeToDrawingElement(SUEdgeRef edge)
    SUEdgeRef SUEdgeFromDrawingElement(SUDrawingElementRef drawing_elem)
    SU_RESULT SUEdgeCreate(SUEdgeRef* edge, const SUPoint3D* start, const SUPoint3D* end)
    SU_RESULT SUEdgeRelease(SUEdgeRef* edge)
    SU_RESULT SUEdgeGetCurve(SUEdgeRef edge, SUCurveRef* curve)
    SU_RESULT SUEdgeGetStartVertex(SUEdgeRef edge, SUVertexRef* vertex)
    SU_RESULT SUEdgeGetEndVertex(SUEdgeRef edge, SUVertexRef* vertex)
    SU_RESULT SUEdgeSetSoft(SUEdgeRef edge, bool soft_flag)
    SU_RESULT SUEdgeGetSoft(SUEdgeRef edge, bool* soft_flag)
    SU_RESULT SUEdgeSetSmooth(SUEdgeRef edge, bool smooth_flag)
    SU_RESULT SUEdgeGetSmooth(SUEdgeRef edge, bool* smooth_flag)
    SU_RESULT SUEdgeGetNumFaces(SUEdgeRef edge, size_t* count)
    SU_RESULT SUEdgeGetFaces(SUEdgeRef edge, size_t len, SUFaceRef faces[], size_t* count)
    SU_RESULT SUEdgeGetColor(SUEdgeRef edge, SUColor* color)
    SU_RESULT SUEdgeGetLengthWithTransform(SUEdgeRef edge, const SUTransformation* transform, double* length)
    SU_RESULT SUEdgeSetColor(SUEdgeRef edge, const SUColor* color)
