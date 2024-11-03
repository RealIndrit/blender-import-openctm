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
            mesh_obj = bpy.data.objects.new(name="ImportedObject", object_data=mesh)

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

            # Validate mesh
            mesh.validate()

            bm = bmesh.new()
            bm.from_mesh(mesh)

            # Ensure the BMesh is valid
            bm.normal_update()

            if ctmGetInteger(ctm_context, CTM_HAS_NORMALS) == CTM_TRUE:
                print("NORMALS")

                normal_ctm = ctmGetFloatArray(ctm_context, CTM_NORMALS)
                normals = np.fromiter(normal_ctm, dtype=float,
                                    count=vertex_count * 3).reshape((-1, 3))

                print(normals, len(normals))


            bm.faces.ensure_lookup_table()
            if ctmGetInteger(ctm_context, CTM_UV_MAP_COUNT) > 0:
                print("UV MAP")
                uv_layer = bm.loops.layers.uv.new()
                uv_coords = ctmGetFloatArray(ctm_context, CTM_UV_MAP_1)
                uvs = np.fromiter(uv_coords, count=face_count, dtype=float).reshape((-1, 2))
                print(uvs, len(uvs))

            # # Get colour map
            colour_map = ctmGetNamedAttribMap(ctm_context, c_char_p(_encode('Color')))
            if colour_map != CTM_FALSE:
                print("Colours")
                colour_layer = bm.loops.layers.color.new()
                colours = ctmGetFloatArray(ctm_context, colour_map)
                colours = np.array(colours).reshape(-1, 4)
                print(colours, len(colours))

            # # Validate mesh
            # mesh.validate()

            bm.to_mesh(mesh)
            bm.free()

            # Update the mesh with new data
            mesh.update()

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