#!/usr/bin/env python
"""Stage 1 — Extract data from a .skp file into the intermediate JSON format.

Runs under Wine with the Windows Python + compiled ``sketchup.pyd`` + SketchUpAPI.dll.

Usage::

    python skp_extractor.py <input.skp> <work_dir>

Produces ``<work_dir>/intermediate.json`` and ``<work_dir>/textures/``.
"""

import os
import sys
from collections import OrderedDict

# ``sketchup`` is the compiled Cython extension (sketchup.pyd on Windows).
import sketchup

# Sibling modules — will be on sys.path when invoked via cli.py or directly.
from intermediate import (
    make_camera_record,
    make_component_def_record,
    make_entity_node,
    make_intermediate,
    make_material_record,
    make_mesh_data,
    make_scene_record,
    make_texture_record,
    save_intermediate,
)
from skputil import DEFAULT_MATERIAL_NAME, keep_offset


def skp_log(*args):
    if args:
        print("SU | " + " ".join(str(a) for a in args))


# ---------------------------------------------------------------------------
# Material extraction
# ---------------------------------------------------------------------------

def extract_materials(model, work_dir):
    """Return a list of ``MaterialRecord`` dicts and a scales mapping."""
    textures_dir = os.path.join(work_dir, "textures")
    os.makedirs(textures_dir, exist_ok=True)

    materials = []
    material_scales = {}  # name -> (s_scale, t_scale)
    used_filenames = {}  # base filename -> count (for deduplication)

    for mat in model.materials:
        name = mat.name
        r, g, b, a = mat.color
        opacity = mat.opacity
        tex = mat.texture

        tex_record = None
        if tex:
            dims = tex.dimensions  # (width, height, s_scale, t_scale)
            material_scales[name] = (dims[2], dims[3])

            tex_filename = tex.name.split(os.sep)[-1]
            # Also handle backslash paths from Windows SDK
            tex_filename = tex_filename.split("\\")[-1]

            # Deduplicate filenames: multiple materials can reference the
            # same texture filename but with different content (cropped or
            # scaled differently by SketchUp).  Append a counter so each
            # material gets its own file on disk.
            if tex_filename in used_filenames:
                used_filenames[tex_filename] += 1
                base, ext = os.path.splitext(tex_filename)
                tex_filename = f"{base}_{used_filenames[tex_filename]}{ext}"
            else:
                used_filenames[tex_filename] = 0

            tex_path = os.path.join(textures_dir, tex_filename)
            try:
                tex.write(tex_path)
            except Exception as e:
                skp_log(f"Warning: could not write texture {tex_filename}: {e}")

            tex_record = make_texture_record(
                filename=tex_filename,
                width=dims[0],
                height=dims[1],
                s_scale=dims[2],
                t_scale=dims[3],
                use_alpha_channel=tex.use_alpha_channel,
            )
        else:
            material_scales[name] = (1.0, 1.0)

        materials.append(make_material_record(
            name=name,
            color_rgba=[r, g, b, a],
            opacity=opacity,
            texture=tex_record,
        ))

    return materials, material_scales


# ---------------------------------------------------------------------------
# Mesh extraction (ports write_mesh_data)
# ---------------------------------------------------------------------------

def extract_mesh(entities, name, default_material, material_scales):
    """Return a ``MeshData`` dict or ``None``."""
    verts = []
    loops_vert_idx = []
    mat_index = []
    smooth = []
    mats = keep_offset()
    seen = keep_offset()
    uv_list = []

    for f in entities.faces:
        if f.material:
            mat_number = mats[f.material.name]
        else:
            mat_number = mats[default_material]
            if default_material != DEFAULT_MATERIAL_NAME:
                try:
                    f.st_scale = material_scales[default_material]
                except KeyError:
                    pass

        vs, tri, uvs = f.tessfaces

        mapping = {}
        for i, (v, uv) in enumerate(zip(vs, uvs)):
            prev_len = len(seen)
            mapping[i] = seen[v]
            if len(seen) > prev_len:
                verts.append(list(v))
            uvs.append(uv)

        smooth_edge = False
        for edge in f.edges:
            if edge.GetSmooth():
                smooth_edge = True
                break

        for face in tri:
            f0, f1, f2 = face[0], face[1], face[2]

            if mapping[f2] == 0:
                loops_vert_idx.extend([mapping[f2], mapping[f0], mapping[f1]])
                uv_list.append([
                    uvs[f2][0], uvs[f2][1],
                    uvs[f0][0], uvs[f0][1],
                    uvs[f1][0], uvs[f1][1],
                ])
            else:
                loops_vert_idx.extend([mapping[f0], mapping[f1], mapping[f2]])
                uv_list.append([
                    uvs[f0][0], uvs[f0][1],
                    uvs[f1][0], uvs[f1][1],
                    uvs[f2][0], uvs[f2][1],
                ])

            smooth.append(smooth_edge)
            mat_index.append(mat_number)

    if not verts:
        return None

    # Build the ordered material-name list (same order as the original code)
    mats_sorted = OrderedDict(sorted(mats.items(), key=lambda x: x[1]))
    face_materials = list(mats_sorted.keys())

    triangles = list(zip(*[iter(loops_vert_idx)] * 3))
    triangles = [list(t) for t in triangles]

    return make_mesh_data(
        vertices=verts,
        triangles=triangles,
        uvs_per_triangle=uv_list,
        triangle_material_indices=mat_index,
        triangle_smooth=smooth,
        face_materials=face_materials,
    )


