#!/usr/bin/env python
"""Stage 2 — Build a .blend file from the intermediate JSON produced by Stage 1.

Runs inside Blender headless::

    blender --background --python blend_builder.py -- \\
        <work_dir> <output.blend> [--max-instance N] [--scene NAME]

Uses only headless-safe ``bpy`` APIs (no ``bpy.ops.object.add``, no
``bpy.context.screen``, no outliner ops).
"""

import argparse
import math
import os
import sys
from collections import defaultdict

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

# Sibling modules — add our own directory to sys.path so ``intermediate``
# and ``skputil`` can be imported regardless of how Blender was invoked.
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

from intermediate import load_intermediate  # noqa: E402
from skputil import (  # noqa: E402
    DEFAULT_MATERIAL_NAME,
    EntityType,
    group_name,
    group_safe_name,
    inherent_default_mat,
    proxy_dict,
)


def skp_log(*args):
    if args:
        print("SU | " + " ".join(str(a) for a in args))


# ---------------------------------------------------------------------------
# Hidden-tag collection management
# ---------------------------------------------------------------------------

_hidden_tag_collections = {}  # layer_name -> bpy.types.Collection


def get_hidden_tag_collection(layer_name):
    """Return (or create) a collection for entities on a hidden tag/layer.

    Collections are named ``"Hidden Tag: <layer_name>"`` and linked under
    the scene's root collection.  They will be excluded from the view layer
    after the hierarchy is built (see ``main()``).
    """
    if layer_name in _hidden_tag_collections:
        return _hidden_tag_collections[layer_name]

    coll_name = f"Hidden Tag: {layer_name}"
    coll = bpy.data.collections.new(coll_name)
    bpy.context.scene.collection.children.link(coll)
    _hidden_tag_collections[layer_name] = coll
    return coll


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def write_materials(material_records, work_dir):
    """Create Blender materials from intermediate material records.

    Returns ``(materials_dict, materials_scales_dict)``.
    """
    materials = {}
    materials_scales = {}

    # Default material -------------------------------------------------------
    bmat = bpy.data.materials.new(DEFAULT_MATERIAL_NAME)
    bmat.diffuse_color = (0.8, 0.8, 0.8, 0)
    if bpy.app.version < (6, 0, 0):
        bmat.use_nodes = True
    nodes = bmat.node_tree.nodes
    links = bmat.node_tree.links
    nodes.clear()
    output_shader = nodes.new("ShaderNodeOutputMaterial")
    output_shader.location = (0, 0)
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (-300, 0)
    links.new(principled.outputs[0], output_shader.inputs["Surface"])
    materials[DEFAULT_MATERIAL_NAME] = bmat

    textures_dir = os.path.join(work_dir, "textures")

    for rec in material_records:
        name = rec["name"]
        r, g, b, a = rec["color_rgba"]
        tex = rec.get("texture")

        if tex:
            materials_scales[name] = (tex["s_scale"], tex["t_scale"])
        else:
            materials_scales[name] = (1.0, 1.0)

        bmat = bpy.data.materials.new(name)
        bmat.diffuse_color = (
            math.pow(r / 255.0, 2.2),
            math.pow(g / 255.0, 2.2),
            math.pow(b / 255.0, 2.2),
            round(a / 255.0, 2),
        )

        if round(a / 255.0, 2) < 1:
            bmat.blend_method = "BLEND"

        if bpy.app.version < (6, 0, 0):
            bmat.use_nodes = True

        nodes = bmat.node_tree.nodes
        links = bmat.node_tree.links
        nodes.clear()
        output_shader = nodes.new("ShaderNodeOutputMaterial")
        output_shader.location = (0, 0)
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (-300, 0)
        links.new(principled.outputs[0], output_shader.inputs["Surface"])

        default_shader = nodes["Principled BSDF"]
        default_shader.inputs["Base Color"].default_value = bmat.diffuse_color
        default_shader.inputs["Alpha"].default_value = round(a / 255.0, 2)

        if tex:
            tex_path = os.path.join(textures_dir, tex["filename"])
            if os.path.isfile(tex_path):
                img = bpy.data.images.load(tex_path)
                img.pack()
                tex_node = nodes.new("ShaderNodeTexImage")
                tex_node.image = img
                tex_node.location = (-600, 0)
                links.new(tex_node.outputs["Color"], default_shader.inputs["Base Color"])
                if img.file_format in ("PNG", "TARGA"):
                    links.new(tex_node.outputs["Alpha"], default_shader.inputs["Alpha"])
            else:
                skp_log(f"Warning: texture file not found: {tex_path}")

        materials[name] = bmat

    return materials, materials_scales


