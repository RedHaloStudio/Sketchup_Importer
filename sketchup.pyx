# -*- coding: utf-8 -*-

from cpython.version cimport PY_MAJOR_VERSION
from libcpp cimport bool
from libc.stddef cimport size_t
from libc.stdlib cimport malloc, free

from slapi.slapi cimport *
from slapi.initialize cimport *
from slapi.model.defs cimport *
from slapi.model.drawing_element cimport *
from slapi.model.entities cimport *
from slapi.unicodestring cimport *
from slapi.model.entities cimport *
from slapi.model.entity cimport *
from slapi.model.camera cimport *
from slapi.model.geometry_input cimport *
from slapi.model.model cimport *
from slapi.model.component_definition cimport *
from slapi.model.component_instance cimport *
from slapi.model.material cimport *
from slapi.model.group cimport *
from slapi.model.texture cimport *
from slapi.model.scene cimport *
from slapi.model.edge cimport *
from slapi.model.layer cimport *
from slapi.model.face cimport *
from slapi.model.mesh_helper cimport *

cdef class defaultdict(dict):
    default_factory = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default


class keep_offset(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, int)

    def __missing__(self, _):
        return defaultdict.__len__(self)

    def __getitem__(self, item):
        number = defaultdict.__getitem__(self, item)
        self[item] = number
        return number


cdef inline double m(double& v):
    """
    :param v: value to be converted from inches to meters
    :return: value in meters
    """
    return <double> 0.0254 * v

def get_API_version():
    cdef size_t major, minor
    SUGetAPIVersion(&major, &minor)
    return (major, minor)

cdef check_result(SU_RESULT r):
    if not r is SU_ERROR_NONE:
        print(__str_from_SU_RESULT(r))
        raise RuntimeError("Sketchup library giving unexpected results {}".format(__str_from_SU_RESULT(r)))

cdef __str_from_SU_RESULT(SU_RESULT r):
    if r is SU_ERROR_NONE:
        return "SU_ERROR_NONE"
    if r is SU_ERROR_NULL_POINTER_INPUT:
        return "SU_ERROR_NONE"
    if r is SU_ERROR_INVALID_INPUT:
        return "SU_ERROR_INVALID_INPUT"
    if r is SU_ERROR_NULL_POINTER_OUTPUT:
        return "SU_ERROR_NULL_POINTER_OUTPUT"
    if r is SU_ERROR_INVALID_OUTPUT:
        return "SU_ERROR_INVALID_OUTPUT"
    if r is SU_ERROR_OVERWRITE_VALID:
        return "SU_ERROR_OVERWRITE_VALID"
    if r is SU_ERROR_GENERIC:
        return "SU_ERROR_GENERIC"
    if r is SU_ERROR_SERIALIZATION:
        return "SU_ERROR_SERIALIZATION"
    if r is SU_ERROR_OUT_OF_RANGE:
        return "SU_ERROR_OUT_OF_RANGE"
    if r is SU_ERROR_NO_DATA:
        return "SU_ERROR_NO_DATA"
    if r is SU_ERROR_INSUFFICIENT_SIZE:
        return "SU_ERROR_INSUFFICIENT_SIZE"
    if r is SU_ERROR_UNKNOWN_EXCEPTION:
        return "SU_ERROR_UNKNOWN_EXCEPTION"
    if r is SU_ERROR_MODEL_INVALID:
        return "SU_ERROR_MODEL_INVALID"
    if r is SU_ERROR_MODEL_VERSION:
        return "SU_ERROR_MODEL_VERSION"

cdef StringRef2Py(SUStringRef& suStr):
    cdef size_t out_length = 0
    cdef SU_RESULT res = SUStringGetUTF8Length(suStr, &out_length)
    cdef char* out_char_array
    cdef size_t out_number_of_chars_copied
    if out_length == 0:
        return ""
    else:
        out_char_array = <char*> malloc(sizeof(char) * (out_length * 2))
        SUStringGetUTF8(suStr, out_length, out_char_array, &out_number_of_chars_copied)
        try:
            py_result = out_char_array[:out_number_of_chars_copied].decode('UTF-8')
        finally:
            free(out_char_array)
        return py_result

