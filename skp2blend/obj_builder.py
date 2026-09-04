#!/usr/bin/env python3
"""Stage 2b — Build a Wavefront OBJ (+MTL) file from intermediate JSON.

Pure Python — no Blender or numpy dependency.

Usage::

    python3 obj_builder.py <work_dir> <output.obj> [--scene NAME]

Reads ``intermediate.json`` from *work_dir*, flattens the entity tree
into world-space geometry, and writes ``<output>.obj`` + ``<output>.mtl``
alongside each other.  Texture files are copied into an ``textures/``
directory next to the OBJ.
"""

import argparse
import os
import shutil
import sys

_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

from intermediate import load_intermediate  # noqa: E402, I001
from skputil import DEFAULT_MATERIAL_NAME, inherent_default_mat  # noqa: E402


# ---------------------------------------------------------------------------
# Pure-Python 4x4 matrix math (list-of-lists, row-major)
# ---------------------------------------------------------------------------

_IDENTITY = [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
]


def mat4_multiply(a, b):
    """Multiply two 4x4 matrices (list-of-4-lists-of-4-floats)."""
    result = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            s = 0.0
            for k in range(4):
                s += a[i][k] * b[k][j]
            result[i][j] = s
    return result


def mat4_transform_point(m, p):
    """Transform a 3D point *p* by 4x4 matrix *m* (homogeneous, w=1)."""
    x = m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + m[0][3]
    y = m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + m[1][3]
    z = m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + m[2][3]
    return [x, y, z]


# ---------------------------------------------------------------------------
# MTL writer
# ---------------------------------------------------------------------------

def write_mtl(material_records, textures_src_dir, mtl_path, output_dir):
    """Write a Wavefront .mtl file and copy referenced textures.

    Returns a set of material names that were written.
    """
    textures_dst_dir = os.path.join(output_dir, "textures")
    written_names = set()

    with open(mtl_path, "w", encoding="utf-8") as f:
        # Default material
        f.write(f"newmtl {DEFAULT_MATERIAL_NAME}\n")
        f.write("Kd 0.8 0.8 0.8\n")
        f.write("d 1.0\n\n")
        written_names.add(DEFAULT_MATERIAL_NAME)

        for rec in material_records:
            name = rec["name"]
            r, g, b, a = rec["color_rgba"]
            opacity = rec.get("opacity", round(a / 255.0, 4))
            tex = rec.get("texture")

            f.write(f"newmtl {name}\n")
            f.write(f"Kd {r / 255.0:.6f} {g / 255.0:.6f} {b / 255.0:.6f}\n")
            f.write(f"d {opacity}\n")

            if tex:
                tex_filename = tex["filename"]
                src = os.path.join(textures_src_dir, tex_filename)
                if os.path.isfile(src):
                    os.makedirs(textures_dst_dir, exist_ok=True)
                    dst = os.path.join(textures_dst_dir, tex_filename)
                    if not os.path.isfile(dst):
                        shutil.copy2(src, dst)
                    f.write(f"map_Kd textures/{tex_filename}\n")
                else:
                    print(f"OBJ | Warning: texture not found: {src}")

            f.write("\n")
            written_names.add(name)

    return written_names


# ---------------------------------------------------------------------------
# OBJ writer
# ---------------------------------------------------------------------------

