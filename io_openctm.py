import bpy
import bmesh
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

            print(len(mesh.vertices), len(mesh.polygons))

            # Could be cooked, UNTESTED
            if ctmGetInteger(ctm_context, CTM_UV_MAP_COUNT) > 0:
                for map_index in range(8):
                    uv_coords = ctmGetFloatArray(ctm_context, (0x0700 + map_index))
                    if uv_coords:
                        uv_name = ctmGetUVMapString(ctm_context, (0x0700 + map_index), CTM_NAME)
                        uv_name = uv_name.decode("utf-8") + f"{map_index}"
                        uv_layer = mesh.uv_layers.new(name=f"UV{uv_name}")
                        uvs = np.fromiter(uv_coords, count=vertex_count * 2, dtype=float).reshape((-1, 2))

                        for i, loop in enumerate(mesh.loops):
                            uv_layer.data[loop.index].uv = uvs[i % len(uvs)]

            # Get colour map UNTESTED
            # https://github.com/Puxtril/CSV-Import/blob/master/ImportCSV.py#L347
            # colour_map = ctmGetNamedAttribMap(ctm_context, c_char_p(_encode('Color')))
            # if colour_map != CTM_FALSE:
            #     colours = ctmGetFloatArray(ctm_context, colour_map)
            #     colours = np.array(colours, count=vertex_count * 4, dtype=float).reshape((-1, 4))
            #     if colours:
            #         for color_3_index in range(len(colours)):
            #             color_3_layer = mesh.vertex_colors.new(name=f"rgb{color_3_index}")
            #             cur_col_3 = colours[color_3_index]
            #             color_3_layer.data[color_3_index].color = [cur_col_3[0] *255, cur_col_3[1] *255, cur_col_3[2] *255, cur_col_3[3] *255]

            # Update the mesh with new data
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