cdef SUStringRef Py2StringRef(s):
    cdef SUStringRef out_string_ref
    cdef SU_RESULT res
    if type(s) is unicode:
        # fast path for most common case(s)
        res = SUStringCreateFromUTF8(&out_string_ref, <unicode> s)
    elif PY_MAJOR_VERSION < 3 and isinstance(s, bytes):
        # only accept byte strings in Python 2.x, not in Py3
        res = SUStringCreateFromUTF8(&out_string_ref, (<bytes> s).decode('ascii'))
    elif isinstance(s, unicode):
        # an evil cast to <unicode> might work here in some(!) cases,
        # depending on what the further processing does.  to be safe,
        # we can always create a copy instead
        res = SUStringCreateFromUTF8(&out_string_ref, unicode(s))
    else:
        raise TypeError("Cannot make sense of string {}".format(s))
    return out_string_ref

cdef class Entity:
    cdef SUEntityRef entity

    def __cinit__(self):
        self.entity.ptr = <void*> 0

    property id:
        def __get__(self):
            cdef int32_t entity_id
            check_result(SUEntityGetID(self.entity, &entity_id))
            return entity_id

    def __len__(self):
        cdef size_t count
        check_result(SUEntityGetNumAttributeDictionaries(self.entity, &count))
        return count

cdef class Point2D:
    cdef SUPoint2D p

    def __cinit__(self, double x, double y):
        self.p.x = x
        self.p.y = y

    property x:
        def __get__(self): return self.p.x
        def __set__(self, double x): self.p.x = x

    property y:
        def __get__(self): return self.p.y
        def __set__(self, double y): self.p.y = y

cdef class Point3D:
    cdef SUPoint3D p

    def __cinit__(self, double x=0, double y=0, double z=0):
        self.p.x = x
        self.p.y = y
        self.p.z = z

    property x:
        def __get__(self): return self.p.x
        def __set__(self, double x): self.p.x = x

    property y:
        def __get__(self): return self.p.y
        def __set__(self, double y): self.p.y = y

    property z:
        def __get__(self): return self.p.z
        def __set__(self, double z): self.p.z = z

    def __str__(self):
        return "Point3d<{},{},{}>".format(self.p.x, self.p.y, self.p.z)

    def __repr__(self):
        return "Point3d @{} [{},{},{}]".format(<size_t> &(self.p), self.p.x, self.p.y, self.p.z)

cdef class Vector3D:
    cdef SUVector3D p

    def __cinit__(self, double x, double y, double z):
        self.p.x = x
        self.p.y = y
        self.p.z = z

    property x:
        def __get__(self): return self.p.x
        def __set__(self, double x): self.p.x = x

    property y:
        def __get__(self): return self.p.y
        def __set__(self, double y): self.p.y = y

    property z:
        def __get__(self): return self.p.z
        def __set__(self, double z): self.p.z = z

cdef class Edge:
    cdef SUEdgeRef edge

    def __cinit__(self):
        self.edge.ptr = <void *> 0

    cdef set_ptr(self, void* ptr):
        self.edge.ptr = ptr

    def GetSoft(self):
        cdef bool soft_flag = 0
        check_result(SUEdgeGetSoft(self.edge, &soft_flag))
        return soft_flag

    def GetSmooth(self):
        cdef bool smooth_flag = 0
        check_result(SUEdgeGetSmooth(self.edge, &smooth_flag))
        return smooth_flag

cdef class Plane3D:
    cdef Plane3D p
    cdef bool cleanup

    def __cinit__(self, double a, double b, double c, double d):
        self.p.a = a
        self.p.b = b
        self.p.c = c
        self.p.d = d

    property a:
        def __get__(self): return self.p.a
        def __set__(self, double a): self.p.a = a

    property b:
        def __get__(self): return self.p.b
        def __set__(self, double b): self.p.b = b

    property c:
        def __get__(self): return self.p.c
        def __set__(self, double c): self.p.c = c

    property d:
        def __get__(self): return self.p.d
        def __set__(self, double d): self.p.d = d

