import bpy
from .io_openctm import OpenCTMImport

def menu_import(self, context):
    self.layout.operator(OpenCTMImport.bl_idname, text="OpenCTM (.ctm)")

def register():
    bpy.utils.register_class(OpenCTMImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)

def unregister():
    bpy.utils.unregister_class(OpenCTMImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)