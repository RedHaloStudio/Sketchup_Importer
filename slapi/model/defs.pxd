# -*- coding: utf-8 -*-
from libcpp cimport bool
from libc.stdint cimport int64_t, uint32_t

ctypedef int SU_RESULT

ctypedef unsigned char SUByte

cdef extern from "SketchUpAPI/model/defs.h":
    ctypedef struct SUArcCurveRef:
        void *ptr
    ctypedef struct SUAttributeDictionaryRef:
        void *ptr
    ctypedef struct SUAxesRef:
        void *ptr
    ctypedef struct SUCameraRef:
        void *ptr
    ctypedef struct SUClassificationsRef:
        void *ptr
    ctypedef struct SUClassificationAttributeRef:
        void *ptr
    ctypedef struct SUClassificationInfoRef:
        void *ptr
    ctypedef struct SUComponentBehavior:
        pass
    ctypedef struct SUComponentDefinitionRef:
        void *ptr
    ctypedef struct SUComponentInstanceRef:
        void *ptr
    ctypedef struct SUCurveRef:
        void *ptr
    ctypedef struct SUDimensionRef:
        void *ptr
    ctypedef struct SUDimensionLinearRef:
        void *ptr
    ctypedef struct SUDimensionRadialRef:
        void *ptr
    ctypedef struct SUDimensionStyleRef:
        void *ptr
    ctypedef struct SUDrawingElementRef:
        void *ptr
    ctypedef struct SUDynamicComponentInfoRef:
        void *ptr
    ctypedef struct SUDynamicComponentAttributeRef:
        void *ptr
    ctypedef struct SUEdgeRef:
        void *ptr
    ctypedef struct SUEdgeUseRef:
        void *ptr
    ctypedef struct SUEntitiesRef:
        void *ptr
    ctypedef struct SUEntityListRef:
        void *ptr
    ctypedef struct SUEntityListIteratorRef:
        void *ptr
    ctypedef struct SUEntityRef:
        void *ptr
    ctypedef struct SUEnvironmentRef:
        void *ptr
    ctypedef struct SUEnvironmentsRef:
        void *ptr
    ctypedef struct SUFaceRef:
        void *ptr
    ctypedef struct SUFontRef:
        void *ptr
    ctypedef struct SUGeometryInputRef:
        void *ptr
    ctypedef struct SUGroupRef:
        void *ptr
    ctypedef struct SUGuideLineRef:
        void *ptr
    ctypedef struct SUGuidePointRef:
        void *ptr
    ctypedef struct SUImageRef:
        void *ptr
    ctypedef struct SUImageRepRef:
        void *ptr
    ctypedef struct SUInstancePathRef:
        void *ptr
    ctypedef struct SULayerRef:
        void *ptr
    ctypedef struct SULayerFolderRef:
        void *ptr
    ctypedef struct SULengthFormatterRef:
        void *ptr
    ctypedef struct SULineStyleRef:
        void *ptr
    ctypedef struct SULineStylesRef:
        void *ptr
    ctypedef struct SULocationRef:
        void *ptr
    ctypedef struct SULoopInputRef:
        void *ptr
    ctypedef struct SULoopRef:
        void *ptr
    ctypedef struct SUMaterialRef:
        void *ptr
    ctypedef struct SUMeshHelperRef:
        void *ptr
    ctypedef struct SUModelRef:
        void *ptr
    ctypedef struct SUOpeningRef:
        void *ptr
    ctypedef struct SUOptionsManagerRef:
        void *ptr
    ctypedef struct SUOptionsProviderRef:
        void *ptr
    ctypedef struct SUOverlayRef:
        void *ptr
    ctypedef struct SUPolyline3dRef:
        void *ptr
    ctypedef struct SURenderingOptionsRef:
        void *ptr
    ctypedef struct SUSceneRef:
        void *ptr
    ctypedef struct SUSchemaRef:
        void *ptr
    ctypedef struct SUSchemaTypeRef:
        void *ptr
    ctypedef struct SUSectionPlaneRef:
        void *ptr
    ctypedef struct SUSelectionRef:
        void *ptr
    ctypedef struct SUShadowInfoRef:
        void *ptr
    ctypedef struct SUSnapRef:
        void *ptr
    ctypedef struct SUStyleRef:
        void *ptr
    ctypedef struct SUStylesRef:
        void *ptr
    ctypedef struct SUTextRef:
        void *ptr
    ctypedef struct SUTextureRef:
        void *ptr
    ctypedef struct SUTextureWriterRef:
        void *ptr
    ctypedef struct SUTypedValueRef:
        void *ptr
    ctypedef struct SUUVHelperRef:
        void *ptr
    ctypedef struct SUVertexRef:
        void *ptr

    cdef enum SURefType:
        SURefType_Unknown = 0,
        SURefType_AttributeDictionary,
        SURefType_Camera,
        SURefType_ComponentDefinition,
        SURefType_ComponentInstance,
        SURefType_Curve,
        SURefType_Edge,
        SURefType_EdgeUse,
        SURefType_Environment,
        SURefType_Environments,
        SURefType_Entities,
        SURefType_Face,
        SURefType_Group,
        SURefType_Image,
        SURefType_Layer,
        SURefType_Location,
        SURefType_Loop,
        SURefType_MeshHelper,
        SURefType_Material,
        SURefType_Model,
        SURefType_Polyline3D,
        SURefType_Scene,
        SURefType_Texture,
        SURefType_TextureWriter,
        SURefType_TypedValue,
        SURefType_UVHelper,
        SURefType_Vertex,
        SURefType_RenderingOptions,
        SURefType_GuidePoint,
        SURefType_GuideLine,
        SURefType_Schema,
        SURefType_SchemaType,
        SURefType_ShadowInfo,
        SURefType_Axes,
        SURefType_ArcCurve,
        SURefType_SectionPlane,
        SURefType_DynamicComponentInfo,
        SURefType_DynamicComponentAttribute,
        SURefType_Style,
        SURefType_Styles,
        SURefType_ImageRep,
        SURefType_InstancePath,
        SURefType_Font,
        SURefType_Dimension,
        SURefType_DimensionLinear,
        SURefType_DimensionRadial,
        SURefType_DimensionStyle,
        SURefType_Text,
        SURefType_EntityList,
        SURefType_EntityListIterator,
        SURefType_DrawingElement,
        SURefType_Entity,
        SURefType_LengthFormatter,
        SURefType_LineStyle,
        SURefType_LineStyleManager,
        SURefType_Selection,
        SURefType_LayerFolder,
        SURefType_Snap
