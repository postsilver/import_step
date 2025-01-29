import bpy
import os
import subprocess
import tempfile
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty
from bpy.types import Operator, AddonPreferences

bl_info = {
    "name": "Import STEP Files",
    "author": "posthuman",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "File > Import",
    "description": "Import CAD STEP files using FreeCAD conversion",
    "warning": "Requires FreeCAD installed",
    "category": "Import-Export",
}

class ImportSTEPPreferences(AddonPreferences):
    bl_idname = __name__

    freecad_path: StringProperty(
        name="FreeCAD Command Path",
        description="Path to FreeCADCmd executable",
        subtype='FILE_PATH',
        default="FreeCADCmd",
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Provide the path to FreeCADCmd:")
        layout.prop(self, "freecad_path")

class ImportSTEP(Operator, ImportHelper):
    bl_idname = "import_scene.step"
    bl_label = "Import STEP"
    bl_options = {'UNDO'}

    filter_glob: StringProperty(
        default="*.step;*.stp",
        options={'HIDDEN'},
    )

    deflection: FloatProperty(
        name="Deflection",
        description="Lower values increase mesh detail",
        default=0.1,
        min=0.01,
        max=10.0,
    )

    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        freecad_cmd = prefs.freecad_path

        step_path = self.filepath
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            stl_path = os.path.join(tmp_dir, "output.stl")

            script = f"""
import FreeCAD
import Part
import Mesh

doc = FreeCAD.newDocument()
shape = Part.read(r"{step_path}")
mesh = doc.addObject("Mesh::Feature", "Mesh")
mesh.Mesh = Mesh.Mesh(shape.tessellate({self.deflection}))
Mesh.export([mesh], r"{stl_path}")
FreeCAD.closeDocument(doc.Name)
"""

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as tmp_script:
                tmp_script.write(script)
                tmp_script_path = tmp_script.name

            try:
                subprocess.run(
                    [freecad_cmd, tmp_script_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError as e:
                self.report({'ERROR'}, f"FreeCAD conversion failed: {e}")
                return {'CANCELLED'}
            except FileNotFoundError:
                self.report({'ERROR'}, "FreeCADCmd not found. Check the path in addon preferences.")
                return {'CANCELLED'}
            finally:
                os.unlink(tmp_script_path)

            if os.path.exists(stl_path):
                bpy.ops.wm.stl_import(
    filepath=stl_path,
    use_facet_normal=True,  # Better mesh normals
    global_scale=1.0
)
                self.report({'INFO'}, "STEP file imported successfully")
            else:
                self.report({'ERROR'}, "STL file not generated")
                return {'CANCELLED'}

        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportSTEP.bl_idname, text="STEP (.step/.stp)")

def register():
    bpy.utils.register_class(ImportSTEPPreferences)
    bpy.utils.register_class(ImportSTEP)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportSTEPPreferences)
    bpy.utils.unregister_class(ImportSTEP)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()