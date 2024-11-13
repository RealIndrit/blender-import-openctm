import bpy
import numpy as np
from bpy_extras.io_utils import ImportHelper, ExportHelper, axis_conversion, orientation_helper
from .openctm import *
from bpy.props import (
    BoolProperty,
    IntProperty,
    IntVectorProperty,
    StringProperty,
    PointerProperty,
    EnumProperty
)

@orientation_helper(axis_forward="Z", axis_up="Y")
class OpenCTMImport(bpy.types.Operator, ImportHelper):
    """Import from OpenCTM Format"""
    bl_idname = "import_scene.openctm"
    bl_label = "Import OpenCTM"
    filename_ext = ".ctm"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.ctm", options={'HIDDEN'})

    uv_pref: BoolProperty(name="UV", description="Import UV", default=True)
    colour_pref: BoolProperty(name="Color", description="Import vertex colors", default=True)
    select_pref: BoolProperty(name="Select", description="Select imported object after completion",
                                        default=True)

    def draw(self, context):
        box = self.layout.box()
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")

        box = self.layout.box()
        row1 = box.row()
        row1.prop(self, "uv_pref")
        row1.prop(self, "colour_pref")
        row2 = box.row()
        row2.prop(self, "select_pref")

    def execute(self, context):
        self.report({'INFO'}, f"Importing: {self.filepath}...")
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
                            if uv_name:
                                uv_name = uv_name.decode("utf-8") + f"{map_index}"
                            else:
                                uv_name = f"{map_index}"
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