# ---------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------

def build_mesh(mesh_data, name, materials):
    """Create a Blender mesh from an intermediate MeshData dict.

    Returns ``(mesh, alpha_flag)`` or ``(None, False)`` if *mesh_data* is None.
    """
    if mesh_data is None:
        return None, False

    verts = mesh_data["vertices"]
    tris = mesh_data["triangles"]
    uv_list = mesh_data["uvs_per_triangle"]
    mat_indices = mesh_data["triangle_material_indices"]
    smooth_flags = mesh_data["triangle_smooth"]
    face_mats = mesh_data["face_materials"]

    if not verts:
        return None, False

    me = bpy.data.meshes.new(name)
    alpha = False
    uvs_used = False

    # Assign material slots ------------------------------------------------
    for mat_name in face_mats:
        bmat = materials.get(mat_name, materials.get(DEFAULT_MATERIAL_NAME))
        me.materials.append(bmat)
        try:
            if "Image Texture" in bmat.node_tree.nodes.keys():
                uvs_used = True
        except AttributeError:
            pass

    # Geometry --------------------------------------------------------------
    tri_count = len(tris)
    loops_vert_idx = []
    for t in tris:
        loops_vert_idx.extend(t)

    loop_start = []
    idx = 0
    for t in tris:
        loop_start.append(idx)
        idx += len(t)
    loop_total = [len(t) for t in tris]

    flat_verts = []
    for v in verts:
        flat_verts.extend(v)

    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", flat_verts)

    me.loops.add(len(loops_vert_idx))
    me.loops.foreach_set("vertex_index", loops_vert_idx)

    me.polygons.add(tri_count)
    me.polygons.foreach_set("loop_start", loop_start)
    me.polygons.foreach_set("loop_total", loop_total)
    me.polygons.foreach_set("material_index", mat_indices)
    me.polygons.foreach_set("use_smooth", smooth_flags)

    # UVs -------------------------------------------------------------------
    if uvs_used and uv_list:
        me.uv_layers.new()
        k = 0
        for i in range(tri_count):
            for j in range(3):
                uv_off = j * 2
                me.uv_layers[0].data[k].uv = (uv_list[i][uv_off], uv_list[i][uv_off + 1])
                k += 1

    me.update(calc_edges=True)
    me.validate()
    return me, alpha


# ---------------------------------------------------------------------------
# Component analysis (on intermediate tree)
# ---------------------------------------------------------------------------

def _inherent_mat(node_mat, parent_default):
    return inherent_default_mat(node_mat, parent_default)


def analyze_entities(node, parent_transform, default_material, etype, component_stats, component_skip):
    """Walk the entity tree and count component instances (mirrors SceneImporter.analyze_entities)."""
    if etype == EntityType.component:
        name = node.get("definition_name", node["name"])
        component_stats[(name, default_material)].append(parent_transform)

    for child in node.get("children", []):
        child_type = child["type"]
        if child.get("hidden"):
            continue
        child_mat = _inherent_mat(child.get("material_name"), default_material)
        child_transform = parent_transform
        if child.get("transform"):
            child_transform = (Matrix(parent_transform) @ Matrix(child["transform"])).to_4x4()
            child_transform = [list(row) for row in child_transform]

        if child_type == "group":
            analyze_entities(child, child_transform, child_mat, EntityType.group,
                             component_stats, component_skip)
        elif child_type == "component_instance":
            cname = child.get("definition_name", child["name"])
            if (cname, child_mat) in component_skip:
                continue
            analyze_entities(child, child_transform, child_mat, EntityType.component,
                             component_stats, component_skip)

    return component_stats


