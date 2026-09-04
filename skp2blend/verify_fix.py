import bpy
bpy.ops.wm.open_mainfile(filepath="/data/kornlada.blend")

print("=== Timmer Gavelsida materials ===")
for m in bpy.data.materials:
    if "Timmer" in m.name:
        tex_info = "no texture"
        if m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    tex_info = f"{n.image.name} {n.image.size[0]}x{n.image.size[1]} packed={n.image.packed_file is not None}"
        print(f"  {m.name:30s} {tex_info}")

print()
print("=== Summary ===")
print(f"Materials: {len(bpy.data.materials)}")
print(f"Images: {len(bpy.data.images)}")

uv = sum(1 for me in bpy.data.meshes if me.uv_layers)
no_uv = sum(1 for me in bpy.data.meshes if not me.uv_layers)
print(f"Meshes with UV: {uv}")
print(f"Meshes without UV: {no_uv}")

# Verify all texture images have distinct content (unique sizes)
print()
print("=== All texture images and sizes ===")
for img in sorted(bpy.data.images, key=lambda i: i.name):
    if img.name == "Render Result":
        continue
    print(f"  {img.name:55s} {img.size[0]:5d}x{img.size[1]:<5d} packed={img.packed_file is not None}")
