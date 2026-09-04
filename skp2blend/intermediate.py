"""Shared intermediate JSON schema for the two-stage SKP-to-Blend converter.

Pure Python — no external dependencies. Imported by both skp_extractor.py
(Stage 1, runs under Wine) and blend_builder.py (Stage 2, runs under Blender).
"""

import json
import os

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Data helpers — plain dicts are used instead of dataclasses so the module
# works on the Windows-embeddable Python 3.11 distribution (no pip).
# ---------------------------------------------------------------------------

def make_texture_record(
    filename,
    width,
    height,
    s_scale=1.0,
    t_scale=1.0,
    use_alpha_channel=False,
):
    return {
        "filename": filename,
        "width": width,
        "height": height,
        "s_scale": s_scale,
        "t_scale": t_scale,
        "use_alpha_channel": use_alpha_channel,
    }


def make_material_record(
    name,
    color_rgba,
    opacity=1.0,
    texture=None,
):
    """Create a material record.

    Parameters
    ----------
    color_rgba : list[int]
        [R, G, B, A] with values 0-255.
    texture : dict | None
        Result of ``make_texture_record`` or ``None``.
    """
    return {
        "name": name,
        "color_rgba": list(color_rgba),
        "opacity": opacity,
        "texture": texture,
    }


def make_mesh_data(
    vertices,
    triangles,
    uvs_per_triangle,
    triangle_material_indices,
    triangle_smooth,
    face_materials,
):
    """Create a mesh-data record.

    Parameters
    ----------
    vertices : list[list[float]]
        [[x, y, z], ...] in **meters**.
    triangles : list[list[int]]
        [[i0, i1, i2], ...] vertex-index triples.
    uvs_per_triangle : list[list[float]]
        [[u0, v0, u1, v1, u2, v2], ...] — six floats per triangle matching
        the existing ``uv_list`` format in ``write_mesh_data``.
    triangle_material_indices : list[int]
        Per-triangle material slot index into *face_materials*.
    triangle_smooth : list[bool]
        Per-triangle smooth flag.
    face_materials : list[str]
        Ordered list of material names corresponding to slot indices.
    """
    return {
        "vertices": vertices,
        "triangles": triangles,
        "uvs_per_triangle": uvs_per_triangle,
        "triangle_material_indices": triangle_material_indices,
        "triangle_smooth": triangle_smooth,
        "face_materials": face_materials,
    }


def make_entity_node(
    node_type,
    name,
    transform=None,
    material_name=None,
    layer_name=None,
    hidden=False,
    definition_name=None,
    mesh=None,
    children=None,
):
    """Create a recursive entity-tree node.

    Parameters
    ----------
    node_type : str
        One of ``"root"``, ``"group"``, ``"component_instance"``.
    transform : list[list[float]] | None
        4x4 row-major matrix (same layout as ``sketchup.pyx`` returns).
    mesh : dict | None
        Result of ``make_mesh_data`` or ``None``.
    children : list[dict] | None
        Nested ``make_entity_node`` dicts.
    """
    return {
        "type": node_type,
        "name": name,
        "transform": transform,
        "material_name": material_name,
        "layer_name": layer_name,
        "hidden": hidden,
        "definition_name": definition_name,
        "mesh": mesh,
        "children": children or [],
    }


def make_camera_record(position, target, up, fov, perspective, aspect_ratio):
    """Create a camera record.

    Parameters
    ----------
    position, target, up : list[float]
        3-element lists in **meters**.
    fov : float | None
        Field of view in degrees, or ``None`` for orthographic.
    perspective : bool
    aspect_ratio : float | None
        ``None`` when the camera uses the dynamic/screen ratio.
    """
    return {
        "position": list(position),
        "target": list(target),
        "up": list(up),
        "fov": fov,
        "perspective": perspective,
        "aspect_ratio": aspect_ratio,
    }


def make_scene_record(name, camera, hidden_layer_names=None):
    return {
        "name": name,
        "camera": camera,
        "hidden_layer_names": hidden_layer_names or [],
    }


def make_component_def_record(name, depth):
    return {"name": name, "depth": depth}


# ---------------------------------------------------------------------------
# Top-level document
# ---------------------------------------------------------------------------

def make_intermediate(
    materials,
    component_definitions,
    entity_tree,
    cameras,
    scenes=None,
):
    """Build the complete intermediate dict ready for JSON serialization."""
    return {
        "schema_version": SCHEMA_VERSION,
        "materials": materials,
        "component_definitions": component_definitions,
        "entity_tree": entity_tree,
        "cameras": cameras,
        "scenes": scenes or [],
    }


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def save_intermediate(data, work_dir):
    """Write *data* to ``<work_dir>/intermediate.json``."""
    os.makedirs(work_dir, exist_ok=True)
    path = os.path.join(work_dir, "intermediate.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def load_intermediate(work_dir):
    """Read and return the intermediate dict from *work_dir*."""
    path = os.path.join(work_dir, "intermediate.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
