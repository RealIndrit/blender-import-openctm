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
        ctm_context = ctmNewContext(CTM_IMPORT)
        try:
            ctmLoad(ctm_context, _encode(self.filepath))
            err = ctmGetError(ctm_context)
            if err != CTM_NONE:
                raise IOError("Error loading file: %s" % str(ctmErrorString(err)))

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

            mesh = bpy.data.meshes.new(name="ImportedMesh")
            obj = bpy.data.objects.new(name="ImportedObject", object_data=mesh)

            # Link the object to the collection in the current scene
            bpy.context.collection.objects.link(obj)

            mesh.from_pydata(vertices, [], faces)

            # Update the mesh with new data
            mesh.update()

            # Select the imported object
            obj.select_set(True)

        finally:
            ctmFreeContext(ctm_context)

        self.report({'INFO'}, "Imported: " + self.filepath)
        return {'FINISHED'}

def _encode(_filename):
    try:
        return str(_filename).encode("utf-8")
    except UnicodeEncodeError:
        pass