#!/usr/bin/env python3
"""CLI orchestrator for the two-stage SKP-to-Blend converter.

Usage::

    python cli.py input.skp output.blend [--max-instance N] [--scene NAME] \\
                                         [--keep-work-dir] [--clip-end F]

Stage 1 runs ``skp_extractor.py`` under Wine (Windows Python + SketchUp SDK).
Stage 2 runs ``blend_builder.py`` inside Blender headless.

Exit codes:
    0  success
    1  bad input (missing file, bad arguments)
    2  Stage 1 failure (extractor)
    3  Stage 2 failure (builder)
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _to_wine_path(posix_path):
    """Convert a POSIX absolute path to a Wine Z:-drive path."""
    return "Z:" + posix_path.replace("/", "\\")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a SketchUp .skp file to a Blender .blend file",
    )
    parser.add_argument("input_skp", help="Path to the input .skp file")
    parser.add_argument("output_blend", help="Path for the output .blend file")
    parser.add_argument("--max-instance", type=int, default=1, help="Instancing threshold (default: 1)")
    parser.add_argument("--scene", type=str, default="", help="Import a specific named SketchUp scene")
    parser.add_argument("--clip-end", type=float, default=250.0, help="Camera far clip plane in meters")
    parser.add_argument("--keep-work-dir", action="store_true", help="Don't delete the intermediate work directory")
    parser.add_argument("--work-dir", type=str, default="", help="Use a specific work directory instead of a temp one")
    parser.add_argument("--preview", action="store_true", help="Render a PNG preview image next to the output .blend")
    parser.add_argument("--also-obj", action="store_true", help="Also produce a Wavefront OBJ alongside the .blend")
    parser.add_argument("--obj-only", action="store_true", help="Only produce OBJ output (skip Blender Stage 2)")
    parser.add_argument(
        "--wine-python",
        type=str,
        default=r"C:\Python311\python.exe",
        help="Wine path to Windows Python executable (default: C:\\Python311\\python.exe)",
    )
    parser.add_argument(
        "--blender",
        type=str,
        default="blender",
        help="Path to the Blender executable (default: blender)",
    )
    args = parser.parse_args()

    # --- Validate input ---
    input_skp = os.path.abspath(args.input_skp)
    output_blend = os.path.abspath(args.output_blend)

    if not os.path.isfile(input_skp):
        print(f"Error: input file not found: {input_skp}", file=sys.stderr)
        sys.exit(1)

    # --- Work directory ---
    if args.work_dir:
        work_dir = os.path.abspath(args.work_dir)
        os.makedirs(work_dir, exist_ok=True)
        cleanup = False
    else:
        work_dir = tempfile.mkdtemp(prefix="skp2blend_")
        cleanup = not args.keep_work_dir

    print(f"Work directory: {work_dir}")

    extractor_script = os.path.join(_THIS_DIR, "skp_extractor.py")
    builder_script = os.path.join(_THIS_DIR, "blend_builder.py")

    try:
        # =============================================================
        # Stage 1 — Extract .skp data (runs under Wine on Linux)
        # =============================================================
        print("\n=== Stage 1: Extracting SKP data ===")

        is_linux = platform.system() == "Linux"

        if is_linux:
            win_input = _to_wine_path(input_skp)
            win_work = _to_wine_path(work_dir)
            win_script = _to_wine_path(extractor_script)
            stage1_cmd = [
                "xvfb-run", "-a",
                "wine", args.wine_python,
                win_script, win_input, win_work,
            ]
        else:
            # On macOS/Windows we can run the extractor natively
            stage1_cmd = [
                sys.executable,
                extractor_script, input_skp, work_dir,
            ]

        print(f"Running: {' '.join(stage1_cmd)}")
        result = subprocess.run(stage1_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Filter out known harmless noise from Wine/libtiff/xvfb
        _noise = {"not a tiff or mdi file", "x connection to", "broken (explicit kill"}
        for line in result.stdout.decode(errors="replace").splitlines():
            if any(pat in line.lower() for pat in _noise):
                continue
            print(line)

        if result.returncode != 0:
            print(f"\nError: Stage 1 (extractor) failed with exit code {result.returncode}", file=sys.stderr)
            sys.exit(2)

        intermediate_path = os.path.join(work_dir, "intermediate.json")
        if not os.path.isfile(intermediate_path):
            print(f"\nError: Stage 1 did not produce {intermediate_path}", file=sys.stderr)
            sys.exit(2)

        print(f"Stage 1 complete — intermediate.json ({os.path.getsize(intermediate_path)} bytes)")

        # =============================================================
        # Stage 2 — Build .blend (runs inside Blender headless)
        # =============================================================
        if not args.obj_only:
            print("\n=== Stage 2: Building .blend file ===")

            stage2_cmd = [
                args.blender, "--background", "--python", builder_script,
                "--",
                work_dir, output_blend,
                "--max-instance", str(args.max_instance),
                "--clip-end", str(args.clip_end),
            ]
            if args.scene:
                stage2_cmd.extend(["--scene", args.scene])

            print(f"Running: {' '.join(stage2_cmd)}")
            result = subprocess.run(stage2_cmd)

            if result.returncode != 0:
                print(f"\nError: Stage 2 (builder) failed with exit code {result.returncode}", file=sys.stderr)
                sys.exit(3)

            if not os.path.isfile(output_blend):
                print(f"\nError: Stage 2 did not produce {output_blend}", file=sys.stderr)
                sys.exit(3)

            print(f"\nSuccess: {output_blend} ({os.path.getsize(output_blend)} bytes)")

        # =============================================================
        # Preview render
        # =============================================================
        if args.preview and not args.obj_only:
            preview_path = os.path.splitext(output_blend)[0] + ".png"
            print(f"\n=== Rendering preview to {preview_path} ===")

            render_script = os.path.join(_THIS_DIR, "render_preview.py")
            preview_cmd = [
                args.blender, "--background", output_blend,
                "--python", render_script,
                "--", preview_path,
            ]

            print(f"Running: {' '.join(preview_cmd)}")
            result = subprocess.run(preview_cmd)

            if result.returncode != 0:
                print("Warning: preview render failed", file=sys.stderr)
            elif os.path.isfile(preview_path):
                print(f"Preview: {preview_path} ({os.path.getsize(preview_path)} bytes)")

        # =============================================================
        # Stage 2b — Build OBJ (pure Python, no Blender needed)
        # =============================================================
        if args.also_obj or args.obj_only:
            obj_output = os.path.splitext(output_blend)[0] + ".obj"
            obj_builder_script = os.path.join(_THIS_DIR, "obj_builder.py")

            print("\n=== Stage 2b: Building OBJ file ===")

            stage2b_cmd = [
                sys.executable, obj_builder_script,
                work_dir, obj_output,
            ]
            if args.scene:
                stage2b_cmd.extend(["--scene", args.scene])

            print(f"Running: {' '.join(stage2b_cmd)}")
            result = subprocess.run(stage2b_cmd)

            if result.returncode != 0:
                print(f"\nError: Stage 2b (OBJ builder) failed with exit code {result.returncode}", file=sys.stderr)
                sys.exit(3)

            if not os.path.isfile(obj_output):
                print(f"\nError: Stage 2b did not produce {obj_output}", file=sys.stderr)
                sys.exit(3)

            print(f"\nSuccess: {obj_output} ({os.path.getsize(obj_output)} bytes)")

    finally:
        if cleanup:
            print(f"Cleaning up {work_dir}")
            shutil.rmtree(work_dir, ignore_errors=True)
        elif args.keep_work_dir or args.work_dir:
            print(f"Work directory retained at {work_dir}")


if __name__ == "__main__":
    main()
