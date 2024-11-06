import bpy
import numpy as np
from bpy_extras.io_utils import ImportHelper
from .openctm import *
from bpy.props import StringProperty

class OpenCTMImport(bpy.types.Operator, ImportHelper):
    """Import from OpenCTM Format"""
    bl_idname = "import_scene.openctm"
    bl_label = "Import from OpenCTM Format"

    filename_ext = ".ctm"
    filter_glob: StringProperty(
        default="*.ctm",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, including the null terminator.
    )

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

            mesh.update()


            mesh_obj = bpy.data.objects.new(name="ImportedObject", object_data=mesh)
            bpy.context.scene.collection.objects.link(mesh_obj)
            # Select the imported object
            mesh_obj.select_set(True)

        finally:
            ctmFreeContext(ctm_context)

        self.report({'INFO'}, "Imported: " + self.filepath)
        return {'FINISHED'}

def _encode(_filename):
    try:
        return str(_filename).encode("utf-8")
    except UnicodeEncodeError:
        pass