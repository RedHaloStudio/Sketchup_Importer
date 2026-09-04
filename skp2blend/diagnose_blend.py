import bpy
import sys

bpy.ops.wm.open_mainfile(filepath="/data/kornlada.blend")

print("=" * 70)
print("BLEND FILE DIAGNOSTICS")
print("=" * 70)

# Basic counts
print(f"\nObjects:      {len(bpy.data.objects)}")
print(f"Meshes:       {len(bpy.data.meshes)}")
print(f"Materials:    {len(bpy.data.materials)}")
print(f"Images:       {len(bpy.data.images)}")
print(f"Collections:  {len(bpy.data.collections)}")
print(f"Cameras:      {len(bpy.data.cameras)}")

# Object type breakdown
from collections import Counter
type_counts = Counter(ob.type for ob in bpy.data.objects)
print(f"\nObject types: {dict(type_counts)}")

# Instance types
instance_counts = Counter(ob.instance_type for ob in bpy.data.objects if ob.instance_type != 'NONE')
if instance_counts:
    print(f"Instance types: {dict(instance_counts)}")

# Check for objects with VERTS instancing (dupli-verts)
dupli_verts = [ob for ob in bpy.data.objects if ob.instance_type == 'VERTS']
if dupli_verts:
    print(f"\nDUPLI-VERT objects ({len(dupli_verts)}):")
    for ob in dupli_verts:
        child_count = len([c for c in bpy.data.objects if c.parent == ob])
        vert_count = len(ob.data.vertices) if ob.data else 0
        print(f"  {ob.name}: {vert_count} verts (instances) x {child_count} child(ren)")

# Check for COLLECTION instancing
collection_instances = [ob for ob in bpy.data.objects if ob.instance_type == 'COLLECTION']
if collection_instances:
    print(f"\nCOLLECTION instance objects ({len(collection_instances)}):")
    for ob in collection_instances:
        coll = ob.instance_collection
        coll_name = coll.name if coll else "NONE"
        coll_objs = len(coll.objects) if coll else 0
        print(f"  {ob.name} -> collection '{coll_name}' ({coll_objs} objects)")

# Mesh statistics
print("\n--- Mesh Statistics ---")
total_verts = 0
total_polys = 0
total_loops = 0
large_meshes = []
invalid_meshes = []
meshes_no_mat = []
meshes_many_mats = []

for me in bpy.data.meshes:
    nv = len(me.vertices)
    np = len(me.polygons)
    nl = len(me.loops)
    total_verts += nv
    total_polys += np
    total_loops += nl
    if nv > 10000:
        large_meshes.append((me.name, nv, np))
    if len(me.materials) == 0 and np > 0:
        meshes_no_mat.append(me.name)
    if len(me.materials) > 10:
        meshes_many_mats.append((me.name, len(me.materials)))
    # Validate
    is_valid = me.validate(verbose=False)
    if is_valid:  # validate returns True if it fixed something
        invalid_meshes.append(me.name)

print(f"Total vertices:  {total_verts}")
print(f"Total polygons:  {total_polys}")
print(f"Total loops:     {total_loops}")

if large_meshes:
    print(f"\nLarge meshes (>10k verts):")
    for name, nv, np in sorted(large_meshes, key=lambda x: -x[1]):
        print(f"  {name}: {nv} verts, {np} polys")

if invalid_meshes:
    print(f"\nMeshes with validation issues ({len(invalid_meshes)}):")
    for name in invalid_meshes[:20]:
        print(f"  {name}")

if meshes_no_mat:
    print(f"\nMeshes with polygons but no materials ({len(meshes_no_mat)}):")
    for name in meshes_no_mat[:20]:
        print(f"  {name}")

if meshes_many_mats:
    print(f"\nMeshes with >10 material slots:")
    for name, count in meshes_many_mats:
        print(f"  {name}: {count} materials")

# Object hierarchy depth
def max_depth(ob, d=0):
    children = [c for c in bpy.data.objects if c.parent == ob]
    if not children:
        return d
    return max(max_depth(c, d+1) for c in children)

roots = [ob for ob in bpy.data.objects if ob.parent is None]
print(f"\nRoot objects: {len(roots)}")
deepest = 0
deepest_name = ""
for r in roots:
    d = max_depth(r)
    if d > deepest:
        deepest = d
        deepest_name = r.name
print(f"Max hierarchy depth: {deepest} (from '{deepest_name}')")

# Hidden objects
hidden = sum(1 for ob in bpy.data.objects if ob.hide_viewport or ob.hide_get())
print(f"Hidden objects: {hidden}")

# Objects with negative scale (can cause rendering issues)
neg_scale = [ob for ob in bpy.data.objects if any(s < 0 for s in ob.scale)]
if neg_scale:
    print(f"\nObjects with negative scale ({len(neg_scale)}):")
    for ob in neg_scale[:10]:
        print(f"  {ob.name}: scale={tuple(ob.scale)}")

# Check render engine
print(f"\nRender engine: {bpy.context.scene.render.engine}")

# Material issues
print("\n--- Material Diagnostics ---")
for mat in bpy.data.materials:
    issues = []
    if mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if node.image is None:
                    issues.append("Image Texture node with no image")
                elif node.image.packed_file is None:
                    issues.append(f"Unpacked image: {node.image.name}")
                elif node.image.size[0] == 0 or node.image.size[1] == 0:
                    issues.append(f"Zero-size image: {node.image.name}")
    if issues:
        print(f"  {mat.name}: {', '.join(issues)}")

# Check for extremely small images (potential texture issues)
print("\n--- Small Textures (may look wrong) ---")
for img in bpy.data.images:
    if img.name == "Render Result":
        continue
    w, h = img.size
    if w > 0 and h > 0 and (w < 16 or h < 16):
        users = sum(1 for mat in bpy.data.materials if mat.node_tree and
                    any(n.type == 'TEX_IMAGE' and n.image == img for n in mat.node_tree.nodes))
        print(f"  {img.name}: {w}x{h} (used by {users} material(s))")

# Depsgraph evaluation
print("\n--- Scene evaluation ---")
dg = bpy.context.evaluated_depsgraph_get()
print(f"Depsgraph updates: {len(dg.updates)}")
eval_objects = sum(1 for _ in dg.object_instances)
print(f"Evaluated object instances (with duplis): {eval_objects}")

print("\n" + "=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
