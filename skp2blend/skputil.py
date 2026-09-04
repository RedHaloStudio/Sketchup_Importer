"""Standalone utility functions used by both extraction and building stages.

Ported from ``sketchup_importer/SKPutil/__init__.py`` — pure Python, no
``bpy`` or ``sketchup`` SDK imports.
"""

from collections import defaultdict
from enum import Enum

DEFAULT_MATERIAL_NAME = "DefaultMaterial"

_su_group_num = 0


class proxy_dict(dict):
    """Dictionary that transparently strips a ``_proxy`` suffix on lookup."""

    def __getitem__(self, key):
        if key.lower().endswith("_proxy"):
            try:
                return dict.__getitem__(self, key[:-6])
            except KeyError:
                return dict.__getitem__(self, key)
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            print(f"SU | KeyError: {key}, Skipping...")
            return None


class keep_offset(defaultdict):
    """Auto-incrementing index map — identical semantics to the original."""

    def __init__(self):
        defaultdict.__init__(self, int)

    def __missing__(self, _):
        return defaultdict.__len__(self)

    def __getitem__(self, item):
        number = defaultdict.__getitem__(self, item)
        self[item] = number
        return number


def group_name(name, material):
    if material != DEFAULT_MATERIAL_NAME:
        return f"{name}_{material}"
    return name


def group_safe_name(name):
    if not name:
        global _su_group_num
        _su_group_num += 1
        padded = f"{_su_group_num:03d}"
        return f"{name}No_Name_{padded}"
    return name


def inherent_default_mat(mat_name, default_material):
    """Resolve the effective material name.

    Unlike the original which receives a Material SDK object, this version
    takes the material *name* (a string or ``None``).
    """
    if mat_name is None:
        mat_name = default_material
    if mat_name == DEFAULT_MATERIAL_NAME and default_material != DEFAULT_MATERIAL_NAME:
        mat_name = default_material
    return mat_name


class EntityType(Enum):
    none = 0
    group = 1
    component = 2
    outer = 3


# ---------------------------------------------------------------------------
# Component-depth analysis — operates on the intermediate EntityNode tree
# ---------------------------------------------------------------------------

def component_deps(node):
    """Return the nesting depth of components under *node* (an EntityNode dict).

    This mirrors ``SKP_util.component_deps`` but works on the serialised
    intermediate tree rather than live SDK objects.
    """
    is_component = node.get("type") == "component_instance"
    own_depth = 1 if is_component else 0
    child_depth = 0
    for child in node.get("children", []):
        child_depth = max(child_depth, component_deps(child))
    return max(own_depth, child_depth)
