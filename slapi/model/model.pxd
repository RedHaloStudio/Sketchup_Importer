# -*- coding: utf-8 -*-
from libcpp cimport bool
from slapi.model.defs cimport *
from slapi.geometry cimport *
from slapi.unicodestring cimport *

cdef extern from "SketchUpAPI/model/model.h":
    enum SUEntityType "SUModelStatistics::SUEntityType":
        SUEntityType_Edge = 0,
        SUEntityType_Face
        SUEntityType_ComponentInstance
        SUEntityType_Group
        SUEntityType_Image
        SUEntityType_ComponentDefinition
        SUEntityType_Layer
        SUEntityType_Material
        SUNumEntityTypes

    struct SUModelStatistics:
        int entity_counts[<int>SUNumEntityTypes]

    enum SUModelUnits:
        SUModelUnits_Inches,
        SUModelUnits_Feet,
        SUModelUnits_Millimeters,
        SUModelUnits_Centimeters,
        SUModelUnits_Meters

    enum SUModelLoadStatus:
        SUModelLoadStatus_Success = 0,
        SUModelLoadStatus_Success_MoreRecent

    enum SUModelVersion:
        SUModelVersion_SU3,
        SUModelVersion_SU4,
        SUModelVersion_SU5,
        SUModelVersion_SU6,
        SUModelVersion_SU7,
        SUModelVersion_SU8,
        SUModelVersion_SU2013,
        SUModelVersion_SU2014,
        SUModelVersion_SU2015,
        SUModelVersion_SU2016,
        SUModelVersion_SU2017,
        SUModelVersion_SU2018,
        SUModelVersion_SU2019,
        SUModelVersion_SU2020,
        SUModelVersion_SU2021,
        SUModelVersion_SU2022,
        SUModelVersion_SU2023,
        SUModelVersion_SU2024,
        SUModelVersion_SU2025

    # Entity type flags for SUModelGetEntitiesOfTypeByPersistentIDs
    int FLAG_GET_ENTITIES_TYPE_DEFINITION_ENTITIES
    int FLAG_GET_ENTITIES_TYPE_LAYERS
    int FLAG_GET_ENTITIES_TYPE_LAYER_FOLDERS
    int FLAG_GET_ENTITIES_TYPE_MATERIALS
    int FLAG_GET_ENTITIES_TYPE_SCENES
    int FLAG_GET_ENTITIES_TYPE_STYLES
    int FLAG_GET_ENTITIES_TYPE_DEFINITIONS
    int FLAG_GET_ENTITIES_TYPE_ALL

    SU_RESULT SUModelCreate(SUModelRef* model)
    SU_RESULT SUModelCreateFromFile(SUModelRef* model, const char* file_path)
    SU_RESULT SUModelCreateFromFileWithStatus(SUModelRef* model, const char* file_path, SUModelLoadStatus* status)
    SU_RESULT SUModelCreateFromBuffer(SUModelRef* model, const unsigned char* buffer, size_t buffer_size)
    SU_RESULT SUModelCreateFromBufferWithStatus(SUModelRef* model, const unsigned char* buffer, size_t buffer_size, SUModelLoadStatus* status)
    SU_RESULT SUModelRelease(SUModelRef* model)
    #SUModelRef SUModelFromExisting(uintptr_t data)
    SU_RESULT SUModelGetEntities(SUModelRef model, SUEntitiesRef* entities)
    SU_RESULT SUModelGetActiveEntities(SUModelRef model, SUEntitiesRef* entities)
    SU_RESULT SUModelGetActivePath(SUModelRef model, SUInstancePathRef* instance_path)
    SU_RESULT SUModelGetNumMaterials(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetMaterials(SUModelRef model, size_t len, SUMaterialRef materials[], size_t* count)
    SU_RESULT SUModelGetEnvironments(SUModelRef model, SUEnvironmentsRef* environments)
    SU_RESULT SUModelAddMaterials(SUModelRef model, size_t len, const SUMaterialRef materials[])
    SU_RESULT SUModelLoadMaterial(SUModelRef model, const char* file_path, SUMaterialRef* material)
    SU_RESULT SUModelGetNumComponentDefinitions(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetComponentDefinitions(SUModelRef model, size_t len, SUComponentDefinitionRef components[], size_t* count)
    SU_RESULT SUModelGetNumGroupDefinitions(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetGroupDefinitions(SUModelRef model, size_t len, SUComponentDefinitionRef definitions[], size_t* count)
    SU_RESULT SUModelGetNumImageDefinitions(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetImageDefinitions(SUModelRef model, size_t len, SUComponentDefinitionRef definitions[], size_t* count)
    SU_RESULT SUModelAddComponentDefinitions(SUModelRef model, size_t len, const SUComponentDefinitionRef components[])
    SU_RESULT SUModelRemoveComponentDefinitions(SUModelRef model, size_t len, SUComponentDefinitionRef components[])
    SU_RESULT SUModelSaveToFile(SUModelRef model, const char* file_path)
    SU_RESULT SUModelSaveToFileWithVersion(SUModelRef model, const char* file_path, SUModelVersion version)
    SU_RESULT SUModelGetCamera(SUModelRef model, SUCameraRef* camera)
    SU_RESULT SUModelSetCamera(SUModelRef model, SUCameraRef* camera)
    SU_RESULT SUModelGetNumScenes(SUModelRef model, size_t* num_scenes)
    SU_RESULT SUModelGetNumLayers(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetLayers(SUModelRef model, size_t len, SULayerRef layers[], size_t* count)
    SU_RESULT SUModelAddLayers(SUModelRef model, size_t len, const SULayerRef layers[])
    SU_RESULT SUModelGetDefaultLayer(SUModelRef model, SULayerRef* layer)
    SU_RESULT SUModelRemoveLayers(SUModelRef model, size_t len, SULayerRef layers[])
    SU_RESULT SUModelGetActiveLayer(SUModelRef model, SULayerRef* layer)
    SU_RESULT SUModelSetActiveLayer(SUModelRef model, SULayerRef layer)
    SU_RESULT SUModelGetVersion(SUModelRef model, int* major, int* minor, int* build)
    SU_RESULT SUModelGetNumAttributeDictionaries(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetAttributeDictionaries(SUModelRef model, size_t len, SUAttributeDictionaryRef dictionaries[], size_t* count)
    SU_RESULT SUModelGetAttributeDictionary(SUModelRef model, const char* name, SUAttributeDictionaryRef* dictionary)
    SU_RESULT SUModelIsGeoReferenced(SUModelRef model, bool* is_geo_ref)
    SU_RESULT SUModelGetLocation(SUModelRef model, SULocationRef* location)
    SU_RESULT SUModelGetStatistics(SUModelRef model, SUModelStatistics* statistics)
    SU_RESULT SUModelSetGeoReference(SUModelRef model, double latitude, double longitude, double altitude, bool is_z_value_centered, bool is_on_ocean_floor)
    SU_RESULT SUModelGetRenderingOptions(SUModelRef model, SURenderingOptionsRef* rendering_options)
    SU_RESULT SUModelGetShadowInfo(SUModelRef model, SUShadowInfoRef* shadow_info)
    SU_RESULT SUModelGetOptionsManager(SUModelRef model, SUOptionsManagerRef* options_manager)
    SU_RESULT SUModelGetNorthCorrection(SUModelRef model, double* north_correction)
    SU_RESULT SUModelMergeCoplanarFaces(SUModelRef model)
    SU_RESULT SUModelGetScenes(SUModelRef model, size_t len, SUSceneRef scenes[], size_t* count)
    SU_RESULT SUModelGetSceneWithName(SUModelRef model, const char* name, SUSceneRef* scene)
    SU_RESULT SUModelAddScenes(SUModelRef model, size_t len, const SUSceneRef scenes[])
    SU_RESULT SUModelAddScene(SUModelRef model, int index, SUSceneRef scene, int* out_index)
    SU_RESULT SUModelReorderScene(SUModelRef model, SUSceneRef scene, size_t new_index)
    SU_RESULT SUModelGetActiveScene(SUModelRef model, SUSceneRef *scene)
    SU_RESULT SUModelSetActiveScene(SUModelRef model, SUSceneRef scene)
    SU_RESULT SUModelAddMatchPhotoScene(SUModelRef model, const char* image_file, SUCameraRef camera, const char* scene_name, SUSceneRef *scene)
    SU_RESULT SUModelGetName(SUModelRef model, SUStringRef* name)
    SU_RESULT SUModelSetName(SUModelRef model, const char* name)
    SU_RESULT SUModelGetPath(SUModelRef model, SUStringRef* path)
    SU_RESULT SUModelGetTitle(SUModelRef model, SUStringRef* title)
    SU_RESULT SUModelGetDescription(SUModelRef model, SUStringRef* description)
    SU_RESULT SUModelSetDescription(SUModelRef model, const char* description)
    SU_RESULT SUModelGetUnits(SUModelRef model, SUModelUnits* units)
    SU_RESULT SUModelGetClassifications(SUModelRef model, SUClassificationsRef* classifications)
    SU_RESULT SUModelGetAxes(SUModelRef model, SUAxesRef* axes)
    SU_RESULT SUModelGetStyles(SUModelRef model, SUStylesRef* styles)
    SU_RESULT SUModelGetInstancePathByPid(SUModelRef model, SUStringRef pid_ref, SUInstancePathRef* instance_path_ref)
    SU_RESULT SUModelGetNumFonts(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetFonts(SUModelRef model, size_t len, SUFontRef fonts[], size_t* count)
    SU_RESULT SUModelGetDimensionStyle(SUModelRef model, SUDimensionStyleRef* style)
    SU_RESULT SUModelGetLengthFormatter(SUModelRef model, SULengthFormatterRef* formatter)
    SU_RESULT SUModelGenerateUniqueMaterialName(SUModelRef model, const char* in_name, SUStringRef* out_name)
    SU_RESULT SUModelFixErrors(SUModelRef model)
    SU_RESULT SUModelOrientFacesConsistently(SUModelRef model, bool recurse_components)
    SU_RESULT SUModelGetLineStyles(SUModelRef model, SULineStylesRef* line_styles)
    SU_RESULT SUModelLoadDefinition(SUModelRef model, const char* filename, SUComponentDefinitionRef* definition)
    SU_RESULT SUModelLoadDefinitionWithStatus(SUModelRef model, const char* filename, SUComponentDefinitionRef* definition, SUModelLoadStatus* status)
    SU_RESULT SUModelRemoveMaterials(SUModelRef model, size_t len, SUMaterialRef materials[])
    SU_RESULT SUModelRemoveScenes(SUModelRef model, size_t len, SUSceneRef scenes[])
    SU_RESULT SUModelGetNumAllMaterials(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetAllMaterials(SUModelRef model, size_t len, SUMaterialRef materials[], size_t* count)
    SU_RESULT SUModelGetGuid(SUModelRef model, SUStringRef* guid)
    SU_RESULT SUModelGetLayersByPersistentIDs(SUModelRef model, size_t num_pids, const int64_t pids[], SULayerRef layers[])
    SU_RESULT SUModelIsDrawingElementVisible(SUModelRef model, SUInstancePathRef path, bool* visible)
    SU_RESULT SUModelGetEntitiesByPersistentIDs(SUModelRef model, size_t num_pids, const int64_t pids[], SUEntityRef entities[])
    SU_RESULT SUModelGetEntitiesOfTypeByPersistentIDs(SUModelRef model, const uint32_t type_flags, const size_t num_pids, const int64_t pids[], SUEntityRef entities[])
    SU_RESULT SUModelGetSelection(SUModelRef model, SUSelectionRef* selection)
    SU_RESULT SUModelGetNumLayerFolders(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetLayerFolders(SUModelRef model, size_t len, SULayerFolderRef* layer_folders, size_t* count)
    SU_RESULT SUModelPurgeEmptyLayerFolders(SUModelRef model, size_t* count)
    SU_RESULT SUModelAddLayerFolder(SUModelRef model, SULayerFolderRef layer_folder)
    SU_RESULT SUModelPurgeUnusedLayers(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetNumTopLevelLayers(SUModelRef model, size_t* count)
    SU_RESULT SUModelGetTopLevelLayers(SUModelRef model, size_t len, SULayerRef layers[], size_t* count)
    SU_RESULT SUModelRemoveLayerFolders(SUModelRef model, size_t len, SULayerFolderRef layer_folders[])
    SU_RESULT SUModelGetBehavior(SUModelRef model, SUComponentBehavior* behavior)
    SU_RESULT SUModelSetBehavior(SUModelRef model, const SUComponentBehavior* behavior)