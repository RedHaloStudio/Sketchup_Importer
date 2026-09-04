import bpy
bpy.ops.wm.open_mainfile(filepath="/data/kornlada.blend")

print("MATERIAL_COUNT:", len(bpy.data.materials))
print("IMAGE_COUNT:", len(bpy.data.images))
print("MESH_COUNT:", len(bpy.data.meshes))

for m in bpy.data.materials:
    has_tex = False
    tex_info = ""
    if m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE":
                has_tex = True
                if n.image:
                    tex_info = n.image.name + " packed=" + str(n.image.packed_file is not None)
                else:
                    tex_info = "NO_IMAGE_SET"
    print("MAT:", m.name, "| has_tex:", has_tex, "|", tex_info)

for img in bpy.data.images:
    print("IMG:", img.name, "| packed:", img.packed_file is not None, "| size:", img.size[0], "x", img.size[1])

uv = 0
no_uv = 0
for me in bpy.data.meshes:
    if me.uv_layers:
        uv += 1
    else:
        no_uv += 1
print("MESHES_WITH_UV:", uv)
print("MESHES_WITHOUT_UV:", no_uv)
