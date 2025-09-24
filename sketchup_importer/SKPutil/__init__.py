# <pep8-80 compliant>

from collections import OrderedDict, defaultdict
from enum import Enum

default_material_name = "Material"
su_group_num = 0


class proxy_dict(dict):
    """
    Class that emulates a dictionary
    and returns the real definition value
    even when asking for a _proxy one
    """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def __getitem__(self, key):
        if key.lower().endswith("_proxy"):
            try:
                return dict.__getitem__(self, key[:-6])
            except KeyError as _e:
                return dict.__getitem__(self, key)

        return dict.__getitem__(self, key)


class keep_offset(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, int)

    def __missing__(self, _):
        return defaultdict.__len__(self)

    def __getitem__(self, item):
        number = defaultdict.__getitem__(self, item)
        self[item] = number

        return number


def group_name(name, material):
    if material != default_material_name:
        return f"{name}_{material}"
    else:
        return name


def group_safe_name(name):
    if not name:
        global su_group_num
        su_group_num += 1
        padded_num_str = f"{su_group_num:03d}"
        su_group_num_str = "No_Name_" + padded_num_str
        return f"{name}{su_group_num_str}"

    return name


def inherent_default_mat(mat, default_material):
    mat_name = mat.name if mat else default_material
    if mat_name == (default_material_name and default_material != default_material_name):
        mat_name = default_material

    return mat_name


class EntityType(Enum):
    none = 0
    group = 1
    component = 2
    outer = 3


class SKP_util:
    layers_skip = []

    def component_deps(self, entities, comp=True):
        own_depth = 1 if comp else 0
        group_depth = 0
        for group in entities.groups:
            if self.layers_skip and group.layer in self.layers_skip:
                continue
            group_depth = max(group_depth, self.component_deps(group.entities, comp=False))

        instance_depth = 0
        for instance in entities.instances:
            if self.layers_skip and instance.layer in self.layers_skip:
                continue
            instance_depth = max(instance_depth, 1 + self.component_deps(instance.definition.entities))

        return max(own_depth, group_depth, instance_depth)
