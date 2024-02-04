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
from mathutils import Matrix, Euler, Quaternion, Vector

from . import sketchup
from .SKPutil import *

bl_info = {
    "name": "SketchUp Importer",
    "author": "Martijn Berger, Sanjay Mehta, Arindam Mondal, Peter Kirkham",
    "version": (0, 23, 2),
    "blender": (3, 2, 0),
    "description": "Import of native SketchUp (.skp) files",
    #"warning": "Very early preview",
    "wiki_url": "https://github.com/martijnberger/pyslapi",
    "doc_url": "https://github.com/arindam-m/pyslapi/wiki",
    "tracker_url": "https://github.com/arindam-m/pyslapi/wiki/Bug-Report",
    "category": "Import-Export",
    "location": "File > Import"
}

DEBUG = False

LOGS = True

MIN_LOGS = False

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
        row.prop(self, 'camera_far_plane')
        layout = self.layout
        row = layout.row()
        row.use_property_split = True
        row.prop(self, 'draw_bounds')


def skp_log(*args):
    # Log output by pre-pending "SU |"
    if len(args) > 0:
        print("SU | " + " ".join(["%s" % a for a in args]))


def create_nested_collection(coll_name):
    context = bpy.context
    main_coll_name = "SKP Imported Data"  # data imported into this collection

    # Check if the main import collection exists and create it if missing
    if not bpy.data.collections.get(main_coll_name):
        skp_main_coll = bpy.data.collections.new(main_coll_name)
        context.scene.collection.children.link(skp_main_coll)

    # Check if the named collection being created exists and create if missing
    if not bpy.data.collections.get(coll_name):
        skp_nested_coll = bpy.data.collections.new(coll_name)
        bpy.data.collections[main_coll_name].children.link(skp_nested_coll)

    # Set active layer to the named collection just created
    view_layer_coll = context.view_layer.layer_collection
    main_parent_coll = view_layer_coll.children[main_coll_name]
    coll_set_to_active = main_parent_coll.children[coll_name]
    context.view_layer.active_layer_collection = coll_set_to_active


