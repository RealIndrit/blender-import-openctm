import bpy
from .io_openctm import OpenCTMImport, OpenCTMExport

def menu_import(self, context):
    self.layout.operator(OpenCTMImport.bl_idname, text="OpenCTM (.ctm)")

def menu_export(self, context):
    self.layout.operator(OpenCTMExport.bl_idname, text="OpenCTM (.ctm)")

def register():
    bpy.utils.register_class(OpenCTMImport)
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.utils.register_class(OpenCTMExport)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)

def unregister():
    bpy.utils.unregister_class(OpenCTMImport)
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.utils.unregister_class(OpenCTMExport)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)

if __name__ == "__main__":
    register()