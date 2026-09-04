# ===========================================================================
# Two-stage SKP-to-Blend converter — Docker image
#
# Build-time prerequisites (not redistributable — user must supply):
#   sketchup_sdk/   SketchUp C SDK for Windows x64
#     binaries/sketchup/x64/SketchUpAPI.dll   (+ companion DLLs)
#   sketchup.pyd    Compiled Cython extension for Windows Python 3.11 x64
#                   (built via: python setup.py build_ext --inplace)
#
# Build:
#   docker build -t skp2blend .
#
# Run:
#   docker run --rm -v /path/to/files:/data skp2blend /data/model.skp /data/model.blend
# ===========================================================================

FROM scottyhardy/docker-wine:stable-11.0

USER root
ENV DEBIAN_FRONTEND=noninteractive

# ── Extra packages not in the base image ─────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        unzip xz-utils \
        libxi6 libxrender1 libxfixes3 libglib2.0-0 libxkbcommon0 \
        libgl1 libsm6 \
    && rm -rf /var/lib/apt/lists/*

# ── Wine prefix init ────────────────────────────────────────────────────
ENV WINEDEBUG=-all
ENV WINEPREFIX=/root/.wine
ENV WINEARCH=win64

RUN xvfb-run -a wine wineboot --init && wineserver -w

# ── Windows Python 3.11 (embeddable) ───────────────────────────────────
RUN wget -qO /tmp/python-embed.zip \
        "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" && \
    mkdir -p "${WINEPREFIX}/drive_c/Python311" && \
    cd "${WINEPREFIX}/drive_c/Python311" && \
    unzip /tmp/python-embed.zip && \
    rm /tmp/python-embed.zip

# Enable import of .py files next to the embedded Python
RUN sed -i 's/^#import site/import site/' \
    "${WINEPREFIX}/drive_c/Python311/python311._pth"

# ── SketchUp SDK + compiled extension ──────────────────────────────────
COPY sketchup_sdk/binaries/sketchup/x64/*.dll "${WINEPREFIX}/drive_c/Python311/"
COPY sketchup.pyd "${WINEPREFIX}/drive_c/Python311/"

# ── Blender (headless) ─────────────────────────────────────────────────
ARG BLENDER_VERSION=5.0.1
ARG BLENDER_URL=https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz
RUN wget -qO /tmp/blender.tar.xz "${BLENDER_URL}" && \
    mkdir -p /opt/blender && \
    tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 && \
    rm /tmp/blender.tar.xz && \
    ln -s /opt/blender/blender /usr/local/bin/blender

# ── Converter scripts ──────────────────────────────────────────────────
COPY intermediate.py skputil.py skp_extractor.py blend_builder.py obj_builder.py \
     render_preview.py cli.py \
     /opt/skp2blend/

# Also copy the Python modules into the Wine Python directory so the
# extractor can import them
RUN cp /opt/skp2blend/intermediate.py /opt/skp2blend/skputil.py \
       "${WINEPREFIX}/drive_c/Python311/"

ENV PATH="/opt/skp2blend:${PATH}"

ENTRYPOINT ["python3", "/opt/skp2blend/cli.py", \
            "--blender", "/usr/local/bin/blender", \
            "--wine-python", "C:\\Python311\\python.exe"]
