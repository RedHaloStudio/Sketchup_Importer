# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.unicodestring cimport *
from slapi.color cimport *

cdef extern from "SketchUpAPI/model/material.h":
    cdef enum SUMaterialType:
        SUMaterialType_Colored = 0,  # Colored material
        SUMaterialType_Textured,     # Textured material
        SUMaterialType_ColorizedTexture #Colored and textured material

    cdef enum SUMaterialOwnerType:
        SUMaterialOwnerType_None = 0,        # Not owned
        SUMaterialOwnerType_DrawingElement,  # Can be applied to SUDrawingElements
        SUMaterialOwnerType_Image,           # Owned exclusively by an Image
        SUMaterialOwnerType_Layer            # Owned exclusively by a Layer

    cdef enum SUMaterialColorizeType:
        SUMaterialColorizeType_Shift = 0,  # Shifts the texture's Hue
        SUMaterialColorizeType_Tint        # Colorize the texture

    cdef enum SUMaterialWorkflow:
        SUMaterialWorkflow_Classic = 0,          # Classic material workflow
        SUMaterialWorkflow_PBRMetallicRoughness  # PBR metallic/roughness material workflow

    cdef enum SUMaterialNormalMapStyle:
        SUMaterialNormalMapStyle_OpenGL = 0,  # OpenGL style
        SUMaterialNormalMapStyle_DirectX     # DirectX style

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
    SU_RESULT SUMaterialIsDrawnTransparent(SUMaterialRef material, bool* transparency)  # API 6.0
    SU_RESULT SUMaterialGetOwnerType(SUMaterialRef material, SUMaterialOwnerType* type)  # API 7.1
    SU_RESULT SUMaterialSetColorizeType(SUMaterialRef material, SUMaterialColorizeType type)  # API 7.1
    SU_RESULT SUMaterialGetColorizeType(SUMaterialRef material, SUMaterialColorizeType* type)  # API 7.1
    SU_RESULT SUMaterialGetColorizeDeltas(SUMaterialRef material, double* hue, double* saturation, double* lightness)  # API 7.1
    SU_RESULT SUMaterialWriteToFile(SUMaterialRef material, const char* file_path)  # API 9.1
    
    # PBR Metallic Roughness Workflow - API 13.0
    SU_RESULT SUMaterialGetWorkflow(SUMaterialRef material, SUMaterialWorkflow* workflow)
    SU_RESULT SUMaterialSetMetalnessEnabled(SUMaterialRef material, bool enable)
    SU_RESULT SUMaterialIsMetalnessEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetMetallicTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetMetallicTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetMetallicFactor(SUMaterialRef material, double factor)
    SU_RESULT SUMaterialGetMetallicFactor(SUMaterialRef material, double* factor)
    SU_RESULT SUMaterialSetRoughnessEnabled(SUMaterialRef material, bool enable)
    SU_RESULT SUMaterialIsRoughnessEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetRoughnessTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetRoughnessTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetRoughnessFactor(SUMaterialRef material, double factor)
    SU_RESULT SUMaterialGetRoughnessFactor(SUMaterialRef material, double* factor)
    SU_RESULT SUMaterialIsNormalEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetNormalTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetNormalTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetNormalScale(SUMaterialRef material, double scale)
    SU_RESULT SUMaterialGetNormalScale(SUMaterialRef material, double* scale)
    SU_RESULT SUMaterialSetNormalStyle(SUMaterialRef material, SUMaterialNormalMapStyle style)
    SU_RESULT SUMaterialGetNormalStyle(SUMaterialRef material, SUMaterialNormalMapStyle* style)
    SU_RESULT SUMaterialIsAOEnabled(SUMaterialRef material, bool* enabled)
    SU_RESULT SUMaterialSetAOTexture(SUMaterialRef material, SUTextureRef texture)
    SU_RESULT SUMaterialGetAOTexture(SUMaterialRef material, SUTextureRef* texture)
    SU_RESULT SUMaterialSetAOStrength(SUMaterialRef material, double strength)
    SU_RESULT SUMaterialGetAOStrength(SUMaterialRef material, double* strength)