class SceneImporter():

    def __init__(self):
        self.filepath = "/tmp/untitled.skp"
        self.name_mapping = {}
        self.component_meshes = {}
        self.scene = None
        self.layers_skip = []

    def set_filename(self,
                     filename):
        self.filepath = filename
        self.basepath, self.skp_filename = os.path.split(self.filepath)
        return self  # allow chaining

    #
    # This is the main method to load a SketchUp file into Blender. The method
    # is structured to import the following in order:
    #     1) Import SketchUp scenes and optional last view as cameras.
    #     2) Import the materials in the SketchUp model.
    #     3) Import components in the SketchUp model as a group containing
    #        multiple linked objects if the number of instances for each
    #        component is higher than a given threshold.
    #     4) Import remaining mesh objects.
    #
    def load(self,
             context,
             **options):
        """Load a SketchUp file"""

        # Blender settings
        self.context = context
        self.reuse_material = options['reuse_material']
        self.reuse_group = options['reuse_existing_groups']
        self.max_instance = options['max_instance']
        #self.render_engine = options['render_engine']
        self.component_stats = defaultdict(list)
        self.component_skip = proxy_dict()
        self.component_depth = proxy_dict()
        self.group_written = {}
        ren_res_x = context.scene.render.resolution_x
        ren_res_y = context.scene.render.resolution_y
        self.aspect_ratio = ren_res_x / ren_res_y
        
        # Start stopwatch for overall import
        _time_main = time.time()

        # Log filename being imported
        if LOGS:
            skp_log(f"Importing: {self.filepath}")
        addon_name = __name__.split('.')[0]
        self.prefs = context.preferences.addons[addon_name].preferences

        # Open the SketchUp file and access the model using SketchUp API
        try:
            self.skp_model = sketchup.Model.from_file(self.filepath)
        except Exception as e:
            if LOGS:
                skp_log(f"Error reading input file: {self.filepath}")
                skp_log(e)
            return {'FINISHED'}

        # Start stopwatch for camera import
        if not MIN_LOGS:
            skp_log("")
            skp_log("=== Importing Sketchup scenes and views as Blender "
                    "Cameras ===")
        _time_camera = time.time()

        # Create collection for cameras
        create_nested_collection("SKP Scenes (as Cameras)")

        # Import a specific named SketchUp scene as a Blender camera and hide
        # the layers associated with that specific scene
        if options['import_scene']:
            options['scenes_as_camera'] = False
            options['import_camera'] = True
            for s in self.skp_model.scenes:
                if s.name == options['import_scene']:
                    if not MIN_LOGS:
                        skp_log(f"Importing named SketchUp scene '{s.name}'")
                    self.scene = s

                    # Skip s.layers which are the invisible layers
                    self.layers_skip = [l for l in s.layers]
            if not self.layers_skip and not MIN_LOGS:
                skp_log("Scene: '{}' didn't have any invisible layers."
                        .format(options['import_scene']))
            if self.layers_skip != [] and not MIN_LOGS:
                hidden_layers = sorted([l.name for l in self.layers_skip])
                print("SU | Invisible Layer(s)/Tag(s): \n     ", end="")
                print(*hidden_layers, sep=', ')

        # Import each scene as a Blender camera
        if options['scenes_as_camera']:
            if not MIN_LOGS:
                skp_log("Importing all SketchUp scenes as Blender cameras")
            for s in self.skp_model.scenes:
                self.write_camera(s.camera, s.name)

        # Set the active camera and use for 3D view
        if options['import_camera']:
            if not MIN_LOGS:
                skp_log("Importing last SketchUp view as Blender camera")
            if self.scene:
                active_cam = self.write_camera(self.scene.camera,
                                               name=self.scene.name)
                context.scene.camera = bpy.data.objects[active_cam]
            else:
                active_cam = self.write_camera(self.skp_model.camera)
                context.scene.camera = bpy.data.objects[active_cam]
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces[0].region_3d.view_perspective = 'CAMERA'
                    break
        SKP_util.layers_skip = self.layers_skip
        if not MIN_LOGS:
            skp_log("Cameras imported in "
                    f"{(time.time() - _time_camera):.4f} sec.")

        # Start stopwatch for material imports
        if not MIN_LOGS:
            skp_log("")
            skp_log("=== Importing Sketchup materials into Blender ===")
        _time_material = time.time()
        self.write_materials(self.skp_model.materials)
        if not MIN_LOGS:
            skp_log("Materials imported in "
                    f"{(time.time() - _time_material):.4f} sec.")

        # Start stopwatch for component import
        if not MIN_LOGS:
            skp_log("")
            skp_log("=== Importing Sketchup components into Blender ===")
        _time_analyze_depth = time.time()

        # Create collection for components
        create_nested_collection('SKP Components')

        # Determine the number of components that exist in the SketchUp model
        self.skp_components = proxy_dict(
            self.skp_model.component_definition_as_dict)
        u_comps = [k for k, v in self.skp_components.items()]
        if not MIN_LOGS:
            print(f"SU | Contains {len(u_comps)} components: \n     ", end="")
            print(*u_comps, sep=', ')

        # Analyse component depths
        D = SKP_util()
        for c in self.skp_model.component_definitions:
            self.component_depth[c.name] = D.component_deps(c.entities)
            if DEBUG:
                print(f"     -- ({c.name}) --\n        "
                      f"Depth: {self.component_depth[c.name]}\n", end="")
                print("        Instances (Used): "
                      f"{c.numInstances} ({c.numUsedInstances})")
        if not MIN_LOGS:
            skp_log(f"Component depths analyzed in "
                    f"{(time.time() - _time_analyze_depth):.4f} sec.")

        # Import the components as duplicated groups then hide components
        self.write_duplicateable_groups()
        bpy.data.collections['SKP Components'].hide_viewport = True
        for vl in context.scene.view_layers:
            for l in vl.active_layer_collection.children:
                if l.name == 'SKP Components':
                    l.exclude = True  # hide component collection in view layer
        if options['dedub_only']:
            return {'FINISHED'}

        # Start stopwatch for mesh objects import
        if not MIN_LOGS:
            skp_log("")
            skp_log("=== Importing Sketchup mesh objects into Blender ===")
        _time_mesh_data = time.time()

        # Create collection for mesh objects
        create_nested_collection('SKP Mesh Objects')

        # Import mesh objects into structure that matches the SketchUp outliner
        self.write_entities(self.skp_model.entities,
                            "_(Loose Entity)",
                            Matrix.Identity(4))
        for k, _v in self.component_stats.items():
            name, mat = k
            if options['dedub_type'] == 'VERTEX':
                self.instance_group_dupli_vert(name, mat, self.component_stats)
            else:
                self.instance_group_dupli_face(name, mat, self.component_stats)
        if not MIN_LOGS:
            skp_log("Entities imported in "
                    f"{(time.time() - _time_mesh_data):.4f} sec.")

        # Importing has completed
        if LOGS:
            skp_log("Finished entire importing process in %.4f sec.\n" %
                    (time.time() - _time_main))
        return {'FINISHED'}

    #
    # Write components as groups that can be duplicated later.
    #
    def write_duplicateable_groups(self):
        component_stats = self.analyze_entities(
            self.skp_model.entities,
            "Sketchup",
            Matrix.Identity(4),
            component_stats=defaultdict(list))
        instance_when_over = self.max_instance
        max_depth = max(self.component_depth.values(), default=0)

        # Filter out components from list if the total number of instances
        # is lower than the minimum threshold for creating duplicated mesh
        # objects.
        component_stats = {
            k: v
            for k, v in component_stats.items() if len(v) >= instance_when_over
        }
        for i in range(max_depth + 1):
            for k, v in component_stats.items():
                name, mat = k
                depth = self.component_depth[name]
                comp_def = self.skp_components[name]
                if comp_def and depth == 1:
                    #self.component_skip[(name, mat)] = comp_def.entities
                    pass
                elif comp_def and depth == i:
                    gname = group_name(name, mat)
                    if self.reuse_group and gname in bpy.data.collections:
                        skp_log("Group {} already defined".format(gname))
                        self.component_skip[(name, mat)] = comp_def.entities
                        self.group_written[(name,
                                            mat)] = bpy.data.collections[gname]
                    else:
                        group = bpy.data.collections.new(name=gname)
                        skp_log("Component {} written as group".format(gname))
                        self.component_def_as_group(comp_def.entities,
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
            if DEBUG:
                print(f"     |G {group.name}")
                print(f"     {Matrix(group.transform)}")
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
            if DEBUG:
                print(f"     |C {cdef.name}")
                print(f"     {Matrix(instance.transform)}")
            self.analyze_entities(cdef.entities,
                                  cdef.name,
                                  transform @ Matrix(instance.transform),
                                  default_material=mat,
                                  etype=EntityType.component,
                                  component_stats=component_stats)
        return component_stats

    #
    # Import materials from SketchUp into Blender.
    #
    def write_materials(self,
                        materials):
        if self.context.scene.render.engine != 'CYCLES':
            self.context.scene.render.engine = 'CYCLES'
        self.materials = {}
        self.materials_scales = {}
        if self.reuse_material and 'Material' in bpy.data.materials:
            self.materials['Material'] = bpy.data.materials['Material']
        else:
            bmat = bpy.data.materials.new('Material')
            bmat.diffuse_color = (.8, .8, .8, 1)
            #if self.render_engine == 'CYCLES':
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
                    #skp_log(f"Texture saved temporarily at {temp_file_path}")
                    tex.write(temp_file_path)
                    img = bpy.data.images.load(temp_file_path)
                    img.pack()
                    #os.remove(temp_file_path)
                    shutil.rmtree(temp_dir)
                    #if self.render_engine == 'CYCLES':
                    #    bmat.use_nodes = True
                    tex_node = bmat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    tex_node.location = Vector((-750, 225))
                    bmat.node_tree.links.new(
                        tex_node.outputs['Color'], default_shader_base_color)
                    bmat.node_tree.links.new(
                        tex_node.outputs['Alpha'], default_shader_alpha)
                self.materials[name] = bmat
            else:
                self.materials[name] = bpy.data.materials[name]
            if not MIN_LOGS:
                print(f"     {name}")

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
                    bmat = self.materials['Material']
                me.materials.append(bmat)
                #if bmat.alpha < 1.0:
                #    alpha = True
                try:
                    #                    if self.render_engine == 'CYCLES':
                    if 'Image Texture' in bmat.node_tree.nodes.keys():
                        uvs_used = True
                #else:
                #    for ts in bmat.texture_slots:
                #        if ts is not None and ts.texture_coords is not
                #                        None:
                #            uvs_used = True
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
        me.vertices.foreach_set('co', unpack_list(verts))

        me.loops.add(len(loops_vert_idx))
        me.loops.foreach_set('vertex_index', loops_vert_idx)

        me.polygons.add(tri_face_count)
        me.polygons.foreach_set('loop_start', loop_start)
        me.polygons.foreach_set('loop_total', loop_total)
        me.polygons.foreach_set('material_index', mat_index)
        me.polygons.foreach_set('use_smooth', smooth)

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

    #
    # Recursively import all the mesh objects. Groups containing no mesh
    # information are imported as empty objects and can contain nested
    # groups or components. This approach preserves the hierarchy from the
    # SketchUp outliner.
    #
    def write_entities(self,
                       entities,
                       name,
                       parent_transform,
                       default_material='Material',
                       etype=None,
                       parent_name=None,
                       parent_location=Vector((0, 0, 0))):

        # Check if this is a component that has already been duplicated. We
        # can skip writing this if it is already contained in a duplication
        # group.
        if etype == EntityType.component and (
                name, default_material) in self.component_skip:
            self.component_stats[(name,
                                  default_material)].append(parent_transform)
            return

        # Get the mesh data for this object
        me, alpha = self.write_mesh_data(entities=entities, name=name,
                                         default_material=default_material)

        # If there are no further nested groups or components, then we can
        # create an object containing the mesh. Otherwise we create a new
        # empty object and place an object containing the loose geometry as
        # a mesh within this group.
        nested_groups = 0
        for group in entities.groups:
            nested_groups += 1  # count groups (brute force approach)
        nested_comps = 0
        for comp in entities.instances:
            nested_comps += 1  # count components (brute force approach)
        nested_count = nested_groups + nested_comps
        hide_empty = False
        if nested_count == 0 or name == "_(Loose Entity)":
            ob = bpy.data.objects.new(name, me)
            ob.matrix_world = parent_transform
            if 0.01 < alpha < 1.0:
                ob.show_transparent = True
            if me:
                me.update(calc_edges=True)
        else:
            ob = bpy.data.objects.new(name, None)  # empty object to hold group
            ob.matrix_world = parent_transform
            #ob.hide_viewport = True  # disable empties in viewport
            hide_empty = True
            if me:
                ob_mesh = bpy.data.objects.new("_" + name + " (Loose Mesh)",
                                               me)
                ob_mesh.matrix_world = parent_transform
                if 0.01 < alpha < 1.0:
                    ob_mesh.show_transparent = True
                me.update(calc_edges=True)
                ob_mesh.parent = ob
                ob_mesh.location = Vector((0, 0, 0))
                bpy.context.collection.objects.link(ob_mesh)

        # Nested adjustments to the world matrix
        loc = ob.location
        nested_location = Vector((loc[0], loc[1], loc[2]))

        # Nest the object by assigning it to the parent object
        if parent_name is not None and parent_name != "_(Loose Entity)":
            ob.parent = bpy.data.objects[parent_name]
            ob.location -= parent_location
        if nested_count > 0:
            ob.rotation_mode = 'QUATERNION'  # change from default mode of xyz
            ob.rotation_quaternion = Vector((1, 0, 0, 0))
            ob.scale = Vector((1, 1, 1))
        bpy.context.collection.objects.link(ob)
        ob.hide_set(hide_empty)  # enable but do not show empties in viewport

        for group in entities.groups:
            if group.hidden:
                continue
            if self.layers_skip and group.layer in self.layers_skip:
                continue
            temp_ob = bpy.data.objects.new(group.name, None)
            gname = "G-" + group_safe_name(temp_ob.name)
            if DEBUG:
                print(f"     Grp: {gname} in {ob.name}")
            self.write_entities(group.entities,
                                gname,
                                parent_transform @ Matrix(group.transform),
                                default_material=inherent_default_mat(
                                    group.material, default_material),
                                etype=EntityType.group,
                                parent_name=ob.name,
                                parent_location=nested_location)

        for instance in entities.instances:
            if instance.hidden:
                continue
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            mat_name = inherent_default_mat(instance.material,
                                            default_material)
            cdef = self.skp_components[instance.definition.name]
            if instance.name == "":
                cname = "C-" + cdef.name
            else:
                cname = instance.name + " (C-" + cdef.name + ")"
            if DEBUG:
                print(f"     Cmp: {cname} in {ob.name}")
            self.write_entities(cdef.entities,
                                cname,
                                parent_transform @ Matrix(instance.transform),
                                default_material=mat_name,
                                etype=EntityType.component,
                                parent_name=ob.name,
                                parent_location=nested_location)

    def instance_object_or_group(self,
                                 name,
                                 default_material):
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

    def component_def_as_group(self,
                               entities,
                               name,
                               parent_transform,
                               default_material='Material',
                               etype=None,
                               group=None):

        if etype == EntityType.outer:
            if (name, default_material) in self.component_skip:
                return
            else:
                if DEBUG:
                    skp_log("Write instance definition as group {} {}".format(
                        group.name, default_material))
                self.component_skip[(name, default_material)] = True
        if etype == EntityType.component and (
                name, default_material) in self.component_skip:
            ob = self.instance_object_or_group(name, default_material)
            ob.matrix_world = parent_transform
            self.context.collection.objects.link(ob)
            try:
                ob.layers = 18 * [False] + [True] + [False]
            except:
                pass  # capture AttributeError
            group.objects.link(ob)
            return
        else:
            me, alpha = self.write_mesh_data(entities=entities, name=name,
                                             default_material=default_material)
        if me:
            ob = bpy.data.objects.new(name, me)
            ob.matrix_world = parent_transform
            if alpha:
                ob.show_transparent = True
            me.update(calc_edges=True)
            self.context.collection.objects.link(ob)
            try:
                ob.layers = 18 * [False] + [True] + [False]
            except:
                pass  # capture AttributeError
            group.objects.link(ob)
        for g in entities.groups:
            if self.layers_skip and g.layer in self.layers_skip:
                continue
            self.component_def_as_group(
                g.entities,
                "G-" + g.name,
                parent_transform @ Matrix(g.transform),
                default_material=inherent_default_mat(g.material,
                                                      default_material),
                etype=EntityType.group,
                group=group)
        for instance in entities.instances:
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            cdef = self.skp_components[instance.definition.name]
            self.component_def_as_group(
                cdef.entities,
                cdef.name,
                parent_transform @ Matrix(instance.transform),
                default_material=inherent_default_mat(instance.material,
                                                      default_material),
                etype=EntityType.component,
                group=group)

    #
    # Creates a single group in a collection that contains duplicated
    # instances of a component. Scaling and rotations are used to identify
    # similar components. Each duplicate group contains components with the
    # same scale and rotation applied.
    #
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

        # Create a new group with duplicated components as a linked object.
        # Each duplicated group has a specific location, scale and rotation
        # applied.
        for scale, rot, locs in get_orientations(
                component_stats[(name, default_material)]):
            verts = []
            main_loc = Vector(locs[0])
            for c in locs:
                verts.append(Vector(c) - main_loc)
            dme = bpy.data.meshes.new("DUPLI-" + name)
            dme.vertices.add(len(verts))
            dme.vertices.foreach_set("co", unpack_list(verts))
            dme.update(calc_edges=True)  # update mesh with new data
            dme.validate()
            dob = bpy.data.objects.new("DUPLI-" + name, dme)
            dob.location = main_loc
            dob.instance_type = 'VERTS'
            ob = self.instance_object_or_group(name, default_material)
            ob.scale = scale
            ob.rotation_mode = 'QUATERNION'  # change from default mode of xyz
            ob.rotation_quaternion = Quaternion((rot[0], rot[1], rot[2],
                                                 rot[3]))
            ob.parent = dob
            self.context.collection.objects.link(ob)
            self.context.collection.objects.link(dob)
            skp_log(f"Complex group {name} {default_material} instanced "
                    f"{len(verts)} times, scale -> {scale}, rot -> {rot}")
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
            main_loc, _real_rot, real_scale = Matrix(transforms[0]).decompose()
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
            dme = bpy.data.meshes.new("DUPLI-" + name)
            dme.vertices.add(len(verts))
            dme.vertices.foreach_set('co', unpack_list(verts))
            dme.tessfaces.add(f_count / 4)
            dme.tessfaces.foreach_set('vertices_raw', unpack_face_list(faces))
            dme.update(calc_edges=True)  # Update mesh with new data
            dme.validate()
            dob = bpy.data.objects.new("DUPLI-" + name, dme)
            dob.instance_type = 'FACES'
            dob.location = main_loc
            #dob.use_dupli_faces_scale = True
            #dob.dupli_faces_scale = 10
            ob = self.instance_object_or_group(name, default_material)
            ob.scale = real_scale
            ob.parent = dob
            self.context.collection.objects.link(ob)
            self.context.collection.objects.link(dob)
            skp_log("Complex group {} {} instanced {} times".format(
                name, default_material, f_count / 4))
        return

    def write_camera(self,
                     camera,
                     name="Last View"):
        skp_log(f"Writing camera: {name}")
        pos, target, up = camera.GetOrientation()
        bpy.ops.object.add(type='CAMERA', location=pos)
        ob = self.context.object
        ob.name = "Cam: " + name
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
            skp_log(f"Cam: '{name}' uses dynamic/screen aspect ratio.")
            aspect_ratio = self.aspect_ratio
        if fov == False:
            skp_log(f"Cam: '{name}' is in Orthographic Mode.")
            cam.type = 'ORTHO'
        #cam.ortho_scale = 3.0
        else:
            cam.angle = (math.pi * fov / 180) * aspect_ratio
        cam.clip_end = self.prefs.camera_far_plane
        cam.name = "Cam: " + name
        return cam.name


class SceneExporter():

    def __init__(self):
        self.filepath = '/tmp/untitled.skp'

    def set_filename(self, filename):
        self.filepath = filename
        self.basepath, self.skp_filename = os.path.split(self.filepath)
        return self

    def save(self, context, **options):
        skp_log(f"Finished exporting: {self.filepath}")
        return {'FINISHED'}


class ImportSKP(Operator, ImportHelper):
    """Load a Trimble SketchUp .skp file"""
    bl_idname = 'import_scene.skp'
    bl_label = "Import SKP"
    bl_options = {'PRESET', 'REGISTER', 'UNDO'}
    filename_ext = '.skp'

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
        description="Import instantiated groups only.",
        default=False
    )

    reuse_existing_groups: BoolProperty(
        name="Reuse Groups",
        description="Use existing Blender groups to instance components with.",
        default=False
    )

    # Altered from initial default of 50 so as to force import all
    # components to be imported as duplicated objects.
    max_instance: IntProperty(
        name="Instantiation Threshold :",
        default=1
    )

    dedub_type: EnumProperty(
        name="Instancing Type :",
        items=(('FACE', "Faces", ""),
               ('VERTEX', "Vertices", ""),),
        default='VERTEX',
    )

    import_scene: StringProperty(
        name="Import A Scene :",
        description="Import a specific SketchUp Scene",
        default=""
    )

    def execute(self,
                context):
        keywords = self.as_keywords(ignore=("axis_forward", "axis_up",
                                            "filter_glob", "split_mode"))
        return SceneImporter().set_filename(keywords['filepath']).load(
            context, **keywords)

    def draw(self,
             context):
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
        #split = col.split(factor=0.5)
        #col = split.column()
        col.prop(self, "max_instance")
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "dedub_type")
        row = layout.row()
        row.use_property_split = True
        row.prop(self, "import_scene")


class ExportSKP(Operator, ExportHelper):
    """Export .blend into .skp file"""
    bl_idname = "export_scene.skp"
    bl_label = "Export SKP"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".skp"

    def execute(self,
                context):
        keywords = self.as_keywords()
        return SceneExporter().set_filename(keywords['filepath']) \
            .save(context, **keywords)


def menu_func_import(self,
                     context):
    self.layout.operator(ImportSKP.bl_idname,
                         text="SketchUp (.skp)")


def menu_func_export(self,
                     context):
    self.layout.operator(ExportSKP.bl_idname,
                         text="SketchUp (.skp)")


def register():
    bpy.utils.register_class(SketchupAddonPreferences)
    bpy.utils.register_class(ImportSKP)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    # bpy.utils.register_class(ExportSKP)
    # bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportSKP)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    # bpy.utils.unregister_class(ExportSKP)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(SketchupAddonPreferences)