@orientation_helper(axis_forward="Z", axis_up="Y")
class OpenCTMExport(bpy.types.Operator, ImportHelper):
    """Export to OpenCTM Format"""
    bl_idname = "export_scene.openctm"
    bl_label = "Export OpenCTM"

    filename_ext = ".ctm"
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.ctm", options={'HIDDEN'})

    uv_pref: BoolProperty(name="UV", description="Export UV", default=True)
    normal_pref: BoolProperty(name="Normal", description="Export Normals", default=True)
    colour_pref: BoolProperty(name="Color", description="Export Vertex colors", default=True)
    compression_pref: EnumProperty(
        name="Algorithm",
        description="What type of compression algorithm the file use",
        items=[("MG1", "MG1", "MG1 Compression"),
               ("MG2", "MG2", "MG2 Compression"),
               ("RAW", "Uncompressed", "No Compression (Raw)"),],
        default="MG1"
    )

    export_vprec: bpy.props.FloatProperty(
        name="Vertex Precision",
        description="Relative vertex precision (fixed point)",
        default=0.01,
        min=0.0001,
        max=1.0
    )
    export_nprec: bpy.props.FloatProperty(
        name="Normal Precision",
        description="Normal precision (fixed point)",
        default=1.0 / 256.0,
        min=0.0001,
        max=1.0
    )
    export_uvprec: bpy.props.FloatProperty(
        name="UV Precision",
        description="UV precision (fixed point)",
        default=1.0 / 1024.0,
        min=0.0001,
        max=1.0
    )
    export_cprec: bpy.props.FloatProperty(
        name="Color Precision",
        description="Color precision (fixed point)",
        default=1.0 / 256.0,
        min=0.0001,
        max=1.0
    )

    def draw(self, context):
        box = self.layout.box()
        box.prop(self, "axis_forward")
        box.prop(self, "axis_up")

        box = self.layout.box()
        row1 = box.row()
        row1.prop(self, "uv_pref")
        row1.prop(self, "colour_pref")
        row2 = box.row()
        row2.prop(self, "normal_pref")

        box = self.layout.box()
        box.prop(self, "compression_pref")

        if self.compression_pref == "MG2":
            box.prop(self, "export_vprec")
            box.prop(self, "export_nprec")
            box.prop(self, "export_uvprec")
            box.prop(self, "export_cprec")


    def execute(self, context):
        self.report({'INFO'}, f"Exporting: {self.filepath}...")
        transform_matrix = axis_conversion(
            from_forward=self.axis_forward,
            from_up=self.axis_up,
        ).to_4x4()

        active_object = bpy.context.active_object

        if active_object is not None:
            if len(bpy.context.selected_objects) == 1:
                active_object.data.transform(transform_matrix)
                if not self.filepath.lower().endswith('.ctm'):
                    self.filepath += '.ctm'


                mesh = active_object.data

                triangle_count = sum(2 if len(f.vertices) == 4 else 1 for f in mesh.polygons)
                p_indices = cast((c_uint * (3 * triangle_count))(), POINTER(c_uint))

                index = 0
                for f in mesh.polygons:
                    p_indices[index] = ctypes.c_uint(f.vertices[0])
                    p_indices[index + 1] = ctypes.c_uint(f.vertices[1])
                    p_indices[index + 2] = ctypes.c_uint(f.vertices[2])
                    index += 3

                    if len(f.vertices) == 4:
                        p_indices[index] = ctypes.c_uint(f.vertices[0])
                        p_indices[index + 1] = ctypes.c_uint(f.vertices[2])
                        p_indices[index + 2] = ctypes.c_uint(f.vertices[3])
                        index += 3

                # Extract vertex array from the Blender mesh
                vertex_count = len(mesh.vertices)
                p_vertices = cast((c_float * (3 * vertex_count))(), POINTER(c_float))

                for i, v in enumerate(mesh.vertices):
                    p_vertices[3 * i] = ctypes.c_float(v.co.x)
                    p_vertices[3 * i + 1] = ctypes.c_float(v.co.y)
                    p_vertices[3 * i + 2] = ctypes.c_float(v.co.z)

                # Extract normals
                if self.normal_pref:
                    p_normals = (ctypes.c_float * (3 * vertex_count))()
                    for i, v in enumerate(mesh.vertices):
                        p_normals[3 * i] = ctypes.c_float(v.normal.x)
                        p_normals[3 * i + 1] = ctypes.c_float(v.normal.y)
                        p_normals[3 * i + 2] = ctypes.c_float(v.normal.z)
                else:
                    p_normals = ctypes.POINTER(ctypes.c_float)()

                # Extract UVs
                if self.uv_pref:
                    p_UV_coords = (ctypes.c_float * (2 * vertex_count))()

                    if hasattr(mesh, "uv_layers") and mesh.uv_layers:
                        uv_layer = mesh.uv_layers.active.data

                        for f in mesh.polygons:
                            for j, loop_index in enumerate(f.loop_indices):
                                k = mesh.loops[loop_index].vertex_index
                                if k < vertex_count:
                                    uv = uv_layer[loop_index].uv
                                    p_UV_coords[k * 2] = ctypes.c_float(uv[0])
                                    p_UV_coords[k * 2 + 1] = ctypes.c_float(uv[1])

                    else:
                        i = 0
                        for v in mesh.vertices:
                            if hasattr(v, "uvco"):
                                p_UV_coords[i] = ctypes.c_float(v.uvco[0])
                                p_UV_coords[i + 1] = ctypes.c_float(v.uvco[1])
                                i += 2
                else:
                    p_UV_coords = POINTER(c_float)()
                
                # Extract colors
                if self.colour_pref:
                    p_colors = cast((c_float * 4 * vertex_count)(), POINTER(c_float))
                    if mesh.vertex_colors:
                        color_layer = mesh.vertex_colors.active.data
                        for f in mesh.polygons:
                            for j, loop_index in enumerate(f.loop_indices):
                                k = mesh.loops[loop_index].vertex_index
                                if k < vertex_count:
                                    col = color_layer[loop_index]
                                    p_colors[k * 4] = col.color[0]
                                    p_colors[k * 4 + 1] = col.color[1]
                                    p_colors[k * 4 + 2] = col.color[2]
                                    p_colors[k * 4 + 3] = 1.0
                else:
                    p_colors = POINTER(c_float)()
                try:
                    # Create an OpenCTM context
                    ctm = ctmNewContext(CTM_EXPORT)

                    # Set the file comment
                    ctmFileComment(ctm, c_char_p(_encode('Created by OpenCTM Addon (https://github.com/RealIndrit/blender-openctm) for Blender (https://www.blender.org/)')))

                    # Define the mesh
                    ctmDefineMesh(ctm, p_vertices, c_uint(vertex_count), p_indices, c_uint(triangle_count), p_normals)

                    # Add UV coordinates?
                    if self.uv_pref:
                        tm = ctmAddUVMap(ctm, p_UV_coords, c_char_p(), c_char_p())
                        if self.compression_pref == "MG2":
                            ctmUVCoordPrecision(ctm, tm, self.export_uvprec)

                    # Add colors?
                    if self.normal_pref:
                        cm = ctmAddAttribMap(ctm, p_colors, c_char_p(_encode('Color')))
                        if self.compression_pref == "MG2":
                            ctmAttribPrecision(ctm, cm, self.export_cprec)

                    # Set compression method
                    if self.compression_pref == "MG2":
                        ctmVertexPrecisionRel(ctm, self.export_vprec)
                        if self.normal_pref:
                            ctmNormalPrecision(ctm, self.export_nprec)


                    if self.compression_pref == "MG2":
                        ctmCompressionMethod(ctm, CTM_METHOD_MG2)
                    elif self.compression_pref == "MG1":
                        ctmCompressionMethod(ctm, CTM_METHOD_MG1)
                    elif self.compression_pref == "RAW":
                        ctmCompressionMethod(ctm, CTM_METHOD_RAW)

                    # Save the file
                    ctmSave(ctm, c_char_p(_encode(self.filepath)))

                    # Check for errors
                    e = ctmGetError(ctm)
                    if e != 0:
                        s = ctmErrorString(e)
                        self.report({'ERROR'}, f"Could not save the file: {s}")

                finally:
                    # Free the OpenCTM context
                    ctmFreeContext(ctm)

                self.report({'INFO'}, f"Exported: {self.filepath}")
                return {'FINISHED'}
            elif len(bpy.context.selected_objects) > 1:
                self.report({'ERROR'}, "Multiple objects selected, only one object per export allowed")
                return {'CANCELLED'}
            elif len(bpy.context.selected_objects) < 1:
                self.report({'ERROR'}, "No object selected")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, f"No object selected")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(OpenCTMImport)
    bpy.utils.register_class(OpenCTMExport)

def unregister():
    bpy.utils.unregister_class(OpenCTMExport)
    bpy.utils.unregister_class(OpenCTMImport)

def _encode(_filename):
    try:
        return str(_filename).encode("utf-8")
    except UnicodeEncodeError:
        pass