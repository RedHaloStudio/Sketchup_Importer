# -*- coding: utf-8 -*-
from slapi.unicodestring cimport SUStringRef

ctypedef unsigned char SUByte

cdef extern from "SketchUpAPI/color.h":
    ctypedef struct SUColor:
        SUByte red,
        SUByte green,
        SUByte blue,
        SUByte alpha
        
    ctypedef enum SU_RESULT:
        pass
        
    SU_RESULT SUColorBlend(SUColor color1, SUColor color2, double weight, SUColor* blended_color)
    
    SU_RESULT SUColorGetNumNames(size_t* size)
    
    SU_RESULT SUColorGetNames(SUStringRef names[], size_t size)
    
    SU_RESULT SUColorSetByName(SUColor* color, const char* name)
    
    SU_RESULT SUColorSetByValue(SUColor* color, size_t value)