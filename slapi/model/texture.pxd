# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.unicodestring cimport *
from slapi.geometry cimport *
from slapi.color cimport *

cdef extern from "SketchUpAPI/model/texture.h":
    SUEntityRef SUTextureToEntity(SUTextureRef texture)
    SUTextureRef SUTextureFromEntity(SUEntityRef entity)
    SU_RESULT SUTextureCreateFromImageRep(SUTextureRef* texture, SUImageRepRef image)   # API 5.0
    SU_RESULT SUTextureCreateFromFile(SUTextureRef* texture, const char* file_path, double s_scale, double t_scale)
    SU_RESULT SUTextureRelease(SUTextureRef* texture)
    SU_RESULT SUTextureGetDimensions(SUTextureRef texture, size_t* width, size_t* height, double* s_scale, double* t_scale)
    SU_RESULT SUTextureSetDimensions(SUTextureRef texture, double s_scale, double t_scale)  # API 13.0
    SU_RESULT SUTextureGetImageRep(SUTextureRef texture, SUImageRepRef* image) # API 5.0
    SU_RESULT SUTextureWriteToFile(SUTextureRef texture, const char* file_path)
    SU_RESULT SUTextureSetFileName(SUTextureRef texture, const char* name) # API 5.0
    SU_RESULT SUTextureGetFileName(SUTextureRef texture,  SUStringRef* file_name)
    SU_RESULT SUTextureGetFilePath(SUTextureRef texture, SUStringRef* file_path)  # API 11.1
    SU_RESULT SUTextureGetUseAlphaChannel(SUTextureRef texture, bool* alpha_channel_used)
    SU_RESULT SUTextureGetAverageColor(SUTextureRef texture, SUColor* color_val)
    SU_RESULT SUTextureGetColorizedImageRep(SUTextureRef texture, SUImageRepRef* image_rep)  # API 6.0
    SU_RESULT SUTextureWriteOriginalToFile(SUTextureRef texture, const char* file_path)  # API 7.1

    # deprecated
    SU_RESULT SUTextureCreateFromImageData(SUTextureRef* texture, size_t width, size_t height, size_t bits_per_pixel, SUByte pixel_data[])
    SU_RESULT SUTextureGetImageDataSize(SUTextureRef texture,  size_t* data_size, size_t* bits_per_pixel)
    SU_RESULT SUTextureGetImageData(SUTextureRef texture, size_t data_size, SUByte pixel_data[])