# ---------------------------------------------------------------------------
# Deduplicated groups (ports write_duplicateable_groups)
# ---------------------------------------------------------------------------

def write_duplicateable_groups(
    entity_tree,
    comp_depth_map,
    max_instance,
    materials,
    component_skip,
    group_written,
    component_meshes,
):
    """Create Blender collections for high-frequency components."""
    component_stats = analyze_entities(
        entity_tree,
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        DEFAULT_MATERIAL_NAME,
        EntityType.none,
        defaultdict(list),
        component_skip,
    )
    component_stats = {k: v for k, v in component_stats.items() if len(v) >= max_instance}

    max_depth = max(comp_depth_map.values(), default=0)

    for i in range(max_depth + 1):
        for k, v in component_stats.items():
            name, mat = k
            depth = comp_depth_map.get(name, 0)
            if depth == 1:
                pass
            elif depth == i:
                gname = group_name(name, mat)
                if gname in bpy.data.collections:
                    skp_log(f"Group {gname} already defined")
                    component_skip[(name, mat)] = True
                    group_written[(name, mat)] = bpy.data.collections[gname]
                else:
                    group = bpy.data.collections.new(name=gname)
                    skp_log(f"Component {gname} written as group")
                    _build_group_from_tree(
                        entity_tree, name, mat, group,
                        materials, component_skip, group_written, component_meshes,
                    )
                    component_skip[(name, mat)] = True
                    group_written[(name, mat)] = group


def _find_definition_node(tree, def_name):
    """Find the first node in tree whose definition_name matches."""
    if tree.get("definition_name") == def_name:
        return tree
    for child in tree.get("children", []):
        result = _find_definition_node(child, def_name)
        if result is not None:
            return result
    return None


def _build_group_from_tree(
    entity_tree, comp_name, default_material, group,
    materials, component_skip, group_written, component_meshes,
):
    """Build collection objects for a component definition (ports component_def_as_group)."""
    node = _find_definition_node(entity_tree, comp_name)
    if node is None:
        return

    mesh_data = node.get("mesh")
    mesh_key = (comp_name, default_material)

    if mesh_key in component_meshes:
        me, alpha = component_meshes[mesh_key]
    else:
        me, alpha = build_mesh(mesh_data, comp_name, materials)
        component_meshes[mesh_key] = (me, alpha)

    if me:
        ob = bpy.data.objects.new(comp_name, me)
        ob.matrix_world = Matrix.Identity(4)
        me.update(calc_edges=True)
        bpy.context.collection.objects.link(ob)
        group.objects.link(ob)

    for child in node.get("children", []):
        if child.get("hidden"):
            continue
        child_type = child["type"]
        child_mat = _inherent_mat(child.get("material_name"), default_material)
        child_name = child["name"]

        if child_type == "group":
            child_mesh = child.get("mesh")
            ckey = (child_name, child_mat)
            if ckey in component_meshes:
                cme, calpha = component_meshes[ckey]
            else:
                cme, calpha = build_mesh(child_mesh, child_name, materials)
                component_meshes[ckey] = (cme, calpha)
            if cme:
                cob = bpy.data.objects.new(child_name, cme)
                if child.get("transform"):
                    cob.matrix_world = Matrix(child["transform"])
                cme.update(calc_edges=True)
                bpy.context.collection.objects.link(cob)
                group.objects.link(cob)

        elif child_type == "component_instance":
            cdef_name = child.get("definition_name", child_name)
            if (cdef_name, child_mat) in component_skip:
                ob = _instance_object_or_group(cdef_name, child_mat, group_written, component_meshes)
                if child.get("transform"):
                    ob.matrix_world = Matrix(child["transform"])
                bpy.context.collection.objects.link(ob)
                group.objects.link(ob)
            else:
                child_mesh = child.get("mesh")
                ckey = (child_name, child_mat)
                if ckey in component_meshes:
                    cme, calpha = component_meshes[ckey]
                else:
                    cme, calpha = build_mesh(child_mesh, child_name, materials)
                    component_meshes[ckey] = (cme, calpha)
                if cme:
                    cob = bpy.data.objects.new(child_name, cme)
                    if child.get("transform"):
                        cob.matrix_world = Matrix(child["transform"])
                    cme.update(calc_edges=True)
                    bpy.context.collection.objects.link(cob)
                    group.objects.link(cob)