cdef class Camera:
    cdef SUCameraRef camera

    def __cinit__(self):
        self.camera.ptr = <void *> 0

    cdef set_ptr(self, void* ptr):
        self.camera.ptr = ptr

    def GetOrientation(self):
        cdef SUPoint3D position
        cdef SUPoint3D target
        cdef SUVector3D up_vector = [0, 0, 0]
        check_result(SUCameraGetOrientation(self.camera, &position, &target, &up_vector))
        return (m(position.x), m(position.y), m(position.z)), \
               (m(target.x), m(target.y), m(target.z)), \
               (m(up_vector.x), m(up_vector.y), m(up_vector.z))

    property fov:
        def __get__(self):
            #Retrieves the field of view in degrees of a camera object. The field of view is measured along the vertical direction of the camera.
            cdef double fov
            cdef SU_RESULT res = SUCameraGetPerspectiveFrustumFOV(self.camera, &fov)
            if res == SU_ERROR_NONE:
                return fov
            if res == SU_ERROR_NO_DATA:
                return False
            raise RuntimeError("Sketchup library giving unexpected results {}".format(__str_from_SU_RESULT(res)))

        def __set__(self, double fov):
            check_result(SUCameraSetPerspectiveFrustumFOV(self.camera, fov))

    property perspective:
        def __get__(self):
            cdef bool p
            check_result(SUCameraGetPerspective(self.camera, &p))
            return p

        def __set__(self, bool p):
            check_result(SUCameraSetPerspective(self.camera, p))

    property scale:
        def __get__(self):
            cdef double height = 0
            check_result(SUCameraGetOrthographicFrustumHeight(self.camera, &height))
            return height

        def __set__(self, double height):
            check_result(SUCameraSetOrthographicFrustumHeight(self.camera, height))

    property ortho:
        def __get__(self):
            cdef double o = 0
            cdef SU_RESULT res = SUCameraGetOrthographicFrustumHeight(self.camera, &o)
            if res == SU_ERROR_NONE:
                return o
            if res == SU_ERROR_NO_DATA:
                return False
            raise RuntimeError("Sketchup library giving unexpected results {}".format(__str_from_SU_RESULT(res)))

    property aspect_ratio:
        def __get__(self):
            cdef double asp = 1.0
            cdef SU_RESULT res = SUCameraGetAspectRatio(self.camera, &asp)
            if res == SU_ERROR_NONE:
                return asp
            if res == SU_ERROR_NO_DATA:
                return False
            raise RuntimeError("Sketchup library giving unexpected results {}".format(__str_from_SU_RESULT(res)))

cdef class Texture:
    cdef SUTextureRef tex_ref

    def __cinit__(self):
        self.tex_ref.ptr = <void*> 0

    def write(self, filename):
        py_byte_string = filename.encode('UTF-8')
        cdef const char* file_path = py_byte_string
        check_result(SUTextureWriteToFile(self.tex_ref, file_path))

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUTextureGetFileName(self.tex_ref, &n))
            return StringRef2Py(n)

    property dimensions:
        def __get__(self):
            cdef double s_scale = 1.0
            cdef double t_scale = 1.0
            cdef size_t width = 0
            cdef size_t height = 0
            cdef SUMaterialRef mat
            check_result(SUTextureGetDimensions(self.tex_ref, &width, &height, &s_scale, &t_scale))
            return width, height, s_scale, t_scale

    property use_alpha_channel:
        def __get__(self):
            cdef bool alpha_channel_used
            check_result(SUTextureGetUseAlphaChannel(self.tex_ref, &alpha_channel_used))
            return alpha_channel_used

