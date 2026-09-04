# skp2blend

Convert SketchUp `.skp` files to Blender `.blend` (and optionally Wavefront `.obj`) on Linux amd64 — no SketchUp installation required.

## Motivation

The SketchUp C SDK and its Python bindings (`sketchup.pyd`) are Windows-only. This makes batch-converting `.skp` files on Linux servers or CI pipelines impossible without a Windows machine. skp2blend solves this by packaging everything into a single Docker image:

- **Wine** runs the Windows Python interpreter and SketchUp SDK to read `.skp` files
- **Blender headless** builds the `.blend` output with full material, texture, camera, and hierarchy support
- **Pure-Python OBJ export** provides a lightweight alternative output format with no Blender dependency

The result is a self-contained CLI tool that runs on any Linux amd64 host with Docker.

## Quick start

```bash
# Using the convenience wrapper (builds/pulls the Docker image as "skp2blend")
./convert.sh model.skp model.blend

# Produce both .blend and .obj
./convert.sh model.skp model.blend --also-obj

# OBJ only (faster — skips Blender entirely)
./convert.sh model.skp model.blend --obj-only
```

Or run the Docker image directly:

```bash
docker run --rm \
    -v "$(pwd):/data" \
    skp2blend \
    /data/model.skp /data/model.blend
```

## How it works

Conversion runs in two stages:

1. **Stage 1 — Extract** (`skp_extractor.py`, runs under Wine)
   Reads the `.skp` file via the SketchUp C SDK and writes a portable `intermediate.json` plus extracted texture files to a work directory.

2. **Stage 2 — Build .blend** (`blend_builder.py`, runs inside Blender headless)
   Reads `intermediate.json` and constructs the Blender scene: materials with Principled BSDF nodes, UV-mapped textures, cameras, the full group/component hierarchy, and deduplicated instancing for repeated components.

3. **Stage 2b — Build .obj** (`obj_builder.py`, pure Python, optional)
   Reads the same `intermediate.json`, flattens the entity tree into world-space geometry, and writes `.obj` + `.mtl` files with texture references. Useful for side-by-side comparison with the `.blend` output or as an archival format.

## CLI options

| Flag | Description |
|---|---|
| `--scene NAME` | Import a specific named SketchUp scene (applies layer visibility and camera) |
| `--max-instance N` | Instancing threshold — components appearing N+ times are deduplicated (default: 1) |
| `--clip-end F` | Camera far clip plane in meters (default: 250.0) |
| `--preview` | Render a 1920×1080 PNG preview image next to the output `.blend` |
| `--also-obj` | Also produce a `.obj` file alongside the `.blend` |
| `--obj-only` | Only produce `.obj` output, skip Blender |
| `--keep-work-dir` | Retain the intermediate work directory after conversion |
| `--work-dir PATH` | Use a specific work directory instead of a temporary one |

## Using the GHCR image

Pre-built images are published to GHCR by CI on every push to the `skp2blend` branch:

```bash
docker run --rm \
    -v "$(pwd):/data" \
    ghcr.io/recraft-ou/sketchup_importer/skp2blend:latest \
    /data/model.skp /data/model.blend --preview
```

### GPU-accelerated rendering

Pass your GPU to the container for faster EEVEE preview renders. Without a GPU, Blender falls back to software rendering (works but slower).

**NVIDIA** (requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)):

```bash
docker run --rm --gpus all \
    -v "$(pwd):/data" \
    ghcr.io/recraft-ou/sketchup_importer/skp2blend:latest \
    /data/model.skp /data/model.blend --preview
```

**AMD / Intel** (Mesa/RADV — pass the DRI render nodes):

```bash
docker run --rm --device /dev/dri \
    -v "$(pwd):/data" \
    ghcr.io/recraft-ou/sketchup_importer/skp2blend:latest \
    /data/model.skp /data/model.blend --preview
```

## Building the Docker image

The image requires the SketchUp C SDK DLLs and a compiled `sketchup.pyd`, which are not included in this repository. They can be obtained from the [upstream release](https://github.com/RedHaloStudio/Sketchup_Importer/releases/tag/0.27.0):

```bash
# Download and extract the SDK artifacts
wget -qO /tmp/sdk.zip \
    https://github.com/RedHaloStudio/Sketchup_Importer/releases/download/0.27.0/sketchup_importer-0.27.zip
unzip -q /tmp/sdk.zip -d /tmp/sdk

# Place them where the Dockerfile expects
mkdir -p sketchup_sdk/binaries/sketchup/x64
cp /tmp/sdk/sketchup_importer/SketchUpAPI.dll \
   /tmp/sdk/sketchup_importer/SketchUpCommonPreferences.dll \
   sketchup_sdk/binaries/sketchup/x64/
cp /tmp/sdk/sketchup_importer/sketchup.cp311-win_amd64.pyd sketchup.pyd

# Build
docker build -t skp2blend .
```

A GitHub Actions workflow (`.github/workflows/docker.yml`) automates this and pushes the image to GHCR on every push to the `skp2blend` branch.

## Output formats

### .blend

Full-fidelity Blender scene with:
- Principled BSDF materials with packed textures
- UV mapping
- Group/component hierarchy preserved as Blender parent-child relationships
- Named cameras from SketchUp scenes
- VERTS-based instancing for repeated components
- Negative-scale correction for mirrored components

### .obj + .mtl

Flat geometry suitable for interchange and archival:
- All transforms baked into world-space vertex positions
- Z-up to Y-up coordinate conversion (OBJ convention)
- Material colors, opacity, and texture map references in `.mtl`
- Texture files copied to a `textures/` directory alongside the `.obj`
- No hierarchy, cameras, or instancing (OBJ limitation)

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Bad input (missing file, bad arguments) |
| 2 | Stage 1 failure (extractor) |
| 3 | Stage 2 or 2b failure (builder) |
