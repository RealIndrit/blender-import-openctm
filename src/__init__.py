import bpy
from .io_openctm import OpenCTMImport, OpenCTMExport

bl_info = {
    "name": "OpenCTM (.ctm)",
    "description": "Import/Export meshes from/to OpenCTM (.ctm)",
    "author": "RealIndrit",
    "version": (1, 3, 0),
    "blender": (3, 6, 0),
    "location": "File > Import-Export",
    "warning": "",
    "wiki_url": "https://github.com/RealIndrit/blender-import-openctm",
    "tracker_url": "https://github.com/RealIndrit/blender-import-openctm",
    "category": "Import-Export",
}

def menu_import(self, context):
    self.layout.operator(OpenCTMImport.bl_idname, text="OpenCTM (.ctm)")

def menu_export(self, context):
    self.layout.operator(OpenCTMExport.bl_idname, text="OpenCTM (.ctm)")

def register():
    io_openctm.register()
    bpy.types.TOPBAR_MT_file_import.append(menu_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_export)

def unregister():
    io_openctm.unregister()
    bpy.types.TOPBAR_MT_file_import.remove(menu_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_export)

if __name__ == "__main__":
    register()