def _instance_object_or_group(name, default_material, group_written, component_meshes):
    """Return an object that instances a group or directly references a mesh."""
    if (name, default_material) in group_written:
        grp = group_written[(name, default_material)]
        ob = bpy.data.objects.new(name=name, object_data=None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = grp
        ob.empty_display_size = 0.01
        return ob
    me, alpha = component_meshes.get((name, default_material), (None, False))
    if me is not None:
        ob = bpy.data.objects.new(name, me)
        if alpha:
            ob.show_transparent = True
        me.update(calc_edges=True)
        return ob
    # Fallback — empty
    return bpy.data.objects.new(name, None)


# ---------------------------------------------------------------------------
# Entity hierarchy (ports write_entities)
# ---------------------------------------------------------------------------

def _node_has_geometry(node, layers_skip):
    """Check whether a node or any of its descendants contain mesh data."""
    mesh = node.get("mesh")
    if mesh and mesh.get("vertices"):
        return True
    for child in node.get("children", []):
        if child.get("hidden"):
            continue
        child_layer = child.get("layer_name")
        if layers_skip and child_layer in layers_skip:
            continue
        if _node_has_geometry(child, layers_skip):
            return True
    return False


def _count_visible_children(node, layers_skip):
    """Count visible (non-hidden, non-skipped) children of a node."""
    count = 0
    for child in node.get("children", []):
        if child.get("hidden"):
            continue
        child_layer = child.get("layer_name")
        if layers_skip and child_layer in layers_skip:
            count += 1  # still counts — will go into hidden-tag collection
            continue
        count += 1
    return count


def write_entities(
    node,
    parent_transform,
    default_material,
    etype,
    parent_obj,
    parent_location,
    materials,
    component_skip,
    component_stats,
    group_written,
    component_meshes,
    layers_skip,
    target_collection=None,
    depth=0,
):
    """Recursively build Blender objects from the entity tree.

    *target_collection* overrides ``bpy.context.collection`` for linking
    objects.  Used to place hidden-tag entities into their own collection.
    """
    coll = target_collection or bpy.context.collection
    name = node["name"]

    # Deduplicated component — record transform only
    if etype == EntityType.component:
        def_name = node.get("definition_name", name)
        if (def_name, default_material) in component_skip:
            component_stats[(def_name, default_material)].append(
                [list(row) for row in Matrix(parent_transform)]
            )
            return

    # Build mesh
    # Anonymous SketchUp groups (raw name "G-") all get renamed to the same
    # generic "G-G-" by the caller before reaching here -- caching by name
    # alone makes unrelated anonymous groups collide in component_meshes,
    # silently reusing (or losing) each other's geometry. Component
    # instances legitimately share cache by their real definition-derived
    # name; only groups need a guaranteed-unique key (id(node) is unique
    # per node dict instance and never collides).
    if etype == EntityType.component:
        mesh_key = (name, default_material)
    else:
        mesh_key = (id(node), default_material)
    if mesh_key in component_meshes:
        me, alpha = component_meshes[mesh_key]
    else:
        me, alpha = build_mesh(node.get("mesh"), name, materials)
        component_meshes[mesh_key] = (me, alpha)

    visible_children = _count_visible_children(node, layers_skip)

    # Skip empty groups that have no geometry anywhere in their subtree
    if not me and visible_children == 0:
        return
    if not me and etype == EntityType.group and not _node_has_geometry(node, layers_skip):
        return

    # Create a sub-collection for top-level groups to spread objects across
    # multiple collections and reduce depsgraph churn.
    sub_collection = None
    if depth == 1 and visible_children > 0 and name != "_(Loose Entity)":
        sub_collection = bpy.data.collections.new(name)
        coll.children.link(sub_collection)

    link_coll = sub_collection or coll

    hide_empty = False

    if visible_children == 0 or name == "_(Loose Entity)":
        ob = bpy.data.objects.new(name, me)
        ob.matrix_world = Matrix(parent_transform)
        if me:
            me.update(calc_edges=True)
    else:
        ob = bpy.data.objects.new(name, None)
        ob.matrix_world = Matrix(parent_transform)
        hide_empty = True
        if me:
            ob_mesh = bpy.data.objects.new("_" + name + " (Loose Mesh)", me)
            ob_mesh.matrix_world = Matrix(parent_transform)
            me.update(calc_edges=True)
            ob_mesh.parent = ob
            ob_mesh.location = Vector((0, 0, 0))
            link_coll.objects.link(ob_mesh)

    loc = ob.location
    nested_location = Vector((loc[0], loc[1], loc[2]))

    if parent_obj is not None and parent_obj.name != "_(Loose Entity)":
        ob.parent = parent_obj
        ob.location -= parent_location

    if visible_children > 0:
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Vector((1, 0, 0, 0))
        ob.scale = Vector((1, 1, 1))

    link_coll.objects.link(ob)
    ob.hide_set(hide_empty)

    for child in node.get("children", []):
        if child.get("hidden"):
            continue

        child_type = child["type"]
        child_mat = _inherent_mat(child.get("material_name"), default_material)

        # If the child is on a skipped layer, redirect it (and its subtree)
        # into a per-tag hidden collection instead of skipping it entirely.
        child_coll = sub_collection or target_collection
        child_layer = child.get("layer_name")
        if layers_skip and child_layer in layers_skip:
            child_coll = get_hidden_tag_collection(child_layer)

        child_transform = parent_transform
        if child.get("transform"):
            child_transform = Matrix(parent_transform) @ Matrix(child["transform"])
            child_transform = [list(row) for row in child_transform]

        if child_type == "group":
            # Generate safe name the same way the original does
            temp_name = child["name"]
            gname = "G-" + group_safe_name(temp_name)
            child_copy = dict(child)
            child_copy["name"] = gname
            write_entities(
                child_copy, child_transform, child_mat, EntityType.group,
                ob, nested_location,
                materials, component_skip, component_stats,
                group_written, component_meshes, layers_skip,
                target_collection=child_coll,
                depth=depth + 1,
            )
        elif child_type == "component_instance":
            write_entities(
                child, child_transform, child_mat, EntityType.component,
                ob, nested_location,
                materials, component_skip, component_stats,
                group_written, component_meshes, layers_skip,
                target_collection=child_coll,
                depth=depth + 1,
            )


# ---------------------------------------------------------------------------
# Instancing (ports instance_group_dupli_vert)
# ---------------------------------------------------------------------------

def instance_group_dupli_vert(name, default_material, component_stats, group_written, component_meshes):
    """Create VERTS-based instancing for deduplicated components."""

    def get_orientations(transforms):
        orientations = defaultdict(list)
        for t in transforms:
            loc, rot, scale = Matrix(t).decompose()
            s = (scale[0], scale[1], scale[2])
            r = (rot[0], rot[1], rot[2], rot[3])
            orientations[(s, r)].append((loc[0], loc[1], loc[2]))
        for key, locs in orientations.items():
            s, r = key
            yield s, r, locs

    for scale, rot, locs in get_orientations(component_stats[(name, default_material)]):
        verts = []
        main_loc = Vector(locs[0])
        for c in locs:
            verts.append(Vector(c) - main_loc)

        flat_verts = []
        for v in verts:
            flat_verts.extend(v)

        dme = bpy.data.meshes.new("DUPLI-" + name)
        dme.vertices.add(len(verts))
        dme.vertices.foreach_set("co", flat_verts)
        dme.update(calc_edges=True)
        dme.validate()

        dob = bpy.data.objects.new("DUPLI-" + name, dme)
        dob.location = main_loc
        dob.instance_type = "VERTS"

        ob = _instance_object_or_group(name, default_material, group_written, component_meshes)
        ob.scale = scale
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Quaternion((rot[0], rot[1], rot[2], rot[3]))
        ob.parent = dob

        bpy.context.collection.objects.link(ob)
        bpy.context.collection.objects.link(dob)
        skp_log(f"Complex group {name} {default_material} instanced {len(verts)} times")


# ---------------------------------------------------------------------------
# Camera creation (ports write_camera — headless-safe, no bpy.ops.object.add)
# ---------------------------------------------------------------------------

def write_camera(cam_record, name="Last View", aspect_ratio_fallback=16 / 9, clip_end=250.0):
    """Create a Blender camera from an intermediate CameraRecord."""
    pos = Vector(cam_record["position"])
    target = Vector(cam_record["target"])
    up = Vector(cam_record["up"])
    fov = cam_record["fov"]
    aspect_ratio = cam_record["aspect_ratio"]

    cam_data = bpy.data.cameras.new("Cam: " + name)
    ob = bpy.data.objects.new("Cam: " + name, cam_data)

    ob.location = pos

    z = pos - target
    x = up.cross(z)
    y = z.cross(x)
    x.normalize()
    y.normalize()
    z.normalize()

    ob.matrix_world.col[0] = x.resized(4)
    ob.matrix_world.col[1] = y.resized(4)
    ob.matrix_world.col[2] = z.resized(4)
    ob.matrix_world.col[3] = Vector((pos[0], pos[1], pos[2], 1.0))

    if aspect_ratio is None:
        aspect_ratio = aspect_ratio_fallback

    if fov is None:
        cam_data.type = "ORTHO"
    else:
        cam_data.angle = (math.pi * fov / 180) * aspect_ratio

    cam_data.clip_end = clip_end

    bpy.context.collection.objects.link(ob)
    return ob, cam_data


# ---------------------------------------------------------------------------
# Post-processing: fix negative-determinant transforms
# ---------------------------------------------------------------------------

# A 4x4 matrix that negates the Z column — multiplying on the right flips
# the determinant sign without changing location or the other two axes.
_FLIP_Z = Matrix((
    (1, 0, 0, 0),
    (0, 1, 0, 0),
    (0, 0, -1, 0),
    (0, 0, 0, 1),
))


def _mirror_mesh_z(me):
    """Negate Z of all vertices and reverse face winding.

    This "bakes" a Z-axis reflection into the mesh data so that the
    corresponding matrix correction (``@ _FLIP_Z``) produces the same
    world-space positions and correct outward-facing normals with a
    positive-determinant transform.
    """
    bm = bmesh.new()
    bm.from_mesh(me)
    # Negate Z of every vertex
    for v in bm.verts:
        v.co.z = -v.co.z
    # Reverse face winding to keep normals outward after the reflection
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()


def fix_negative_scales():
    """Fix objects whose world matrix has a negative determinant.

    Mirrored SketchUp components produce transforms with det < 0.  Blender
    handles these by flipping normals at render time, which is slow and can
    cause viewport flickering with many objects.

    For each affected mesh object we flip the mesh normals (reversing face
    winding) and correct the *local* matrix so the final world determinant
    is positive.  Shared meshes are duplicated where necessary so
    non-mirrored users are unaffected.

    We must modify ``matrix_local`` (not ``matrix_world``) because
    ``matrix_world`` is recomputed from the parent chain and our changes
    would be lost.
    """
    # Force a depsgraph update so matrix_world values are current.
    bpy.context.view_layer.update()

    # Group mesh objects by their mesh data-block
    mesh_users = defaultdict(list)  # mesh name -> [(ob, needs_flip)]
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.data is None:
            continue
        needs_flip = ob.matrix_world.determinant() < 0
        mesh_users[ob.data.name].append((ob, needs_flip))

    flipped_count = 0
    copied_count = 0

    for me_name, users in mesh_users.items():
        neg_users = [(ob, nf) for ob, nf in users if nf]
        pos_users = [(ob, nf) for ob, nf in users if not nf]

        if not neg_users:
            continue  # all positive — nothing to do

        if not pos_users:
            # All users are mirrored — flip normals in-place and fix
            # every user's local matrix.
            me = neg_users[0][0].data
            _mirror_mesh_z(me)
            for ob, _ in neg_users:
                ob.matrix_local = ob.matrix_local @ _FLIP_Z
                flipped_count += 1
        else:
            # Mixed: some users are mirrored, others aren't.  Duplicate
            # the mesh for the mirrored users and flip normals on the copy.
            me_orig = neg_users[0][0].data
            me_copy = me_orig.copy()
            me_copy.name = me_orig.name + ".mirror"
            _mirror_mesh_z(me_copy)
            for ob, _ in neg_users:
                ob.data = me_copy
                ob.matrix_local = ob.matrix_local @ _FLIP_Z
                flipped_count += 1
                copied_count += 1

    # Update depsgraph so world matrices reflect our local changes
    bpy.context.view_layer.update()

    skp_log(f"Fixed {flipped_count} negative-scale object(s) ({copied_count} mesh copies)")


def remove_degenerate_faces():
    """Remove zero-area faces that can cause shading artifacts."""
    removed_total = 0
    for me in bpy.data.meshes:
        bm = bmesh.new()
        bm.from_mesh(me)
        degenerate = [f for f in bm.faces if f.calc_area() < 1e-8]
        if degenerate:
            bmesh.ops.delete(bm, geom=degenerate, context='FACES')
            removed_total += len(degenerate)
            bm.to_mesh(me)
            me.update()
        bm.free()
    if removed_total:
        skp_log(f"Removed {removed_total} zero-area face(s)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Parse args after the Blender ``--`` separator
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Build a .blend from intermediate JSON")
    parser.add_argument("work_dir", help="Directory containing intermediate.json and textures/")
    parser.add_argument("output_blend", help="Output .blend file path")
    parser.add_argument("--max-instance", type=int, default=1, help="Instancing threshold")
    parser.add_argument("--scene", type=str, default="", help="Import a specific named scene")
    parser.add_argument("--clip-end", type=float, default=250.0, help="Camera far clip plane")
    args = parser.parse_args(argv)

    skp_log(f"Loading intermediate data from {args.work_dir}")
    data = load_intermediate(args.work_dir)

    # Determine hidden layers if a specific scene is requested
    layers_skip = set()
    selected_scene = None
    if args.scene:
        for sc in data.get("scenes", []):
            if sc["name"] == args.scene:
                selected_scene = sc
                layers_skip = set(sc.get("hidden_layer_names", []))
                skp_log(f"Importing scene '{args.scene}', hiding {len(layers_skip)} layer(s)")
                break

    # Set render engine — use EEVEE for fast viewport display.
    # EEVEE avoids the progressive-render flickering that Cycles causes when
    # opening files with many objects.  The engine ID changed in Blender 5.0.
    if bpy.app.version >= (5, 0, 0):
        bpy.context.scene.render.engine = "BLENDER_EEVEE"
    else:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"

    # Remove default objects (Cube, Camera, Light) that Blender creates
    for obj_name in ("Cube", "Camera", "Light"):
        ob = bpy.data.objects.get(obj_name)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)

    # --- Materials ---
    skp_log("Creating materials...")
    materials, materials_scales = write_materials(data["materials"], args.work_dir)
    skp_log(f"  {len(materials)} material(s)")

    # --- Component depths ---
    comp_depth_map = {}
    for cd in data.get("component_definitions", []):
        comp_depth_map[cd["name"]] = cd["depth"]

    entity_tree = data["entity_tree"]

    # --- Cameras ---
    skp_log("Creating cameras...")
    ren = bpy.context.scene.render
    aspect_fallback = ren.resolution_x / ren.resolution_y

    # Named scenes as cameras
    for sc in data.get("scenes", []):
        write_camera(sc["camera"], sc["name"], aspect_ratio_fallback=aspect_fallback, clip_end=args.clip_end)

    # Model camera
    if data.get("cameras"):
        cam_ob, cam_data = write_camera(
            data["cameras"][0], "Last View",
            aspect_ratio_fallback=aspect_fallback,
            clip_end=args.clip_end,
        )
        if selected_scene:
            # If importing a specific scene, use that scene's camera
            for sc in data.get("scenes", []):
                if sc["name"] == args.scene:
                    cam_ob, cam_data = write_camera(
                        sc["camera"], sc["name"],
                        aspect_ratio_fallback=aspect_fallback,
                        clip_end=args.clip_end,
                    )
                    break
        bpy.context.scene.camera = cam_ob

    # --- Deduplicated groups ---
    skp_log("Writing deduplicated groups...")
    component_skip = proxy_dict()
    group_written = {}
    component_meshes = {}
    component_stats = defaultdict(list)

    write_duplicateable_groups(
        entity_tree, comp_depth_map, args.max_instance,
        materials, component_skip, group_written, component_meshes,
    )

    # Hide the component collections
    for gname, coll in group_written.items():
        coll.hide_viewport = True

    # --- Entity hierarchy ---
    skp_log("Building entity hierarchy...")
    write_entities(
        entity_tree,
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        DEFAULT_MATERIAL_NAME,
        EntityType.none,
        None,
        Vector((0, 0, 0)),
        materials,
        component_skip,
        component_stats,
        group_written,
        component_meshes,
        layers_skip,
    )

    # --- Instancing ---
    skp_log("Creating instances...")
    for k in component_stats:
        name, mat = k
        instance_group_dupli_vert(name, mat, component_stats, group_written, component_meshes)

    # --- Exclude hidden-tag collections from view layer ---
    if _hidden_tag_collections:
        vl_root = bpy.context.view_layer.layer_collection
        for child_lc in vl_root.children:
            if child_lc.name.startswith("Hidden Tag: "):
                child_lc.exclude = True
        skp_log(f"Excluded {len(_hidden_tag_collections)} hidden-tag collection(s) from view layer")

    # --- Post-processing ---
    skp_log("Post-processing...")
    fix_negative_scales()
    remove_degenerate_faces()

    # Purge orphan data blocks (unused materials/images) to reduce file size
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    skp_log("Purged orphan data blocks")

    # Force all 3D viewports to SOLID shading to prevent EEVEE shader
    # compilation from freezing the GUI on first open.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.shading.type = "SOLID"
                        space.shading.color_type = "MATERIAL"

    # --- Save ---
    skp_log(f"Saving {args.output_blend}")
    bpy.ops.wm.save_as_mainfile(filepath=args.output_blend)
    skp_log("Done.")


if __name__ == "__main__":
    main()