def write_obj(data, obj_path, mtl_filename):
    """Write a Wavefront .obj file from intermediate data.

    Flattens the entity tree, baking transforms into world-space vertex
    positions.  Each mesh leaf becomes a named ``o`` block.  All geometry
    is included regardless of tag/layer visibility — OBJ has no concept
    of collection exclusion.
    """
    entity_tree = data["entity_tree"]

    # Collected geometry: list of dicts with keys:
    #   name, vertices (world-space), triangles, uvs, tri_mat_names
    meshes = []

    _walk_entities(
        entity_tree,
        _IDENTITY,
        DEFAULT_MATERIAL_NAME,
        meshes,
    )

    # Write OBJ
    v_offset = 1   # OBJ indices are 1-based
    vt_offset = 1

    with open(obj_path, "w", encoding="utf-8") as f:
        f.write("# Exported by skp2blend obj_builder\n")
        f.write(f"mtllib {mtl_filename}\n\n")

        for mesh_entry in meshes:
            obj_name = mesh_entry["name"]
            verts = mesh_entry["vertices"]
            tris = mesh_entry["triangles"]
            uvs = mesh_entry["uvs"]
            tri_mat_names = mesh_entry["tri_mat_names"]
            has_uvs = bool(uvs) and any(uvs)

            f.write(f"o {obj_name}\n")

            # Vertices — convert Z-up (SketchUp/Blender) to Y-up (OBJ convention)
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[2]:.6f} {-v[1]:.6f}\n")

            # UVs
            if has_uvs:
                for i, uv_data in enumerate(uvs):
                    if uv_data:
                        # Each entry is [u0, v0, u1, v1, u2, v2]
                        f.write(f"vt {uv_data[0]:.6f} {uv_data[1]:.6f}\n")
                        f.write(f"vt {uv_data[2]:.6f} {uv_data[3]:.6f}\n")
                        f.write(f"vt {uv_data[4]:.6f} {uv_data[5]:.6f}\n")
                    else:
                        f.write("vt 0.0 0.0\n")
                        f.write("vt 0.0 0.0\n")
                        f.write("vt 0.0 0.0\n")

            # Faces grouped by material
            current_mat = None
            for tri_idx, tri in enumerate(tris):
                mat_name = tri_mat_names[tri_idx] if tri_idx < len(tri_mat_names) else DEFAULT_MATERIAL_NAME
                if mat_name != current_mat:
                    f.write(f"usemtl {mat_name}\n")
                    current_mat = mat_name

                if has_uvs:
                    vt0 = vt_offset + tri_idx * 3
                    f.write(
                        f"f {tri[0] + v_offset}/{vt0}"
                        f" {tri[1] + v_offset}/{vt0 + 1}"
                        f" {tri[2] + v_offset}/{vt0 + 2}\n"
                    )
                else:
                    f.write(
                        f"f {tri[0] + v_offset}"
                        f" {tri[1] + v_offset}"
                        f" {tri[2] + v_offset}\n"
                    )

            v_offset += len(verts)
            if has_uvs:
                vt_offset += len(tris) * 3

            f.write("\n")

    print(f"OBJ | Wrote {len(meshes)} object(s), {v_offset - 1} vertices total")


def _walk_entities(node, parent_mat, default_material, meshes):
    """Recursively walk the entity tree, collecting flattened mesh data."""
    if node.get("hidden"):
        return

    # Compute this node's world transform
    node_transform = node.get("transform")
    if node_transform:
        world_mat = mat4_multiply(parent_mat, node_transform)
    else:
        world_mat = parent_mat

    # Emit mesh if present
    mesh_data = node.get("mesh")
    if mesh_data and mesh_data.get("vertices"):
        _emit_mesh(node["name"], mesh_data, world_mat, default_material, meshes)

    # Recurse into children
    for child in node.get("children", []):
        child_mat = inherent_default_mat(child.get("material_name"), default_material)
        _walk_entities(child, world_mat, child_mat, meshes)


def _emit_mesh(name, mesh_data, world_mat, default_material, meshes):
    """Transform vertices to world space and resolve material names."""
    verts = mesh_data["vertices"]
    tris = mesh_data["triangles"]
    uvs = mesh_data.get("uvs_per_triangle", [])
    mat_indices = mesh_data.get("triangle_material_indices", [])
    face_materials = mesh_data.get("face_materials", [])

    # Transform vertices to world space
    world_verts = [mat4_transform_point(world_mat, v) for v in verts]

    # Resolve per-triangle material names
    tri_mat_names = []
    for idx in mat_indices:
        if idx < len(face_materials):
            mat_name = face_materials[idx]
            # Apply material inheritance
            mat_name = inherent_default_mat(mat_name, default_material)
            tri_mat_names.append(mat_name)
        else:
            tri_mat_names.append(default_material)

    meshes.append({
        "name": name,
        "vertices": world_verts,
        "triangles": tris,
        "uvs": uvs,
        "tri_mat_names": tri_mat_names,
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build a Wavefront OBJ from intermediate JSON")
    parser.add_argument("work_dir", help="Directory containing intermediate.json and textures/")
    parser.add_argument("output_obj", help="Output .obj file path")
    parser.add_argument("--scene", type=str, default="", help="Import a specific named scene")
    args = parser.parse_args()

    print(f"OBJ | Loading intermediate data from {args.work_dir}")
    data = load_intermediate(args.work_dir)

    obj_path = os.path.abspath(args.output_obj)
    output_dir = os.path.dirname(obj_path)
    base = os.path.splitext(os.path.basename(obj_path))[0]
    mtl_filename = base + ".mtl"
    mtl_path = os.path.join(output_dir, mtl_filename)

    # Write materials
    textures_src_dir = os.path.join(args.work_dir, "textures")
    print(f"OBJ | Writing materials to {mtl_path}")
    written_mats = write_mtl(data["materials"], textures_src_dir, mtl_path, output_dir)
    print(f"OBJ | {len(written_mats)} material(s)")

    # Write geometry
    print(f"OBJ | Writing geometry to {obj_path}")
    write_obj(data, obj_path, mtl_filename)

    print(f"OBJ | Done: {obj_path}")


if __name__ == "__main__":
    main()
