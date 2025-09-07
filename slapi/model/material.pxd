# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.unicodestring cimport *
from slapi.color cimport *

cdef extern from "SketchUpAPI/model/material.h":
    cdef enum SUMaterialType:
        SUMaterialType_Colored = 0, # Colored material
        SUMaterialType_Textured,    # Textured material
        SUMaterialType_ColorizedTexture #Colored and textured material

    SUEntityRef SUMaterialToEntity(SUMaterialRef material)
    SUMaterialRef SUMaterialFromEntity(SUEntityRef entity)
    SU_RESULT SUMaterialCreate(SUMaterialRef* material)
    SU_RESULT SUMaterialRelease(SUMaterialRef* material)
    SU_RESULT SUMaterialSetName(SUMaterialRef material, const char* name)
    SU_RESULT SUMaterialGetName(SUMaterialRef material, SUStringRef* name)
    SU_RESULT SUMaterialGetNameLegacyBehavior(SUMaterialRef material, SUStringRef* name) # API 5.0
    SU_RESULT SUMaterialSetColor(SUMaterialRef material, const SUColor* color)
    SU_RESULT SUMaterialGetColor(SUMaterialRef material, SUColor* color)
    SU_RESULT SUMaterialSetTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetTexture(SUMaterialRef material,  SUTextureRef* texture)
    SU_RESULT SUMaterialGetOpacity(SUMaterialRef material, double* alpha)
    SU_RESULT SUMaterialSetOpacity(SUMaterialRef material, double alpha)
    SU_RESULT SUMaterialGetUseOpacity(SUMaterialRef material, bool* use_opacity)
    SU_RESULT SUMaterialSetUseOpacity(SUMaterialRef material, bool use_opacity)
    SU_RESULT SUMaterialSetType(SUMaterialRef material, SUMaterialType type)
    SU_RESULT SUMaterialGetType(SUMaterialRef material, SUMaterialType* type)

    # PBR properties
    SU_RESULT SUMaterialGetAOEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetAOEnabled(SUMaterialRef material, bool enabled)
    SU_RESULT SUMaterialGetAOStrength(SUMaterialRef material, double* strength)
    SU_RESULT SUMaterialSetAOStrength(SUMaterialRef material, double strength)
    SU_RESULT SUMaterialGetAOTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetAOTexture(SUMaterialRef material, SUTextureRef texture)

    SU_RESULT SUMaterialGetMetallicFactor(SUMaterialRef material, double* factor)
    SU_RESULT SUMaterialSetMetallicFactor(SUMaterialRef material, double factor)
    SU_RESULT SUMaterialGetMetallicTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetMetallicTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetMetalnessEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetMetalnessEnabled(SUMaterialRef material, bool enabled)

    SU_RESULT SUMaterialGetNormalEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetNormalEnabled(SUMaterialRef material, bool enabled)
    SU_RESULT SUMaterialGetNormalScale(SUMaterialRef material, double* scale)
    SU_RESULT SUMaterialSetNormalScale(SUMaterialRef material, double scale)
    SU_RESULT SUMaterialGetNormalTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetNormalTexture(SUMaterialRef material, SUTextureRef texture)

    SU_RESULT SUMaterialGetRoughnessEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetRoughnessEnabled(SUMaterialRef material, bool enabled)
    SU_RESULT SUMaterialGetRoughnessFactor(SUMaterialRef material, double* factor)
    SU_RESULT SUMaterialSetRoughnessFactor(SUMaterialRef material, double factor)
    SU_RESULT SUMaterialGetRoughnessTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetRoughnessTexture(SUMaterialRef material, SUTextureRef texture)