cdef class Instance:
    cdef SUComponentInstanceRef instance

    def __cinit__(self):
        self.instance.ptr = <void*> 0

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUComponentInstanceGetName(self.instance, &n))
            return StringRef2Py(n)

    property entity:
        def __get__(self):
            cdef SUEntityRef ref
            ref = SUComponentInstanceToEntity(self.instance)
            res = Entity()
            res.entity.ptr = ref.ptr
            return res

    property definition:
        def __get__(self):
            cdef SUComponentDefinitionRef component
            component.ptr = <void*> 0
            SUComponentInstanceGetDefinition(self.instance, &component)
            c = Component()
            c.comp_def.ptr = component.ptr
            return c

    property transform:
        def __get__(self):
            cdef SUTransformation t
            check_result(SUComponentInstanceGetTransform(self.instance, &t))
            return [[t.values[0], t.values[4], t.values[8], m(t.values[12])],
                    [t.values[1], t.values[5], t.values[9], m(t.values[13])],
                    [t.values[2], t.values[6], t.values[10], m(t.values[14])],
                    [t.values[3], t.values[7], t.values[11], t.values[15]]]  # * transform

    property material:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUComponentInstanceToDrawingElement(self.instance)
            cdef SUMaterialRef mat
            mat.ptr = <void*> 0
            cdef SU_RESULT = SUDrawingElementGetMaterial(draw_elem, &mat)
            if SU_RESULT == SU_ERROR_NONE:
                m = Material()
                m.material.ptr = mat.ptr
                return m
            else:
                return None

    property layer:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUComponentInstanceToDrawingElement(self.instance)
            cdef SULayerRef lay
            lay.ptr = <void*> 0
            cdef SU_RESULT res = SUDrawingElementGetLayer(draw_elem, &lay)
            if res == SU_ERROR_NONE:
                l = Layer()
                l.layer.ptr = lay.ptr
                return l
            else:
                return None

    property hidden:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUComponentInstanceToDrawingElement(self.instance)
            cdef bool hide_flag = False
            check_result(SUDrawingElementGetHidden(draw_elem, &hide_flag))
            return hide_flag

        def __set__(self, bool hide_flag):
            cdef SUDrawingElementRef draw_elem = SUComponentInstanceToDrawingElement(self.instance)
            check_result(SUDrawingElementSetHidden(draw_elem, hide_flag))

cdef instance_from_ptr(SUComponentInstanceRef r):
    res = Instance()
    res.instance.ptr = r.ptr
    #print("Instance {}".format(hex(<int> r.ptr)))
    return res

cdef class Component:
    cdef SUComponentDefinitionRef comp_def

    def __cinit__(self):
        self.comp_def.ptr = <void*> 0

    property entities:
        def __get__(self):
            cdef SUEntitiesRef e
            e.ptr = <void*> 0
            SUComponentDefinitionGetEntities(self.comp_def, &e);
            res = Entities()
            res.set_ptr(e.ptr)
            return res

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUComponentDefinitionGetName(self.comp_def, &n))
            return StringRef2Py(n)

    property numInstances:
        def __get__(self):
            cdef size_t n = 0
            check_result(SUComponentDefinitionGetNumInstances(self.comp_def, &n))
            return n

    property numUsedInstances:
        def __get__(self):
            cdef size_t n = 0
            check_result(SUComponentDefinitionGetNumUsedInstances(self.comp_def, &n))
            return n

cdef class Layer:
    cdef SULayerRef layer

    def __cinit__(self, **kwargs):
        self.layer.ptr = <void*> 0
        if not '__skip_init' in kwargs:
            check_result(SULayerCreate(&(self.layer)))

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SULayerGetName(self.layer, &n))
            return StringRef2Py(n)

    property visible:
        def __get__(self):
            cdef bool visible_flag = False
            check_result(SULayerGetVisibility(self.layer, &visible_flag))
            return visible_flag
        def __set__(self, bool vflag):
            check_result(SULayerSetVisibility(self.layer, vflag))

    def __richcmp__(Layer self, Layer other not None, int op):
        if op == 2:  # __eq__
            return <size_t> self.layer.ptr == <size_t> other.layer.ptr

cdef class Group:
    cdef SUGroupRef group

    def __cinit__(self):
        pass

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUGroupGetName(self.group, &n))
            return StringRef2Py(n)

    property transform:
        def __get__(self):
            cdef SUTransformation t
            check_result(SUGroupGetTransform(self.group, &t))
            return [[t.values[0], t.values[4], t.values[8], m(t.values[12])],
                    [t.values[1], t.values[5], t.values[9], m(t.values[13])],
                    [t.values[2], t.values[6], t.values[10], m(t.values[14])],
                    [t.values[3], t.values[7], t.values[11], t.values[15]]]  # * transform

    property entities:
        def __get__(self):
            cdef SUEntitiesRef entities
            entities.ptr = <void*> 0
            check_result(SUGroupGetEntities(self.group, &entities))
            res = Entities()
            res.set_ptr(entities.ptr)
            return res

    property material:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUGroupToDrawingElement(self.group)
            cdef SUMaterialRef mat
            mat.ptr = <void*> 0
            cdef SU_RESULT res = SUDrawingElementGetMaterial(draw_elem, &mat)
            if res == SU_ERROR_NONE:
                m = Material()
                m.material.ptr = mat.ptr
                return m
            else:
                return None

    property layer:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUGroupToDrawingElement(self.group)
            cdef SULayerRef lay
            lay.ptr = <void*> 0
            cdef SU_RESULT res = SUDrawingElementGetLayer(draw_elem, &lay)
            if res == SU_ERROR_NONE:
                l = Layer(__skip_init=True)
                l.layer.ptr = lay.ptr
                return l
            else:
                return None

    property hidden:
        def __get__(self):
            cdef SUDrawingElementRef draw_elem = SUGroupToDrawingElement(self.group)
            cdef bool hide_flag = False
            check_result(SUDrawingElementGetHidden(draw_elem, &hide_flag))
            return hide_flag

    def __repr__(self):
        return "Group {} \n\ttransform {}".format(self.name, self.transform)

