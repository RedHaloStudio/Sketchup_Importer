# <pep8-80 compliant>

__author__ = 'Martijn Berger'
__license__ = "GPL"

'''
This program is free software; you can redistribute it and
or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see http://www.gnu.org/licenses
'''

import math
import os
import shutil
import tempfile
import time

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty,
                       StringProperty)
from bpy.types import AddonPreferences, Operator
from bpy_extras.io_utils import (ExportHelper, ImportHelper, unpack_face_list,
                                 unpack_list)
from mathutils import Matrix, Quaternion, Vector

from . import sketchup
from .SKPutil import *

bl_info = {
    "name": "SketchUp Importer",
    "author": "Martijn Berger, Sanjay Mehta, Arindam Mondal",
    "version": (0, 24, 0),
    "blender": (4, 5, 0),
    "description": "Import of native SketchUp (.skp) files",
    # "warning": "Very early preview",
    "wiki_url": "https://github.com/martijnberger/pyslapi",
    "doc_url": "https://github.com/arindam-m/pyslapi/wiki",
    "tracker_url": "https://github.com/arindam-m/pyslapi/wiki/Bug-Report",
    "category": "Import-Export",
    "location": "File > Import"
}

DEBUG = False

LOGS = True

MIN_LOGS = True


if not LOGS:
    MIN_LOGS = True


class SketchupAddonPreferences(AddonPreferences):

    bl_idname = __name__

    camera_far_plane: FloatProperty(
        name="Camera Clip Ends At :",
        default=250,
        unit='LENGTH'
    )

    draw_bounds: IntProperty(
        name="Draw Similar Objects As Bounds When It's Over :",
        default=1000
    )

    def draw(self, context):

        layout = self.layout
        layout.label(text="- Basic Import Options -")
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "camera_far_plane")
        layout = self.layout
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "draw_bounds")


def skp_log(*args):

    if len(args) > 0:
        print('SU | ' + ' '.join(['%s' % a for a in args]))


def create_nested_collection(coll_name):

    context = bpy.context

    main_coll_name = 'SKP Imported Data'

    if not bpy.data.collections.get(main_coll_name):
        skp_main_coll = bpy.data.collections.new(main_coll_name)
        context.scene.collection.children.link(skp_main_coll)

    if not bpy.data.collections.get(coll_name):
        skp_nested_coll = bpy.data.collections.new(coll_name)
        bpy.data.collections[main_coll_name].children.link(skp_nested_coll)

    view_layer_coll = context.view_layer.layer_collection
    main_parent_coll = view_layer_coll.children[main_coll_name]

    coll_set_to_active = main_parent_coll.children[coll_name]
    context.view_layer.active_layer_collection = coll_set_to_active


def hide_one_level():

    context = bpy.context

    outliners = [a for a in context.screen.areas if a.type == 'OUTLINER']
    c = context.copy()
    for ol in outliners:
        c["area"] = ol
        bpy.ops.outliner.show_one_level(c, open=False)
        ol.tag_redraw()

    # context.view_layer.update()


