import bpy
import numpy as np
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion, orientation_helper
from .openctm import *
from bpy.props import (
    BoolProperty,
    IntProperty,
    IntVectorProperty,
    StringProperty,
)

@orientation_helper(axis_forward="Z", axis_up="Y")
class OpenCTMImport(bpy.types.Operator, ImportHelper):
    """Import from OpenCTM Format"""
    bl_idname = "import_scene.openctm"
    bl_label = "Import OpenCTM"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".ctm"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.ctm", options={'HIDDEN'})

    uv_pref = BoolProperty(name="UV", description="Import UV", default=True)
    colour_pref = BoolProperty(name="Color", description="Import vertex colors", default=True)
    select_pref = BoolProperty(name="Select", description="Select imported object after completion", default=True)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        box = self.layout.box()
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")
        box.prop(self, "uv_pref")
        box.prop(self, "colour_pref")
        box.prop(self, "select_pref")

    def execute(self, context):
        # Ensure there's at least one object
        if bpy.data.objects:
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

        ctm_context = ctmNewContext(CTM_IMPORT)
        try:
            ctmLoad(ctm_context, _encode(self.filepath))
            err = ctmGetError(ctm_context)
            if err != CTM_NONE:
                raise IOError("Error loading file: %s" % str(ctmErrorString(err)))

            mesh = bpy.data.meshes.new(name="ImportedMesh")

            # read vertices
            vertex_count = ctmGetInteger(ctm_context, CTM_VERTEX_COUNT)
            vertex_ctm = ctmGetFloatArray(ctm_context, CTM_VERTICES)

            vertices = np.fromiter(vertex_ctm,
                                   dtype=float,
                                   count=vertex_count * 3).reshape((-1, 3))

            # read faces
            face_count = ctmGetInteger(ctm_context, CTM_TRIANGLE_COUNT)
            face_ctm = ctmGetIntegerArray(ctm_context, CTM_INDICES)
            faces = np.fromiter(face_ctm, dtype=int,
                                count=face_count * 3).reshape((-1, 3))

            mesh.from_pydata(vertices=vertices, edges=[], faces=faces)

            transform_matrix = axis_conversion(
                from_forward=self.axis_forward,
                from_up=self.axis_up,
            ).to_4x4()

            if self.uv_pref:
                if ctmGetInteger(ctm_context, CTM_UV_MAP_COUNT) > 0:
                    for map_index in range(8):
                        uv_coords = ctmGetFloatArray(ctm_context, (0x0700 + map_index))
                        if uv_coords:
                            uv_name = ctmGetUVMapString(ctm_context, (0x0700 + map_index), CTM_NAME)
                            uv_coords = np.fromiter(uv_coords, dtype=float, count=vertex_count * 2).reshape((-1, 2))
                            uv_name = uv_name.decode("utf-8") + f"{map_index}"
                            uv_layer = mesh.uv_layers.new(name=f"UV{uv_name}")

                            for poly in mesh.polygons:
                                for loop_index in poly.loop_indices:
                                    vertex_index = mesh.loops[loop_index].vertex_index
                                    uv = uv_coords[vertex_index]
                                    uv_layer.data[loop_index].uv = (uv[0], uv[1])

            if self.colour_pref:
                colour_map = ctmGetNamedAttribMap(ctm_context, c_char_p(_encode('Color')))
                if colour_map != CTM_FALSE:
                    color_3_layer = mesh.vertex_colors.new(name=f"RGBA")
                    colours = ctmGetFloatArray(ctm_context, colour_map)
                    colours = np.fromiter(colours, count=vertex_count * 4, dtype=float).reshape((-1, 4))

                    for poly in mesh.polygons:
                        for loop_index in poly.loop_indices:
                            vertex_index = mesh.loops[loop_index].vertex_index
                            color = colours[vertex_index]
                            color_3_layer.data[loop_index].color = (color[0], color[1], color[2], color[3])

                    mesh.vertex_colors.active = color_3_layer
            mesh.update()


            mesh_obj = bpy.data.objects.new(name="ImportedObject", object_data=mesh)
            mesh_obj.data.transform(transform_matrix)
            bpy.context.scene.collection.objects.link(mesh_obj)

            if self.select_pref:
                mesh_obj.select_set(True)

        finally:
            ctmFreeContext(ctm_context)

        self.report({'INFO'}, "Imported: " + self.filepath)
        return {'FINISHED'}

class OpenCTMExport(bpy.types.Operator, ImportHelper):
    """Export to OpenCTM Format"""
    bl_idname = "export_scene.openctm"
    bl_label = "Export OpenCTM"

    filename_ext = ".ctm"

    filter_glob = bpy.props.StringProperty(default="*.ctm", options={'HIDDEN'})

    uv_pref = BoolProperty(name="UV", description="Export UV", default=True)
    normal_pref = BoolProperty(name="UV", description="Export Normals", default=True)
    colour_pref = BoolProperty(name="Color", description="Export Vertex colors", default=True)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        box = self.layout.box()
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")
        box.prop(self, "uv_pref")
        box.prop(self, "colour_pref")

    def execute(self, context):
        filepath = self.filepath
        print(f"Exporting to {filepath}")
        print(f"UV Preference: {self.uv_pref}")
        print(f"Color Preference: {self.colour_pref}")
        # Add your export code here
        self.report({'INFO'}, "Exported: " + self.filepath)
        return {'FINISHED'}

def _encode(_filename):
    try:
        return str(_filename).encode("utf-8")
    except UnicodeEncodeError:
        pass