cdef class Face:
    cdef SUFaceRef face_ref
    cdef double s_scale
    cdef double t_scale

    def __cinit__(self):
        self.face_ref.ptr = <void*> 0
        self.s_scale = 1.0
        self.t_scale = 1.0

    @staticmethod
    def create():
        cdef SUPoint3D[4] vl = [
            [0, 0, 0],
            [100, 100, 0],
            [100, 100, 100],
            [0, 0, 100]]

        cdef SULoopInputRef outer_loop
        outer_loop.ptr = <void*> 0
        check_result(SULoopInputCreate(&outer_loop))
        for i in range(4):
            check_result(SULoopInputAddVertexIndex(outer_loop, i))

        res = Face()
        check_result(SUFaceCreate(&(res.face_ref), vl, &outer_loop))
        print("Face {}".format(<size_t> res.face_ref.ptr))
        return res

    @staticmethod
    def create_simple(list vertices):
        cdef size_t face_len = len(vertices)
        cdef SUPoint3D *vl = <SUPoint3D*> malloc(sizeof(SUPoint3D) * face_len)
        for i, vert in enumerate(vertices):
            if len(vert) != 3:
                raise ValueError('Vertices should have 3 coordinates')
            vl[i].x = float(vert[0])
            vl[i].y = float(vert[1])
            vl[i].z = float(vert[2])

        res = Face()
        check_result(SUFaceCreateSimple(&(res.face_ref), vl, face_len))
        return res

    property st_scale:
        def __set__(self, v):
            self.s_scale = v[0]
            self.t_scale = v[1]

        def __get__(self):
            return self.s_scale, self.t_scale

    property tessfaces:
        def __get__(self):
            cdef double z
            cdef SUMeshHelperRef mesh_ref
            mesh_ref.ptr = <void*> 0
            check_result(SUMeshHelperCreate(&mesh_ref, self.face_ref))
            cdef size_t triangle_count = 0
            cdef size_t vertex_count = 0
            check_result(SUMeshHelperGetNumTriangles(mesh_ref, &triangle_count))
            check_result(SUMeshHelperGetNumVertices(mesh_ref, &vertex_count))
            cdef size_t*indices = <size_t*> malloc(triangle_count * 3 * sizeof(size_t))
            cdef size_t index_count = 0
            check_result(SUMeshHelperGetVertexIndices(mesh_ref, triangle_count * 3, indices, &index_count))
            cdef size_t got_vertex_count = 0
            cdef SUPoint3D*vertices = <SUPoint3D*> malloc(sizeof(SUPoint3D) * vertex_count)
            check_result(SUMeshHelperGetVertices(mesh_ref, vertex_count, vertices, &got_vertex_count))
            cdef SUPoint3D*stq = <SUPoint3D*> malloc(sizeof(SUPoint3D) * vertex_count)
            cdef size_t got_stq_count = 0
            check_result(SUMeshHelperGetFrontSTQCoords(mesh_ref, vertex_count, stq, &got_stq_count))

            vertices_list = []
            uv_list = []
            for i in range(got_vertex_count):
                ind = int(i)
                vertices_list.append((m(vertices[ind].x), m(vertices[ind].y), m(vertices[ind].z)))
            for i in range(got_stq_count):
                z = stq[i].z
                if z == 0:
                    z = 1.0
                ind = int(i)
                uv_list.append((stq[ind].x / z * self.s_scale, stq[ind].y / z * self.t_scale))
            triangles_list = []
            for ii in range(index_count // 3):
                ind = int(ii * 3)
                triangles_list.append((indices[ind], indices[ind + 1], indices[ind + 2]))
            free(vertices)
            free(stq)
            free(indices)
            return (vertices_list, triangles_list, uv_list)

    property edges:
        def __get__(self):
            cdef size_t edge_count = 0
            check_result(SUFaceGetNumEdges(self.face_ref, &edge_count))
            cdef SUEdgeRef*edges_array = <SUEdgeRef*>malloc(sizeof(SUEdgeRef) * edge_count)
            cdef size_t count = 0
            check_result(SUFaceGetEdges(self.face_ref, edge_count, edges_array, &count))
            
            edges_list = []

            for i in range(count):
                e = Edge()
                e.edge.ptr = edges_array[i].ptr
                edges_list.append(e)

            free(edges_array)
            return edges_list

    property material:
        def __get__(self):
            cdef SUMaterialRef mat
            mat.ptr = <void*> 0
            cdef SU_RESULT res = SUFaceGetFrontMaterial(self.face_ref, &mat)
            if res == SU_ERROR_NONE:
                m = Material()
                m.material.ptr = mat.ptr
                return m

    def __repr__(self):
        return "SUFaceRef 0x%0.16X" % <size_t> self.face_ref.ptr

cdef class Entities:
    cdef SUEntitiesRef entities

    def __cinit__(self):
        self.entities.ptr = <void*> 0

    cdef set_ptr(self, void* ptr):
        self.entities.ptr = ptr

    def NumFaces(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumFaces(self.entities, &count))
        return count

    def NumCurves(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumCurves(self.entities, &count))
        return count

    def NumGuidePoints(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumGuidePoints(self.entities, &count))
        return count

    def NumEdges(self, bool standalone_only=False):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumEdges(self.entities, standalone_only, &count))
        return count

    def NumPolyline3ds(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumPolyline3ds(self.entities, &count))
        return count

    def NumGroups(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumGroups(self.entities, &count))
        return count

    def NumImages(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumImages(self.entities, &count))
        return count

    def NumInstances(self):
        cdef size_t count = 0
        check_result(SUEntitiesGetNumInstances(self.entities, &count))
        return count

    property faces:
        def __get__(self):
            cdef size_t len = 0
            check_result(SUEntitiesGetNumFaces(self.entities, &len))
            cdef SUFaceRef*faces_array = <SUFaceRef*> malloc(sizeof(SUFaceRef) * len)
            cdef size_t count = 0
            check_result(SUEntitiesGetFaces(self.entities, len, faces_array, &count))
            for i in range(count):
                res = Face()
                res.face_ref.ptr = faces_array[i].ptr
                yield res
            free(faces_array)

    def get__triangles_lists(self, default_material):
        verts = []
        faces = []
        mat_index = []
        mats = keep_offset()
        seen = keep_offset()
        uv_list = []
        alpha = False  # We assume object does not need alpha flag
        uvs_used = False  # We assume no uvs need to be added

        for f in self.faces:
            vs, tri, uvs = f.triangles

            if f.material:
                mat_number = mats[f.material.name]
            else:
                mat_number = mats[default_material]

            mapping = {}
            for i, (v, uv) in enumerate(zip(vs, uvs)):
                l = len(seen)
                mapping[i] = seen[v]
                if len(seen) > l:
                    verts.append(v)
                uvs.append(uv)

            for face in tri:
                f0, f1, f2 = face[0], face[1], face[2]
                if f2 == 0:  ## eeekadoodle dance
                    faces.append((mapping[f1], mapping[f2], mapping[f0]))
                    uv_list.append((uvs[f2][0], uvs[f2][1],
                                    uvs[f1][0], uvs[f1][1],
                                    uvs[f0][0], uvs[f0][1],
                                    0, 0))
                else:
                    faces.append((mapping[f0], mapping[f1], mapping[f2]))
                    uv_list.append((uvs[f0][0], uvs[f0][1],
                                    uvs[f1][0], uvs[f1][1],
                                    uvs[f2][0], uvs[f2][1],
                                    0, 0))
                mat_index.append(mat_number)
        return verts, faces, uv_list, mat_index, mats

    property groups:
        def __get__(self):
            cdef size_t num_groups = 0
            check_result(SUEntitiesGetNumGroups(self.entities, &num_groups))
            cdef SUGroupRef*groups = <SUGroupRef*> malloc(sizeof(SUGroupRef) * num_groups)
            cdef size_t count = 0
            check_result(SUEntitiesGetGroups(self.entities, num_groups, groups, &count))
            for i in range(count):
                res = Group()
                res.group.ptr = groups[i].ptr
                yield res
            free(groups)

    property instances:
        def __get__(self):
            cdef size_t num_instances = 0
            check_result(SUEntitiesGetNumInstances(self.entities, &num_instances))
            cdef SUComponentInstanceRef*instances = <SUComponentInstanceRef*> malloc(
                sizeof(SUComponentInstanceRef) * num_instances)
            cdef size_t count = 0
            check_result(SUEntitiesGetInstances(self.entities, num_instances, instances, &count))
            for i in range(count):
                yield instance_from_ptr(instances[i])
            free(instances)

    def addFace(self, Face face):
        check_result(SUEntitiesAddFaces(self.entities, 1, &face.face_ref))

    def __repr__(self):
        return "<sketchup.Entities at {}> groups {} instances {}".format(hex(<size_t> &self.entities),
                                                                         self.NumGroups(), self.NumInstances())