class SceneImporter():

    def __init__(self):

        self.filepath = '/tmp/untitled.skp'
        self.name_mapping = {}
        self.component_meshes = {}
        self.scene = None
        self.layers_skip = []

    def set_filename(self, filename):

        self.filepath = filename
        self.basepath, self.skp_filename = os.path.split(self.filepath)
        return self  # allow chaining

    def load(self, context, **options):
        """load a sketchup file"""

        self.context = context
        self.reuse_material = options['reuse_material']
        self.reuse_group = options['reuse_existing_groups']
        self.max_instance = options['max_instance']
        # self.render_engine = options['render_engine']
        self.component_stats = defaultdict(list)
        self.component_skip = proxy_dict()
        self.component_depth = proxy_dict()
        self.group_written = {}
        ren_res_x = context.scene.render.resolution_x
        ren_res_y = context.scene.render.resolution_y
        self.aspect_ratio = ren_res_x / ren_res_y

        if LOGS:
            skp_log(f'Importing: {self.filepath}')

        addon_name = __name__.split('.')[0]
        self.prefs = context.preferences.addons[addon_name].preferences

        _time_main = time.time()

        try:
            self.skp_model = sketchup.Model.from_file(self.filepath)
        except Exception as e:
            if LOGS:
                skp_log(f'Error reading input file: {self.filepath}')
                skp_log(e)
            return {'FINISHED'}

        if options['import_scene']:
            options['scenes_as_camera'] = False
            options['import_camera'] = True
            for s in self.skp_model.scenes:
                if s.name == options['import_scene']:
                    if not MIN_LOGS:
                        skp_log(f"Importing Scene '{s.name}'")
                    self.scene = s
                    # s.layers are the invisible layers
                    self.layers_skip = [l for l in s.layers]
                    # for l in s.layers:
                    #     skp_log(f"SKIP: {l.name}")
            if not self.layers_skip and not MIN_LOGS:
                skp_log("Scene: '{}' didn't have any invisible layers."
                        .format(options['import_scene']))

        # if not self.layers_skip:
        #     self.layers_skip = [
        #         l for l in self.skp_model.layers if not l.visible
        #     ]

        if self.layers_skip != [] and not MIN_LOGS:
            hidden_layers = [l.name for l in self.layers_skip]
            print('SU | Invisible Layer(s)/Tag(s): \r', end='')
            print(*hidden_layers, sep=', ')

        # for l in sorted([l.name for l in self.layers_skip]):
        #     skp_log(l)

        self.skp_components = proxy_dict(
            self.skp_model.component_definition_as_dict)

        if DEBUG:
            u_comps = [k for k, v in self.skp_components.items()]
            print(f'Components: {len(u_comps)} ||| \r', end='')
            print(*u_comps, sep=', ')

        if not MIN_LOGS:
            skp_log(f'Parsed in {(time.time() - _time_main):.4f} sec.')

        create_nested_collection('SKP Scenes (as Cameras)')

        if options['scenes_as_camera']:
            for s in self.skp_model.scenes:
                self.write_camera(s.camera, s.name)

        if options['import_camera']:
            if self.scene:
                active_cam = self.write_camera(self.scene.camera,
                                               name=self.scene.name)
                context.scene.camera = active_cam
            else:
                active_cam = self.write_camera(self.skp_model.camera)
                context.scene.camera = active_cam

        _time_material = time.time()
        self.write_materials(self.skp_model.materials)

        if not MIN_LOGS:
            skp_log('Materials imported ' +
                    f'in {(time.time() - _time_material):.4f} sec.')

        _time_analyze_depth = time.time()

        D = SKP_util()
        SKP_util.layers_skip = self.layers_skip

        for c in self.skp_model.component_definitions:
            self.component_depth[c.name] = D.component_deps(c.entities)

            if DEBUG:
                print(f'\n-- Comp Depth: {self.component_depth[c.name]}\r',
                      end='')
                print(f' ({c.name}) --')
                print(f'Instances: {c.numInstances}')
                print(f'Instances Used: {c.numUsedInstances}\n')

        if not MIN_LOGS:
            skp_log('Component depths analyzed ' +
                    f'in {(time.time() - _time_analyze_depth):.4f} sec.')

        self.write_duplicateable_groups()

        if options["dedub_only"]:
            return {'FINISHED'}

        # self.component_stats = defaultdict(list)

        _time_mesh_data = time.time()

        create_nested_collection('SKP Mesh Objects')

        self.write_entities(self.skp_model.entities,
                            "_(Loose Entity)",
                            Matrix.Identity(4))

        for k, _v in self.component_stats.items():
            name, mat = k
            if options['dedub_type'] == "VERTEX":
                self.instance_group_dupli_vert(name, mat, self.component_stats)
            else:
                self.instance_group_dupli_face(name, mat, self.component_stats)

        if not MIN_LOGS:
            skp_log('Entities imported ' +
                    f'in {(time.time() - _time_mesh_data):.4f} sec.')

        if LOGS:
            skp_log('Finished entire importing process in %.4f sec.\n' %
                    (time.time() - _time_main))

        # hide_one_level()

        # release model and terminate api
        self.skp_model.close()

        return {'FINISHED'}

    def write_duplicateable_groups(self):

        component_stats = self.analyze_entities(
            self.skp_model.entities,
            "Sketchup",
            Matrix.Identity(4),
            component_stats=defaultdict(list))
        instance_when_over = self.max_instance
        max_depth = max(self.component_depth.values(), default=0)
        component_stats = {
            k: v
            for k, v in component_stats.items() if len(v) >= instance_when_over
        }
        for i in range(max_depth + 1):
            for k, v in component_stats.items():
                name, mat = k
                depth = self.component_depth[name]
                # print(k, len(v), depth)
                comp_def = self.skp_components[name]
                if comp_def and depth == 1:
                    # self.component_skip[(name,mat)] = comp_def.entities
                    pass
                elif comp_def and depth == i:
                    gname = group_name(name, mat)
                    if self.reuse_group and gname in bpy.data.collections:
                        # print("Group {} already defined".format(gname))
                        self.component_skip[(name, mat)] = comp_def.entities
                        # grp_name = bpy.data.collections[gname]
                        self.group_written[(name,
                                            mat)] = bpy.data.collections[gname]
                    else:
                        group = bpy.data.collections.new(name=gname)
                        # print("Component written as group".format(gname))
                        self.conponent_def_as_group(comp_def.entities,
                                                    name,
                                                    Matrix(),
                                                    default_material=mat,
                                                    etype=EntityType.outer,
                                                    group=group)
                        self.component_skip[(name, mat)] = comp_def.entities
                        self.group_written[(name, mat)] = group

    def analyze_entities(self,
                         entities,
                         name,
                         transform,
                         default_material="Material",
                         etype=EntityType.none,
                         component_stats=None,
                         component_skip=None):

        if component_skip is None:
            component_skip = []

        if etype == EntityType.component:
            component_stats[(name, default_material)].append(transform)

        for group in entities.groups:
            if self.layers_skip and group.layer in self.layers_skip:
                continue
            # print(transform)
            # print(Matrix(group.transform))
            self.analyze_entities(group.entities,
                                  "G-" + group.name,
                                  transform @ Matrix(group.transform),
                                  default_material=inherent_default_mat(
                                      group.material, default_material),
                                  etype=EntityType.group,
                                  component_stats=component_stats)

        for instance in entities.instances:
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            mat = inherent_default_mat(instance.material, default_material)
            cdef = self.skp_components[instance.definition.name]
            if (cdef.name, mat) in component_skip:
                continue
            self.analyze_entities(cdef.entities,
                                  cdef.name,
                                  transform @ Matrix(instance.transform),
                                  default_material=mat,
                                  etype=EntityType.component,
                                  component_stats=component_stats)

        return component_stats

    def write_materials(self, materials):

        if self.context.scene.render.engine != 'CYCLES':
            self.context.scene.render.engine = 'CYCLES'

        self.materials = {}
        self.materials_scales = {}
        if self.reuse_material and 'Material' in bpy.data.materials:
            self.materials['Material'] = bpy.data.materials['Material']
        else:
            bmat = bpy.data.materials.new('Material')
            bmat.diffuse_color = (.8, .8, .8, 0)
            # if self.render_engine == 'CYCLES':
            bmat.use_nodes = True
            self.materials['Material'] = bmat

        for mat in materials:

            name = mat.name

            if mat.texture:
                self.materials_scales[name] = mat.texture.dimensions[2:]
            else:
                self.materials_scales[name] = (1.0, 1.0)

            if self.reuse_material and not name in bpy.data.materials:
                bmat = bpy.data.materials.new(name)
                r, g, b, a = mat.color
                tex = mat.texture
                bmat.diffuse_color = (math.pow((r / 255.0), 2.2),
                                      math.pow((g / 255.0), 2.2),
                                      math.pow((b / 255.0), 2.2),
                                      round((a / 255.0), 2))  # sRGB to Linear

                if round((a / 255.0), 2) < 1:
                    bmat.blend_method = 'BLEND'

                bmat.use_nodes = True
                default_shader = bmat.node_tree.nodes['Principled BSDF']

                default_shader_base_color = default_shader.inputs['Base Color']
                default_shader_base_color.default_value = bmat.diffuse_color

                default_shader_alpha = default_shader.inputs['Alpha']
                default_shader_alpha.default_value = round((a / 255.0), 2)

                if tex:
                    tex_name = tex.name.split(os.path.sep)[-1]
                    temp_dir = tempfile.gettempdir()
                    skp_fname = self.filepath.split(os.path.sep)[-1].split(".")[0]
                    temp_dir += os.path.sep + skp_fname
                    if not os.path.isdir(temp_dir):
                        os.mkdir(temp_dir)
                    temp_file_path = os.path.join(temp_dir, tex_name)
                    # skp_log(f"Texture saved temporarily at {temp_file_path}")
                    tex.write(temp_file_path)
                    img = bpy.data.images.load(temp_file_path)
                    img.pack()
                    # os.remove(temp_file_path)
                    shutil.rmtree(temp_dir)

                    # if self.render_engine == 'CYCLES':
                    #     bmat.use_nodes = True
                    tex_node = bmat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    tex_node.location = Vector((-750, 225))
                    bmat.node_tree.links.new(
                        tex_node.outputs['Color'], default_shader_base_color)
                    bmat.node_tree.links.new(
                        tex_node.outputs['Alpha'], default_shader_alpha)
                    # else:
                    #     btex = bpy.data.textures.new(tex_name, 'IMAGE')
                    #     btex.image = img
                    #     slot = bmat.texture_slots.add()
                    #     slot.texture = btex

                self.materials[name] = bmat
            else:
                self.materials[name] = bpy.data.materials[name]

    def write_mesh_data(self,
                        entities=None,
                        name="",
                        default_material='Material'):

        mesh_key = (name, default_material)
        if mesh_key in self.component_meshes:
            return self.component_meshes[mesh_key]
        verts = []
        loops_vert_idx = []
        mat_index = []
        smooth = []
        mats = keep_offset()
        seen = keep_offset()
        uv_list = []
        alpha = False
        uvs_used = False

        for f in entities.faces:

            if f.material:
                mat_number = mats[f.material.name]
            else:
                mat_number = mats[default_material]
                if default_material != 'Material':
                    try:
                        f.st_scale = self.materials_scales[default_material]
                    except KeyError as _e:
                        pass

            vs, tri, uvs = f.tessfaces
            num_loops = 0

            mapping = {}
            for i, (v, uv) in enumerate(zip(vs, uvs)):
                l = len(seen)
                mapping[i] = seen[v]
                if len(seen) > l:
                    verts.append(v)
                uvs.append(uv)

            smooth_edge = False

            for edge in f.edges:
                if edge.GetSmooth() == True:
                    smooth_edge = True
                    break

            for face in tri:
                f0, f1, f2 = face[0], face[1], face[2]
                num_loops += 1

                if mapping[f2] == 0:
                    loops_vert_idx.extend([mapping[f2],
                                           mapping[f0],
                                           mapping[f1]])

                    uv_list.append((uvs[f2][0], uvs[f2][1],
                                    uvs[f0][0], uvs[f0][1],
                                    uvs[f1][0], uvs[f1][1]))

                else:
                    loops_vert_idx.extend([mapping[f0],
                                           mapping[f1],
                                           mapping[f2]])

                    uv_list.append((uvs[f0][0], uvs[f0][1],
                                    uvs[f1][0], uvs[f1][1],
                                    uvs[f2][0], uvs[f2][1]))

                smooth.append(smooth_edge)
                mat_index.append(mat_number)

        if len(verts) == 0:
            return None, False

        me = bpy.data.meshes.new(name)

        if len(mats) >= 1:
            mats_sorted = OrderedDict(sorted(mats.items(), key=lambda x: x[1]))
            for k in mats_sorted.keys():
                try:
                    bmat = self.materials[k]
                except KeyError as _e:
                    bmat = self.materials["Material"]
                me.materials.append(bmat)
                # if bmat.alpha < 1.0:
                #     alpha = True
                try:
                    # if self.render_engine == 'CYCLES':
                    if 'Image Texture' in bmat.node_tree.nodes.keys():
                        uvs_used = True
                    # else:
                    #     for ts in bmat.texture_slots:
                    #         if ts is not None and ts.texture_coords is not None:
                    #             uvs_used = True
                except AttributeError as _e:
                    uvs_used = False
        else:
            skp_log(f"WARNING: Object {name} has no material!")

        tri_faces = list(zip(*[iter(loops_vert_idx)] * 3))
        tri_face_count = len(tri_faces)

        loop_start = []
        i = 0
        for f in tri_faces:
            loop_start.append(i)
            i += len(f)

        loop_total = list(map(lambda f: len(f), tri_faces))

        me.vertices.add(len(verts))
        me.vertices.foreach_set("co", unpack_list(verts))

        me.loops.add(len(loops_vert_idx))
        me.loops.foreach_set("vertex_index", loops_vert_idx)

        me.polygons.add(tri_face_count)
        me.polygons.foreach_set("loop_start", loop_start)
        me.polygons.foreach_set("loop_total", loop_total)
        me.polygons.foreach_set("material_index", mat_index)
        me.polygons.foreach_set("use_smooth", smooth)

        if uvs_used:
            k, l = 0, 0
            me.uv_layers.new()
            for i in range(len(tri_faces)):
                for j in range(3):
                    uv_cordinates = (uv_list[i][l], uv_list[i][l + 1])
                    me.uv_layers[0].data[k].uv = Vector(uv_cordinates)
                    k += 1
                    if j != 2:
                        l += 2
                    else:
                        l = 0

        me.update(calc_edges=True)
        me.validate()
        self.component_meshes[mesh_key] = me, alpha

        return me, alpha

    def write_entities(self,
                       entities,
                       name,
                       parent_tranform,
                       default_material="Material",
                       etype=None):

        if etype == EntityType.component and (
                name, default_material) in self.component_skip:
            self.component_stats[(name,
                                  default_material)].append(parent_tranform)
            return

        me, alpha = self.write_mesh_data(entities=entities,
                                         name=name,
                                         default_material=default_material)

        if me:
            ob = bpy.data.objects.new(name, me)
            ob.matrix_world = parent_tranform
            if alpha > 0.01 and alpha < 1.0:
                ob.show_transparent = True
            me.update(calc_edges=True)
            bpy.context.collection.objects.link(ob)

        for group in entities.groups:
            if group.hidden:
                continue
            if self.layers_skip and group.layer in self.layers_skip:
                continue
            self.write_entities(group.entities,
                                "G-" + group_safe_name(group.name),
                                parent_tranform @ Matrix(group.transform),
                                default_material=inherent_default_mat(
                                    group.material, default_material),
                                etype=EntityType.group)

        for instance in entities.instances:
            if instance.hidden:
                continue
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            mat_name = inherent_default_mat(instance.material,
                                            default_material)
            cdef = self.skp_components[instance.definition.name]
            self.write_entities(cdef.entities,
                                cdef.name,
                                parent_tranform @ Matrix(instance.transform),
                                default_material=mat_name,
                                etype=EntityType.component)

    def instance_object_or_group(self, name, default_material):

        try:
            group = self.group_written[(name, default_material)]
            ob = bpy.data.objects.new(name=name, object_data=None)
            ob.instance_type = 'COLLECTION'
            ob.instance_collection = group
            ob.empty_display_size = 0.01
            return ob
        except KeyError as _e:
            me, alpha = self.component_meshes[(name, default_material)]
            ob = bpy.data.objects.new(name, me)
            if alpha:
                ob.show_transparent = True
            me.update(calc_edges=True)
            return ob

    def conponent_def_as_group(self,
                               entities,
                               name,
                               parent_tranform,
                               default_material="Material",
                               etype=None,
                               group=None):

        if etype == EntityType.outer:
            if (name, default_material) in self.component_skip:
                return
            else:
                skp_log("Write instance definition as group {} {}".format(
                    group.name, default_material))
                self.component_skip[(name, default_material)] = True

        if etype == EntityType.component and (
                name, default_material) in self.component_skip:
            ob = self.instance_object_or_group(name, default_material)
            ob.matrix_world = parent_tranform
            self.context.collection.objects.link(ob)
            ob.layers = 18 * [False] + [True] + [False]
            group.objects.link(ob)

            return

        else:
            me, alpha = self.write_mesh_data(entities=entities,
                                             name=name,
                                             default_material=default_material)

        if me:
            ob = bpy.data.objects.new(name, me)
            ob.matrix_world = parent_tranform
            if alpha:
                ob.show_transparent = True
            me.update(calc_edges=True)
            self.context.collection.objects.link(ob)
            ob.layers = 18 * [False] + [True] + [False]
            group.objects.link(ob)

        for g in entities.groups:
            if self.layers_skip and g.layer in self.layers_skip:
                continue
            self.conponent_def_as_group(
                g.entities,
                "G-" + g.name,
                parent_tranform @ Matrix(g.transform),
                default_material=inherent_default_mat(g.material,
                                                      default_material),
                etype=EntityType.group,
                group=group)

        for instance in entities.instances:
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            cdef = self.skp_components[instance.definition.name]
            self.conponent_def_as_group(
                cdef.entities,
                cdef.name,
                parent_tranform @ Matrix(instance.transform),
                default_material=inherent_default_mat(instance.material,
                                                      default_material),
                etype=EntityType.component,
                group=group)

    def instance_group_dupli_vert(self,
                                  name,
                                  default_material,
                                  component_stats):

        def get_orientations(v):

            orientations = defaultdict(list)

            for transform in v:
                loc, rot, scale = Matrix(transform).decompose()
                scale = (scale[0], scale[1], scale[2])
                rot = (rot[0], rot[1], rot[2], rot[3])
                orientations[(scale, rot)].append((loc[0], loc[1], loc[2]))

            for key, locs in orientations.items():
                scale, rot = key
                yield scale, rot, locs

        for scale, rot, locs in get_orientations(
                component_stats[(name, default_material)]):
            verts = []
            main_loc = Vector(locs[0])
            for c in locs:
                verts.append(Vector(c) - main_loc)
            dme = bpy.data.meshes.new('DUPLI_' + name)
            dme.vertices.add(len(verts))
            dme.vertices.foreach_set("co", unpack_list(verts))
            dme.update(calc_edges=True)  # Update mesh with new data
            dme.validate()
            dob = bpy.data.objects.new("DUPLI_" + name, dme)
            dob.location = main_loc
            dob.instance_type = 'VERTS'

            ob = self.instance_object_or_group(name, default_material)
            ob.scale = scale
            ob.rotation_quaternion = Quaternion(
                (rot[0], rot[1], rot[2], rot[3]))
            ob.parent = dob

            self.context.collection.objects.link(ob)
            self.context.collection.objects.link(dob)
            skp_log(
                "Complex group {} {} instanced {} times, scale -> {}".format(
                    name, default_material, len(verts), scale))

        return

    def instance_group_dupli_face(self,
                                  name,
                                  default_material,
                                  component_stats):

        def get_orientations(v):

            orientations = defaultdict(list)

            for transform in v:
                _loc, _rot, scale = Matrix(transform).decompose()
                scale = (scale[0], scale[1], scale[2])
                orientations[scale].append(transform)

            for scale, transforms in orientations.items():
                yield scale, transforms

        for _scale, transforms in get_orientations(
                component_stats[(name, default_material)]):
            main_loc, _, real_scale = Matrix(transforms[0]).decompose()
            verts = []
            faces = []
            f_count = 0

            for c in transforms:
                l_loc, l_rot, _l_scale = Matrix(c).decompose()
                mat = Matrix.Translation(l_loc) * l_rot.to_matrix().to_4x4()

                verts.append(Vector(
                    (mat * Vector((-0.05, -0.05, 0, 1.0)))[0:3]) - main_loc)
                verts.append(Vector(
                    (mat * Vector((0.05, -0.05, 0, 1.0)))[0:3]) - main_loc)
                verts.append(Vector(
                    (mat * Vector((0.05, 0.05, 0, 1.0)))[0:3]) - main_loc)
                verts.append(Vector(
                    (mat * Vector((-0.05, 0.05, 0, 1.0)))[0:3]) - main_loc)

                faces.append(
                    (f_count + 0, f_count + 1, f_count + 2, f_count + 3))

                f_count += 4

            dme = bpy.data.meshes.new('DUPLI_' + name)
            dme.vertices.add(len(verts))
            dme.vertices.foreach_set("co", unpack_list(verts))

            num_loops = len(faces) * 4
            num_polygons = len(faces)
            dme.loops.add(num_loops)
            dme.polygons.add(num_polygons)

            loops = []
            for f in faces:
                loops.extend(f)

            dme.loops.foreach_set("vertex_index", loops)

            loop_start = []
            i = 0
            for f in faces:
                loop_start.append(i)
                i += len(f)

            dme.polygons.foreach_set("loop_start", loop_start)
            dme.polygons.foreach_set("loop_total", [4] * num_polygons)

            dme.update(calc_edges=True)
            dme.validate()
            dob = bpy.data.objects.new("DUPLI_" + name, dme)
            dob.instance_type = 'FACES'
            dob.location = main_loc
            # dob.use_dupli_faces_scale = True
            # dob.dupli_faces_scale = 10

            ob = self.instance_object_or_group(name, default_material)
            ob.scale = real_scale
            ob.parent = dob
            self.context.collection.objects.link(ob)
            self.context.collection.objects.link(dob)
            skp_log("Complex group {} {} instanced {} times".format(
                name, default_material, f_count / 4))

        return

    def write_camera(self, camera, name="Last View"):

        pos, target, up = camera.GetOrientation()
        bpy.ops.object.add(type='CAMERA', location=pos)
        ob = self.context.object
        ob.name = "Cam : " + name

        z = (Vector(pos) - Vector(target))
        x = Vector(up).cross(z)
        y = z.cross(x)

        x.normalize()
        y.normalize()
        z.normalize()

        ob.matrix_world.col[0] = x.resized(4)
        ob.matrix_world.col[1] = y.resized(4)
        ob.matrix_world.col[2] = z.resized(4)

        cam = ob.data
        aspect_ratio = camera.aspect_ratio
        fov = camera.fov
        if aspect_ratio == False:
            # skp_log(f"Camera:'{name}' uses dynamic/screen aspect ratio.")
            aspect_ratio = self.aspect_ratio
        if fov == False:
            # skp_log(f"Camera:'{name}' is in Orthographic Mode.")
            cam.type = 'ORTHO'
            # cam.ortho_scale = 3.0
        else:
            cam.angle = (math.pi * fov / 180) * aspect_ratio
        cam.clip_end = self.prefs.camera_far_plane
        cam.name = "Cam : " + name


