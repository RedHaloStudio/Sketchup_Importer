#!/usr/bin/env python
"""Render a PNG preview of a .blend file.

Runs inside Blender headless::

    blender --background model.blend --python render_preview.py -- output.png
"""

import math
import sys

import bpy


def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    if not argv:
        print("Usage: blender --background file.blend --python render_preview.py -- output.png", file=sys.stderr)
        sys.exit(1)

    output_path = argv[0]

    scene = bpy.context.scene

    # --- Lighting ---
    # Add a sun light for key illumination
    sun_data = bpy.data.lights.new("Preview Sun", type="SUN")
    sun_data.energy = 3.0
    sun_obj = bpy.data.objects.new("Preview Sun", sun_data)
    bpy.context.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(45), math.radians(15), math.radians(30))

    # Light world background for ambient fill
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    if not world.node_tree:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.7, 0.75, 0.8, 1.0)
        bg.inputs["Strength"].default_value = 0.5

    # --- Render settings ---
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = output_path

    # Prefer EEVEE for speed; the engine should already be set by blend_builder
    # but ensure it in case the file was created differently.
    if bpy.app.version >= (5, 0, 0):
        scene.render.engine = "BLENDER_EEVEE"
    else:
        scene.render.engine = "BLENDER_EEVEE_NEXT"

    # --- Render ---
    bpy.ops.render.render(write_still=True)
    print(f"Preview saved to {output_path}")


if __name__ == "__main__":
    main()
