"""
Testbed for debugging bpy part of codes in blender editor.

:Author: jupiterbjy@gmail.com
:Version: 2024-12-01
:License: MIT
"""

import time
from typing import Tuple, Iterator

import bpy


_TEST_DATA = """
Simple Table Model

```obj
v 0 12 15
v 0 12 18
v 0 12 44
v 0 12 47
v 0 48 15
v 0 48 18
v 0 48 44
v 0 48 47
v 0 50 15
v 0 50 47
v 3 12 15
v 3 12 18
v 3 12 44
v 3 12 47
v 3 48 15
v 3 48 18
v 3 48 44
v 3 48 47
v 30 12 15
v 30 12 18
v 30 12 44
v 30 12 47
v 30 48 15
v 30 48 18
v 30 48 44
v 30 48 47
v 33 12 15
v 33 12 18
v 33 12 44
v 33 12 47
v 33 48 15
v 33 48 18
v 33 48 44
v 33 48 47
v 60 12 15
v 60 12 18
v 60 12 44
v 60 12 47
v 60 48 15
v 60 48 18
v 60 48 44
v 60 48 47
v 63 12 15
v 63 12 18
v 63 12 44
v 63 12 47
v 63 48 15
v 63 48 18
v 63 48 44
v 63 48 47
v 63 50 15
v 63 50 47
f 1 2 5
f 1 11 2
f 1 5 11
f 2 6 5
f 2 16 6
f 2 11 12
f 2 12 16
f 3 4 7
f 3 13 4
f 3 7 13
f 4 8 7
f 4 18 8
f 4 13 14
f 4 14 18
f 5 6 9
f 5 15 11
f 6 7 9
f 6 16 7
f 7 8 9
f 7 17 13
f 7 16 17
f 8 10 9
f 8 52 10
f 8 18 52
f 9 10 52
f 9 52 15
f 11 16 12
f 11 15 16
f 13 18 14
f 13 17 18
f 15 23 16
f 16 23 17
f 17 23 18
f 18 23 52
f 19 20 23
f 19 27 20
f 19 23 27
f 20 24 23
f 20 32 24
f 20 27 28
f 20 28 32
f 21 22 25
f 21 29 22
f 21 25 29
f 22 26 25
f 22 34 26
f 22 29 30
f 22 30 34
f 23 24 31
f 23 31 27
f 23 39 52
f 24 25 31
f 24 32 25
f 25 26 31
f 25 33 29
f 25 32 33
f 26 34 31
f 27 32 28
f 27 31 32
f 29 34 30
f 29 33 34
f 31 39 32
f 32 39 33
f 33 39 34
f 34 39 42
f 35 36 39
f 35 43 36
f 35 39 43
f 36 40 39
f 36 48 40
f 36 43 44
f 36 44 48
f 37 38 41
f 37 45 38
f 37 41 45
f 38 42 41
f 38 50 42
f 38 45 46
f 38 46 50
f 39 40 47
f 39 47 43
f 39 51 52
f 40 41 47
f 40 48 41
f 41 42 47
f 41 49 45
f 41 48 49
f 42 50 47
f 43 48 44
f 43 47 48
f 45 50 46
f 45 49 50
f 47 51 48
f 48 51 49
f 49 51 50
f 50 51 52
```

"""


# --- Utilities ---


def _redraw():
    """Trigger viewport redraw."""

    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)

    # for area in ctx.window.screen.areas:
    #     if area.type == "VIEW_3D":
    #         area.tag_redraw()


def _obj_vertex_to_bpy(line: str) -> Tuple[float, float, float]:
    """Convert obj vertex line to blender vertex coordinates.
    This is more of an additional call overhead but whatever, can't put face func alone.
    """

    # Assume it's ALWAYS 3 values
    # noinspection PyTypeChecker
    return tuple(map(float, line[2:].split()))


def _obj_face_to_bpy(line: str) -> Tuple[int, int, int]:
    """Convert obj face line to blender face indices.
    This is because obj face indices starts from 1, but bpy uses 0.
    """

    # Assume it's ALWAYS 3 values
    # noinspection PyTypeChecker
    return tuple((int(x) - 1) for x in line[2:].split())


# --- Operators ---


class GenerateMesh(bpy.types.Operator):
    """Generates Mesh"""

    bl_idname = "mesh.generate_mesh"
    bl_label = "Generate Mesh"
    bl_options = {"REGISTER", "UNDO"}

    prompt_str: bpy.props.StringProperty(
        name="Prompt",
        default="a simple barrel",
    )

    ctx_size: bpy.props.IntProperty(
        name="Context Size",
        default=4096,
        max=8192,
        min=4096,
    )

    temperature: bpy.props.FloatProperty(
        name="Temperature",
        default=0.7,
        max=1.0,
        min=0.0,
    )

    def _prep_line_iterator(self) -> Iterator[str]:
        """Return llm output line by line iterator."""

        for line in _TEST_DATA.strip().splitlines():
            # simulated thread block
            time.sleep(1)

            yield line

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        """Show prompt dialog"""

        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.types.Context):
        """Generate mesh from prompt"""

        iterator = self._prep_line_iterator()
        name = "_".join(word.lower() for word in (next(iterator).strip().split()))

        # create mesh & object, link and set as active
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        context.scene.collection.objects.link(obj)
        context.view_layer.objects.active = obj

        # prep data
        verts = []
        edges = []
        faces = []

        # generate mesh but rebuild mesh & redraw on the fly so we can see progress
        for line in iterator:

            if line.startswith("v "):
                verts.append(_obj_vertex_to_bpy(line))

            elif line.startswith("f "):
                faces.append(_obj_face_to_bpy(line))

            else:
                continue

            # update mesh & redraw
            mesh.clear_geometry()
            mesh.from_pydata(verts, edges, faces)
            _redraw()

        # set origin to geometry center
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

        return {"FINISHED"}


def draw(self, context):
    """Draw this operator in layout"""

    self.layout.operator(GenerateMesh.bl_idname, text="Generate Mesh", icon="INFO")


def register():
    """Register addon"""

    bpy.utils.register_class(GenerateMesh)
    bpy.types.VIEW3D_MT_mesh_add.append(draw)


def unregister():
    """Unregister addon"""

    bpy.utils.unregister_class(GenerateMesh)
    bpy.types.VIEW3D_MT_mesh_add.remove(draw)


if __name__ == "__main__":
    register()

    # bpy.ops.mesh.generate_mesh()

    # noinspection PyUnresolvedReferences
    bpy.ops.mesh.generate_mesh("INVOKE_DEFAULT")