class SceneExporter():

    def __init__(self):

        self.filepath = '/tmp/untitled.skp'

    def set_filename(self, filename):

        self.filepath = filename
        self.basepath, self.skp_filename = os.path.split(self.filepath)

        return self

    def save(self, context, **options):

        skp_log(f'Finished exporting: {self.filepath}')

        return {'FINISHED'}


class ImportSKP(Operator, ImportHelper):
    """Load a Trimble SketchUp SKP file"""

    bl_idname = "import_scene.skp"
    bl_label = "Import SKP"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}

    filename_ext = ".skp"

    filter_glob: StringProperty(
        default="*.skp",
        options={'HIDDEN'},
    )

    scenes_as_camera: BoolProperty(
        name="Scene(s) As Camera(s)",
        description="Import SketchUp Scenes As Blender Camera.",
        default=True
    )

    import_camera: BoolProperty(
        name="Last View In SketchUp As Camera View",
        description="Import last saved view in SketchUp as a Blender Camera.",
        default=False
    )

    reuse_material: BoolProperty(
        name="Use Existing Materials",
        description="Doesn't copy material IDs already in the Blender Scene.",
        default=True
    )

    dedub_only: BoolProperty(
        name="Groups Only",
        description="Import instanciated groups only.",
        default=False
    )

    reuse_existing_groups: BoolProperty(
        name="Reuse Groups",
        description="Use existing Blender groups to instance componenets with.",
        default=False
    )

    max_instance: IntProperty(
        name="Instantiation Threshold :",
        default=50
    )

    dedub_type: EnumProperty(
        name="Instancing Type :",
        items=(('FACE', "Faces", ""),
               ('VERTEX', "Verts", ""),),
        default='FACE',
    )

    import_scene: StringProperty(
        name="Import A Scene :",
        description="Import a specific SketchUp Scene",
        default=""
    )

    # render_engine: EnumProperty(
    #     name="Default Shaders In :",
    #     items=(('CYCLES', "Cycles", ""),
    #            #    ('BLENDER_RENDER', "Blender Render", "")
    #            ),
    #     default='CYCLES'
    # )

    def execute(self, context):

        keywords = self.as_keywords(ignore=("axis_forward", "axis_up",
                                            "filter_glob", "split_mode"))

        return SceneImporter().set_filename(keywords['filepath']).load(
            context, **keywords)

    def draw(self, context):

        layout = self.layout
        layout.label(text="- Primary Import Options -")

        row = layout.row()
        row.prop(self, "scenes_as_camera")
        row = layout.row()
        row.prop(self, "import_camera")
        row = layout.row()
        row.prop(self, "reuse_material")
        row = layout.row()
        row.prop(self, "dedub_only")
        row = layout.row()
        row.prop(self, "reuse_existing_groups")
        col = layout.column()
        col.label(text="- Instantiate components, if they are more than -")
        # split = col.split(factor=0.5)
        # col = split.column()
        col.prop(self, "max_instance")
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "dedub_type")
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "import_scene")
        # row = layout.row()
        # row.use_property_split = True
        # row.prop(self, "render_engine")


class ExportSKP(Operator, ExportHelper):
    """Export .blend into .skp file"""

    bl_idname = "export_scene.skp"
    bl_label = "Export SKP"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".skp"

    def execute(self, context):

        keywords = self.as_keywords()

        return SceneExporter().set_filename(keywords['filepath']).save(
            context, **keywords)


def menu_func_import(self, context):

    self.layout.operator(ImportSKP.bl_idname,
                         text="Import SketchUp Scene(.skp)")


def menu_func_export(self, context):

    self.layout.operator(ExportSKP.bl_idname,
                         text="Export SketchUp Scene(.skp)")


def register():

    bpy.utils.register_class(SketchupAddonPreferences)
    bpy.utils.register_class(ImportSKP)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.utils.register_class(ExportSKP)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():

    bpy.utils.unregister_class(ImportSKP)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(ExportSKP)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(SketchupAddonPreferences)
