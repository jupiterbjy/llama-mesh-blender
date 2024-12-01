"""
Simple, terrible mesh generation addon using Quantized LLaMA-Mesh & llama.cpp

:Author: jupiterbjy@gmail.com
:Version: 2024-12-01
:License: MIT
"""

from typing import Tuple, Iterator

import bpy

from .llama_cpp_wrapper import LlamaCppWrapper


# --- Globals ---

bl_info = {
    "name": "llama-mesh-blender",
    "description": "Simple, terrible mesh generation addon using Quantized LLaMA-Mesh & llama.cpp",
    "author": "jupiterbjy",
    "version": (0, 1),
    "blender": (4, 1, 0),
    "location": "View3D > Add > Mesh",
    "category": "Add Mesh",
    "tracker_url": "https://github.com/jupiterbjy/llama-mesh-blender/issues",
    # ^^^ Don't report broken mesh to me, I can't fix llm!
}


_GGUF_URL = (
    "https://huggingface.co/bartowski/LLaMA-Mesh-GGUF/resolve/main/LLaMA-Mesh-Q8_0.gguf"
)

_PROMPT_TEMPLATE = (
    "Generate {} model with short suggested name in first line, "
    "then make sure to generate vertices and faces wrapped in single code block."
)

# _CHAT_FORMAT = """
# <|begin_of_text|><|start_header_id|>system<|end_header_id|>
#
# {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>
#
# {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
# """


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

        wrapper = LlamaCppWrapper(_GGUF_URL)
        prompt = _PROMPT_TEMPLATE.format(self.prompt_str)

        yield from wrapper.generate_oneshot(
            prompt, f"-c {self.ctx_size}", f"-t {self.temperature}"
        )

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


def draw(self, _context):
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