cdef class Material:
    cdef SUMaterialRef material

    def __cinit__(self):
        self.material.ptr = <void*> 0

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUMaterialGetName(self.material, &n))
            return StringRef2Py(n)

    property color:
        def __get__(self):
            cdef SUColor c
            check_result(SUMaterialGetColor(self.material, &c))
            return (c.red, c.green, c.blue, c.alpha)

    property opacity:
        def __get__(self):
            cdef double alpha
            check_result(SUMaterialGetOpacity(self.material, &alpha))
            return alpha

        def __set__(self, double alpha):
            check_result(SUMaterialSetOpacity(self.material, alpha))

    property texture:
        def __get__(self):
            cdef SUTextureRef t
            t.ptr = <void*> 0
            cdef SU_RESULT res = SUMaterialGetTexture(self.material, &t)
            if res == SU_ERROR_NONE:
                tex = Texture()
                tex.tex_ref.ptr = t.ptr
                return tex
            else:
                return False

cdef class RenderingOptions:
    cdef SURenderingOptionsRef options

    def __cinit__(self):
        self.options.ptr = <void*> 0

cdef class Scene:
    cdef SUSceneRef scene

    def __cinit__(self):
        self.scene.ptr = <void*> 0

    property name:
        def __get__(self):
            cdef SUStringRef n
            n.ptr = <void*> 0
            SUStringCreate(&n)
            check_result(SUSceneGetName(self.scene, &n))
            return StringRef2Py(n)

    property camera:
        def __get__(self):
            cdef SUCameraRef c
            c.ptr = <void*> 0
            check_result(SUSceneGetCamera(self.scene, &c))
            res = Camera()
            res.set_ptr(c.ptr)
            return res

    property rendering_options:
        def __get__(self):
            cdef SURenderingOptionsRef options
            options.ptr = <void*> 0
            check_result(SUSceneGetRenderingOptions(self.scene, &options))
            res = RenderingOptions()
            res.options = options
            return res

    property entity:
        def __get__(self):
            res = Entity()
            res.entity = SUSceneToEntity(self.scene)
            return res

    property layers:
        def __get__(self):
            cdef size_t num_layers
            check_result(SUSceneGetNumLayers(self.scene, &num_layers))
            cdef SULayerRef*layers_array = <SULayerRef*> malloc(sizeof(SULayerRef) * num_layers)
            for i in range(num_layers):
                layers_array[i].ptr = <void*> 0
            cdef size_t count = 0
            check_result(SUSceneGetLayers(self.scene, num_layers, layers_array, &count))
            for i in range(count):
                l = Layer(__skip_init=True)
                l.layer.ptr = layers_array[i].ptr
                yield l
            free(layers_array)

