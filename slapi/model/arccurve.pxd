from slapi.model.defs cimport *
from slapi.geometry cimport *
from slapi.unicodestring cimport *

cdef extern from "SketchUpAPI/model/arccurve.h":
    SUEntityRef SUArcCurveToEntity(SUArcCurveRef arccurve)
    SUArcCurveRef SUArcCurveFromEntity(SUEntityRef entity)
    SUCurveRef SUArcCurveToCurve(SUArcCurveRef arccurve)
    SUArcCurveRef SUArcCurveFromCurve(SUCurveRef curve)
    SU_RESULT SUArcCurveCreate(SUArcCurveRef* arccurve,
                           const SUPoint3D* center,
                           const SUPoint3D* start_point,
                           const SUPoint3D* end_point,
                           const SUVector3D* normal,
                           size_t num_edges)
    SU_RESULT SUArcCurveRelease(SUArcCurveRef* arccurve)
    SU_RESULT SUArcCurveGetRadius(SUArcCurveRef arccurve, double* radius)
    SU_RESULT SUArcCurveGetStartPoint(SUArcCurveRef arccurve, SUPoint3D* point)
    SU_RESULT SUArcCurveGetEndPoint(SUArcCurveRef arccurve, SUPoint3D* point)
    SU_RESULT SUArcCurveGetXAxis(SUArcCurveRef arccurve, SUVector3D* axis)
    SU_RESULT SUArcCurveGetYAxis(SUArcCurveRef arccurve, SUVector3D* axis)
    SU_RESULT SUArcCurveGetCenter(SUArcCurveRef arccurve, SUPoint3D* point)
    SU_RESULT SUArcCurveGetNormal(SUArcCurveRef arccurve, SUVector3D* normal)
    SU_RESULT SUArcCurveGetStartAngle(SUArcCurveRef arccurve, double* angle)
    SU_RESULT SUArcCurveGetEndAngle(SUArcCurveRef arccurve, double* angle)
    SU_RESULT SUArcCurveGetIsFullCircle(SUArcCurveRef arccurve, bool* is_full)