# ---------------------------------------------------------------------------
# Entity-tree extraction (ports write_entities recursion)
# ---------------------------------------------------------------------------

def _mat_name_from_obj(obj):
    """Return the material name string or None."""
    mat = obj.material
    if mat is None:
        return None
    return mat.name


def _layer_name_from_obj(obj):
    """Return the layer name string or None."""
    lay = obj.layer
    if lay is None:
        return None
    return lay.name


def _inherent(mat_name, default_material):
    if mat_name is None:
        mat_name = default_material
    if mat_name == DEFAULT_MATERIAL_NAME and default_material != DEFAULT_MATERIAL_NAME:
        mat_name = default_material
    return mat_name


def extract_entity_tree(entities, skp_components, material_scales):
    """Build the root EntityNode tree from the model's top-level entities."""

    def walk(entities, name, default_material, node_type):
        mesh = extract_mesh(entities, name, default_material, material_scales)

        children = []

        for group in entities.groups:
            if group.hidden:
                continue
            gmat = _inherent(_mat_name_from_obj(group), default_material)
            child = walk(
                group.entities,
                "G-" + group.name,
                gmat,
                "group",
            )
            child["transform"] = group.transform
            child["material_name"] = _mat_name_from_obj(group)
            child["layer_name"] = _layer_name_from_obj(group)
            child["hidden"] = group.hidden
            children.append(child)

        for instance in entities.instances:
            if instance.hidden:
                continue
            imat = _inherent(_mat_name_from_obj(instance), default_material)
            cdef = skp_components.get(instance.definition.name)
            if cdef is None:
                continue
            if instance.name:
                cname = instance.name + " (C-" + cdef.name + ")"
            else:
                cname = "C-" + cdef.name
            child = walk(
                cdef.entities,
                cname,
                imat,
                "component_instance",
            )
            child["transform"] = instance.transform
            child["material_name"] = _mat_name_from_obj(instance)
            child["layer_name"] = _layer_name_from_obj(instance)
            child["hidden"] = instance.hidden
            child["definition_name"] = cdef.name
            children.append(child)

        return make_entity_node(
            node_type=node_type,
            name=name,
            mesh=mesh,
            children=children,
        )

    return walk(entities, "_(Loose Entity)", DEFAULT_MATERIAL_NAME, "root")


# ---------------------------------------------------------------------------
# Camera / scene extraction
# ---------------------------------------------------------------------------

def extract_camera(camera):
    pos, target, up = camera.GetOrientation()
    fov = camera.fov  # False when ortho
    perspective = camera.perspective
    aspect_ratio = camera.aspect_ratio  # False when dynamic

    return make_camera_record(
        position=list(pos),
        target=list(target),
        up=list(up),
        fov=fov if fov is not False else None,
        perspective=perspective,
        aspect_ratio=aspect_ratio if aspect_ratio is not False else None,
    )


def extract_scenes(model):
    scenes = []
    for s in model.scenes:
        cam = extract_camera(s.camera)
        hidden = [lay.name for lay in s.layers]
        scenes.append(make_scene_record(
            name=s.name,
            camera=cam,
            hidden_layer_names=hidden,
        ))
    return scenes


# ---------------------------------------------------------------------------
# Component-depth analysis (ports SKP_util.component_deps on live SDK objects)
# ---------------------------------------------------------------------------

def _live_component_deps(entities, comp=True):
    own_depth = 1 if comp else 0
    group_depth = 0
    for group in entities.groups:
        group_depth = max(group_depth, _live_component_deps(group.entities, comp=False))

    instance_depth = 0
    for instance in entities.instances:
        instance_depth = max(
            instance_depth,
            1 + _live_component_deps(instance.definition.entities),
        )

    return max(own_depth, group_depth, instance_depth)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.skp> <work_dir>", file=sys.stderr)
        sys.exit(1)

    input_skp = sys.argv[1]
    work_dir = sys.argv[2]

    if not os.path.isfile(input_skp):
        print(f"Error: input file not found: {input_skp}", file=sys.stderr)
        sys.exit(1)

    skp_log(f"Opening {input_skp}")
    model = sketchup.Model.from_file(input_skp)

    # --- Materials ---
    skp_log("Extracting materials...")
    materials, material_scales = extract_materials(model, work_dir)
    skp_log(f"  {len(materials)} material(s)")

    # --- Component definitions & depths ---
    skp_log("Analyzing component definitions...")
    skp_components = {}
    for c in model.component_definitions:
        skp_components[c.name] = c

    comp_defs = []
    for c in model.component_definitions:
        depth = _live_component_deps(c.entities)
        comp_defs.append(make_component_def_record(c.name, depth))
    skp_log(f"  {len(comp_defs)} component definition(s)")

    # --- Entity tree ---
    skp_log("Extracting entity tree...")
    entity_tree = extract_entity_tree(model.entities, skp_components, material_scales)

    # --- Cameras ---
    skp_log("Extracting cameras...")
    cameras = [extract_camera(model.camera)]

    # --- Scenes ---
    skp_log("Extracting scenes...")
    scenes = extract_scenes(model)
    skp_log(f"  {len(scenes)} scene(s)")

    # --- Write ---
    data = make_intermediate(
        materials=materials,
        component_definitions=comp_defs,
        entity_tree=entity_tree,
        cameras=cameras,
        scenes=scenes,
    )
    out_path = save_intermediate(data, work_dir)
    skp_log(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