cdef class LoopInput:
    cdef SULoopInputRef loop

    def __cinit__(self, **kwargs):
        self.loop.ptr = <void*> 0
        if not '__skip_init' in kwargs:
            check_result(SULoopInputCreate(&(self.loop)))

    def AddVertexIndex(self, i):
        check_result(SULoopInputAddVertexIndex(self.loop, i))

cdef class Model:
    cdef SUModelRef model

    def __cinit__(self, **kwargs):
        self.model.ptr = <void*> 0
        SUInitialize()
        if not '__skip_init' in kwargs:
            check_result(SUModelCreate(&(self.model)))

    @staticmethod
    def from_file(filename):
        res = Model(__skip_init=True)
        py_byte_string = filename.encode('UTF-8')
        cdef const char* f = py_byte_string
        check_result(SUModelCreateFromFile(&(res.model), f))
        return res

    def save(self, filename):
        py_byte_string = filename.encode('UTF-8')
        cdef const char* f = py_byte_string
        check_result(SUModelSaveToFile(self.model, f))
        return True

    def close(self):
        SUModelRelease(&self.model)
        SUTerminate()

    def NumMaterials(self):
        cdef size_t count = 0
        check_result(SUModelGetNumMaterials(self.model, &count))
        return count

    def NumComponentDefinitions(self):
        cdef size_t count = 0
        check_result(SUModelGetNumComponentDefinitions(self.model, &count))
        return count

    def NumScenes(self):
        cdef size_t count = 0
        check_result(SUModelGetNumScenes(self.model, &count))
        return count

    def NumLayers(self):
        cdef size_t count = 0
        check_result(SUModelGetNumLayers(self.model, &count))
        return count

    def NumAttributeDictionaries(self):
        cdef size_t count = 0
        check_result(SUModelGetNumAttributeDictionaries(self.model, &count))
        return count

    property camera:
        def __get__(self):
            cdef SUCameraRef c
            c.ptr = <void*> 0
            check_result(SUModelGetCamera(self.model, &c))
            res = Camera()
            res.set_ptr(c.ptr)
            return res

    property entities:
        def __get__(self):
            cdef SUEntitiesRef entities
            entities.ptr = <void*> 0
            check_result(SUModelGetEntities(self.model, &entities))
            res = Entities()
            res.set_ptr(entities.ptr)
            return res

    property materials:
        def __get__(self):
            cdef size_t num_materials = 0
            check_result(SUModelGetNumMaterials(self.model, &num_materials))
            cdef SUMaterialRef*materials = <SUMaterialRef*> malloc(sizeof(SUMaterialRef) * num_materials)
            cdef size_t count = 0
            check_result(SUModelGetMaterials(self.model, num_materials, materials, &count))
            for i in range(count):
                m = Material()
                m.material.ptr = materials[i].ptr
                yield m
            free(materials)

    property component_definitions:
        def __get__(self):
            cdef size_t num_component_defs = 0
            check_result(SUModelGetNumComponentDefinitions(self.model, &num_component_defs))
            cdef SUComponentDefinitionRef*components = <SUComponentDefinitionRef*> malloc(
                sizeof(SUComponentDefinitionRef) * num_component_defs)
            cdef size_t count = 0
            check_result(SUModelGetComponentDefinitions(self.model, num_component_defs, components, &count))
            for i in range(count):
                c = Component()
                c.comp_def.ptr = components[i].ptr
                yield c
            free(components)

    property scenes:
        def __get__(self):
            cdef size_t num_scenes = 0
            check_result(SUModelGetNumScenes(self.model, &num_scenes))
            cdef SUSceneRef*scenes_array = <SUSceneRef*> malloc(sizeof(SUSceneRef) * num_scenes)
            for i in range(num_scenes):
                scenes_array[i].ptr = <void*> 0
            cdef size_t count = 0
            check_result(SUModelGetScenes(self.model, num_scenes, scenes_array, &count))
            for i in range(count):
                s = Scene()
                s.scene.ptr = scenes_array[i].ptr
                yield s
            free(scenes_array)

    property component_definition_as_dict:
        def __get__(self):
            res = {}
            for c in self.component_definitions:
                res[c.name] = c
            return res

    property layers:
        def __get__(self):
            cdef size_t num_layers = 0
            check_result(SUModelGetNumLayers(self.model, &num_layers))
            cdef SULayerRef*layers_array = <SULayerRef*> malloc(sizeof(SULayerRef) * num_layers)
            for i in range(num_layers):
                layers_array[i].ptr = <void*> 0
            cdef size_t count = 0
            check_result(SUModelGetLayers(self.model, num_layers, layers_array, &count))
            for i in range(count):
                l = Layer(__skip_init=True)
                l.layer.ptr = layers_array[i].ptr
                yield l
            free(layers_array)
