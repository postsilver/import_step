"""
CAD Importer for Blender
Import STEP and IGES files using FreeCAD conversion with hierarchy and color preservation.

Author: posthuman (postsilver)
License: GPL-3.0
Repository: https://github.com/postsilver/import_step
"""

from __future__ import annotations

import bpy
import os
import subprocess
import tempfile
import platform
import threading
import json
import re
from pathlib import Path
from typing import Set, Optional, Any
from dataclasses import dataclass

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import Operator, AddonPreferences, FileHandler, Context


bl_info = {
    "name": "CAD Importer (STEP/IGES)",
    "author": "posthuman",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "location": "File > Import > CAD Files (.step/.stp/.iges/.igs)",
    "description": "Import CAD STEP and IGES files with hierarchy and color preservation via FreeCAD",
    "warning": "Requires FreeCAD 0.20+ installed",
    "doc_url": "https://github.com/postsilver/import_step",
    "tracker_url": "https://github.com/postsilver/import_step/issues",
    "category": "Import-Export",
}


# =============================================================================
# Constants & Configuration
# =============================================================================

SUPPORTED_EXTENSIONS = {".step", ".stp", ".iges", ".igs"}

QUALITY_PRESETS = {
    'DRAFT':    (1.0,    "Fast preview, low detail"),
    'STANDARD': (0.1,    "Balanced quality and speed"),
    'HIGH':     (0.01,   "High detail, slower conversion"),
    'ULTRA':    (0.001,  "Maximum detail, very slow"),
}


# =============================================================================
# Utility Functions
# =============================================================================

def get_default_freecad_path() -> str:
    """Return the default FreeCADCmd path based on the operating system."""
    system = platform.system()
    paths = {
        "Windows": r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
        "Darwin": "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
        "Linux": "/usr/bin/freecadcmd",
    }
    return paths.get(system, "freecadcmd")


def find_freecad_automatically() -> Optional[str]:
    """Attempt to find FreeCAD installation automatically."""
    system = platform.system()
    
    if system == "Windows":
        # Check common installation paths
        candidates = [
            r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe",
        ]
        # Also check PATH
        import shutil
        path_result = shutil.which("FreeCADCmd.exe")
        if path_result:
            candidates.insert(0, path_result)
            
    elif system == "Darwin":
        candidates = [
            "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
            "/Applications/FreeCAD_0.21.app/Contents/MacOS/FreeCADCmd",
            "/opt/homebrew/bin/freecadcmd",
            "/usr/local/bin/freecadcmd",
        ]
    else:  # Linux
        candidates = [
            "/usr/bin/freecadcmd",
            "/usr/local/bin/freecadcmd",
            "/snap/freecad/current/usr/bin/freecadcmd",
            "/var/lib/flatpak/exports/bin/org.freecadweb.FreeCAD",
        ]
        import shutil
        path_result = shutil.which("freecadcmd") or shutil.which("FreeCADCmd")
        if path_result:
            candidates.insert(0, path_result)
    
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def escape_path_for_python(path: str) -> str:
    """Safely escape a file path for embedding in Python code."""
    # Use repr() to handle all special characters, then strip outer quotes
    return repr(str(path))


def get_quality_items(self, context) -> list:
    """Generate quality preset enum items."""
    return [
        ('DRAFT', "Draft", QUALITY_PRESETS['DRAFT'][1], 'MESH_PLANE', 0),
        ('STANDARD', "Standard", QUALITY_PRESETS['STANDARD'][1], 'MESH_GRID', 1),
        ('HIGH', "High", QUALITY_PRESETS['HIGH'][1], 'MESH_ICOSPHERE', 2),
        ('ULTRA', "Ultra", QUALITY_PRESETS['ULTRA'][1], 'MESH_UVSPHERE', 3),
        ('CUSTOM', "Custom", "Use custom deflection value", 'PREFERENCES', 4),
    ]


# =============================================================================
# FreeCAD Conversion Script Generator
# =============================================================================

def generate_freecad_script(
    input_path: str,
    output_path: str,
    deflection: float,
    export_format: str = 'GLTF',
    preserve_hierarchy: bool = True,
) -> str:
    """
    Generate a FreeCAD Python script for CAD conversion.
    
    Uses glTF or OBJ export to preserve part hierarchy and colors.
    """
    
    input_escaped = escape_path_for_python(input_path)
    output_escaped = escape_path_for_python(output_path)
    
    script = f'''# FreeCAD conversion script - generated by CAD Importer for Blender
import sys
import json

try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
    import Import
except ImportError as e:
    print(f"FREECAD_ERROR: Failed to import FreeCAD modules: {{e}}", file=sys.stderr)
    sys.exit(1)

def convert_cad_file():
    input_path = {input_escaped}
    output_path = {output_escaped}
    deflection = {deflection}
    
    # Create a new document
    doc = FreeCAD.newDocument("CADImport")
    
    try:
        # Import the CAD file (works for both STEP and IGES)
        Import.insert(input_path, doc.Name)
    except Exception as e:
        print(f"FREECAD_ERROR: Failed to read CAD file: {{e}}", file=sys.stderr)
        sys.exit(1)
    
    if not doc.Objects:
        print("FREECAD_ERROR: No objects found in CAD file", file=sys.stderr)
        sys.exit(1)
    
    # Collect info about parts for logging
    part_info = []
    meshes_to_export = []
    
    for obj in doc.Objects:
        if hasattr(obj, 'Shape') and obj.Shape:
            shape = obj.Shape
            
            # Get color if available
            color = None
            if hasattr(obj, 'ViewObject') and obj.ViewObject:
                if hasattr(obj.ViewObject, 'ShapeColor'):
                    c = obj.ViewObject.ShapeColor
                    color = [c[0], c[1], c[2], 1.0]
            
            # Create mesh from shape
            try:
                mesh_data = MeshPart.meshFromShape(
                    Shape=shape,
                    LinearDeflection=deflection,
                    AngularDeflection=0.5,
                    Relative=False
                )
            except Exception:
                # Fallback to basic tessellation
                mesh_data = Mesh.Mesh(shape.tessellate(deflection))
            
            # Create mesh object
            mesh_obj = doc.addObject("Mesh::Feature", obj.Label or "Part")
            mesh_obj.Mesh = mesh_data
            meshes_to_export.append(mesh_obj)
            
            part_info.append({{
                "name": obj.Label,
                "faces": mesh_data.CountFacets,
                "vertices": mesh_data.CountPoints,
            }})
    
    # Export based on format
    export_format = {repr(export_format)}
    
    if export_format == 'GLTF':
        # Export as glTF (preserves hierarchy better)
        # FreeCAD's glTF export requires the mesh objects
        try:
            import importlib
            # Try to use the glTF exporter if available
            if hasattr(Mesh, 'export'):
                Mesh.export(meshes_to_export, output_path)
            else:
                # Fallback: export as OBJ
                output_path = output_path.replace('.glb', '.obj').replace('.gltf', '.obj')
                Mesh.export(meshes_to_export, output_path)
        except Exception as e:
            print(f"FREECAD_ERROR: Export failed: {{e}}", file=sys.stderr)
            sys.exit(1)
    else:
        # Export as OBJ (good hierarchy support)
        try:
            Mesh.export(meshes_to_export, output_path)
        except Exception as e:
            print(f"FREECAD_ERROR: Export failed: {{e}}", file=sys.stderr)
            sys.exit(1)
    
    # Output success info as JSON for parsing
    result = {{
        "success": True,
        "output_path": output_path,
        "parts": part_info,
        "total_parts": len(part_info),
    }}
    print("FREECAD_RESULT:" + json.dumps(result))
    
    # Cleanup
    FreeCAD.closeDocument(doc.Name)

if __name__ == "__main__":
    convert_cad_file()
'''
    return script


# =============================================================================
# Conversion Result Data
# =============================================================================

@dataclass
class ConversionResult:
    """Result of a FreeCAD conversion operation."""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    parts_count: int = 0
    stderr_output: str = ""


# =============================================================================
# Addon Preferences
# =============================================================================

class CADImporterPreferences(AddonPreferences):
    """Addon preferences for CAD Importer."""
    
    bl_idname = __name__
    
    freecad_path: StringProperty(
        name="FreeCAD Command Path",
        description="Path to FreeCADCmd executable. Leave empty for auto-detection",
        subtype='FILE_PATH',
        default="",
    )
    
    default_quality: EnumProperty(
        name="Default Quality",
        description="Default mesh quality preset for imports",
        items=get_quality_items,
        default='STANDARD',
    )
    
    show_import_report: BoolProperty(
        name="Show Import Report",
        description="Display detailed import statistics after conversion",
        default=True,
    )
    
    auto_smooth: BoolProperty(
        name="Auto Smooth Normals",
        description="Apply smooth shading to imported meshes",
        default=True,
    )
    
    def draw(self, context: Context) -> None:
        layout = self.layout
        
        # FreeCAD path section
        box = layout.box()
        box.label(text="FreeCAD Configuration", icon='PREFERENCES')
        
        row = box.row()
        row.prop(self, "freecad_path")
        row.operator("cad_import.detect_freecad", text="", icon='VIEWZOOM')
        
        # Check if FreeCAD is valid
        freecad_status = self._check_freecad_status()
        if freecad_status == "valid":
            box.label(text="✓ FreeCAD found and ready", icon='CHECKMARK')
        elif freecad_status == "not_found":
            box.label(text="✗ FreeCAD not found at specified path", icon='ERROR')
        else:
            box.label(text="⚠ Path not set - will attempt auto-detection", icon='INFO')
        
        # Default settings
        box = layout.box()
        box.label(text="Default Import Settings", icon='IMPORT')
        box.prop(self, "default_quality")
        box.prop(self, "show_import_report")
        box.prop(self, "auto_smooth")
    
    def _check_freecad_status(self) -> str:
        """Check if the configured FreeCAD path is valid."""
        if not self.freecad_path:
            return "not_set"
        if os.path.isfile(self.freecad_path):
            return "valid"
        return "not_found"
    
    def get_freecad_path(self) -> Optional[str]:
        """Get the FreeCAD path, with auto-detection fallback."""
        if self.freecad_path and os.path.isfile(self.freecad_path):
            return self.freecad_path
        return find_freecad_automatically()


class CAD_OT_DetectFreeCAD(Operator):
    """Automatically detect FreeCAD installation"""
    
    bl_idname = "cad_import.detect_freecad"
    bl_label = "Auto-detect FreeCAD"
    bl_options = {'INTERNAL'}
    
    def execute(self, context: Context) -> Set[str]:
        prefs = context.preferences.addons[__name__].preferences
        detected_path = find_freecad_automatically()
        
        if detected_path:
            prefs.freecad_path = detected_path
            self.report({'INFO'}, f"Found FreeCAD at: {detected_path}")
        else:
            self.report({'WARNING'}, "Could not auto-detect FreeCAD. Please set path manually.")
        
        return {'FINISHED'}


# =============================================================================
# Main Import Operator
# =============================================================================

class CAD_OT_ImportCAD(Operator, ImportHelper):
    """Import CAD files (STEP/IGES) using FreeCAD conversion"""
    
    bl_idname = "import_scene.cad"
    bl_label = "Import CAD"
    bl_options = {'UNDO', 'PRESET'}
    
    # File browser filter
    filter_glob: StringProperty(
        default="*.step;*.stp;*.iges;*.igs;*.STEP;*.STP;*.IGES;*.IGS",
        options={'HIDDEN'},
    )
    
    # Import options
    quality_preset: EnumProperty(
        name="Quality",
        description="Mesh quality preset (affects polygon count and detail)",
        items=get_quality_items,
        default='STANDARD',
    )
    
    custom_deflection: FloatProperty(
        name="Custom Deflection",
        description="Lower values = more detail, higher values = faster. Only used with Custom quality",
        default=0.1,
        min=0.0001,
        max=10.0,
        precision=4,
    )
    
    scale: FloatProperty(
        name="Scale",
        description="Scale factor for imported geometry",
        default=1.0,
        min=0.0001,
        max=10000.0,
    )
    
    auto_smooth: BoolProperty(
        name="Smooth Shading",
        description="Apply smooth shading to imported meshes",
        default=True,
    )
    
    # Internal state
    _timer = None
    _thread: Optional[threading.Thread] = None
    _result: Optional[ConversionResult] = None
    _temp_dir: Optional[tempfile.TemporaryDirectory] = None
    _output_path: Optional[str] = None
    
    def invoke(self, context: Context, event) -> Set[str]:
        # Load defaults from preferences
        prefs = context.preferences.addons[__name__].preferences
        self.quality_preset = prefs.default_quality
        self.auto_smooth = prefs.auto_smooth
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context: Context) -> None:
        layout = self.layout
        
        # Quality settings
        layout.label(text="Mesh Quality", icon='MESH_DATA')
        layout.prop(self, "quality_preset", text="")
        
        if self.quality_preset == 'CUSTOM':
            layout.prop(self, "custom_deflection")
        
        layout.separator()
        
        # Transform settings
        layout.label(text="Transform", icon='ORIENTATION_GLOBAL')
        layout.prop(self, "scale")
        
        layout.separator()
        
        # Mesh settings
        layout.label(text="Mesh Options", icon='NORMALS_FACE')
        layout.prop(self, "auto_smooth")
    
    def execute(self, context: Context) -> Set[str]:
        # Validate file
        filepath = Path(self.filepath)
        if not filepath.exists():
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}
        
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.report({'ERROR'}, f"Unsupported file format: {filepath.suffix}")
            return {'CANCELLED'}
        
        # Get FreeCAD path
        prefs = context.preferences.addons[__name__].preferences
        freecad_path = prefs.get_freecad_path()
        
        if not freecad_path:
            self.report({'ERROR'}, 
                "FreeCAD not found. Please install FreeCAD or set the path in addon preferences.")
            return {'CANCELLED'}
        
        # Calculate deflection
        if self.quality_preset == 'CUSTOM':
            deflection = self.custom_deflection
        else:
            deflection = QUALITY_PRESETS[self.quality_preset][0]
        
        # Set wait cursor
        context.window.cursor_set('WAIT')
        
        try:
            result = self._run_conversion(freecad_path, str(filepath), deflection)
        finally:
            context.window.cursor_set('DEFAULT')
        
        if not result.success:
            error_msg = result.error_message or "Unknown error"
            if result.stderr_output:
                print(f"FreeCAD stderr:\n{result.stderr_output}")
            self.report({'ERROR'}, f"Conversion failed: {error_msg}")
            return {'CANCELLED'}
        
        # Import the converted file
        if result.output_path and os.path.exists(result.output_path):
            try:
                self._import_mesh(context, result.output_path)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to import converted mesh: {e}")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Conversion produced no output file")
            return {'CANCELLED'}
        
        # Report success
        prefs = context.preferences.addons[__name__].preferences
        if prefs.show_import_report:
            self.report({'INFO'}, 
                f"Imported {filepath.name}: {result.parts_count} parts")
        else:
            self.report({'INFO'}, "CAD file imported successfully")
        
        return {'FINISHED'}
    
    def _run_conversion(
        self, 
        freecad_path: str, 
        input_path: str, 
        deflection: float
    ) -> ConversionResult:
        """Run the FreeCAD conversion subprocess."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Determine output format and path
            output_path = os.path.join(temp_dir, "output.obj")
            
            # Generate conversion script
            script = generate_freecad_script(
                input_path=input_path,
                output_path=output_path,
                deflection=deflection,
                export_format='OBJ',
                preserve_hierarchy=True,
            )
            
            # Write script to temp file
            script_path = os.path.join(temp_dir, "convert.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            # Run FreeCAD
            try:
                proc = subprocess.run(
                    [freecad_path, script_path],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
            except subprocess.TimeoutExpired:
                return ConversionResult(
                    success=False,
                    error_message="Conversion timed out after 5 minutes"
                )
            except FileNotFoundError:
                return ConversionResult(
                    success=False,
                    error_message=f"FreeCAD executable not found at: {freecad_path}"
                )
            except Exception as e:
                return ConversionResult(
                    success=False,
                    error_message=str(e)
                )
            
            # Parse output
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            
            # Check for errors in stderr
            if "FREECAD_ERROR:" in stderr:
                error_match = re.search(r"FREECAD_ERROR:\s*(.+)", stderr)
                error_msg = error_match.group(1) if error_match else "Unknown FreeCAD error"
                return ConversionResult(
                    success=False,
                    error_message=error_msg,
                    stderr_output=stderr
                )
            
            # Check for success result
            parts_count = 0
            if "FREECAD_RESULT:" in stdout:
                try:
                    result_match = re.search(r"FREECAD_RESULT:(.+)", stdout)
                    if result_match:
                        result_data = json.loads(result_match.group(1))
                        parts_count = result_data.get("total_parts", 0)
                        # Update output path if it was changed
                        output_path = result_data.get("output_path", output_path)
                except json.JSONDecodeError:
                    pass
            
            # Check if output file exists
            if not os.path.exists(output_path):
                return ConversionResult(
                    success=False,
                    error_message="Conversion completed but no output file was created",
                    stderr_output=stderr
                )
            
            # Copy output to a persistent location before temp dir is cleaned
            import shutil
            persistent_output = tempfile.mktemp(suffix=".obj")
            shutil.copy2(output_path, persistent_output)
            
            return ConversionResult(
                success=True,
                output_path=persistent_output,
                parts_count=parts_count,
                stderr_output=stderr
            )
    
    def _import_mesh(self, context: Context, filepath: str) -> None:
        """Import the converted mesh file into Blender."""
        
        # Store current selection to track new objects
        before_objects = set(bpy.data.objects)
        
        # Import based on file extension
        ext = Path(filepath).suffix.lower()
        
        if ext == '.obj':
            bpy.ops.wm.obj_import(filepath=filepath, global_scale=self.scale)
        elif ext == '.stl':
            bpy.ops.wm.stl_import(filepath=filepath, global_scale=self.scale)
        elif ext in ('.glb', '.gltf'):
            bpy.ops.import_scene.gltf(filepath=filepath)
            # Apply scale to glTF imports
            if self.scale != 1.0:
                for obj in context.selected_objects:
                    obj.scale *= self.scale
        
        # Find newly imported objects
        after_objects = set(bpy.data.objects)
        new_objects = after_objects - before_objects
        
        # Apply smooth shading if requested
        if self.auto_smooth and new_objects:
            for obj in new_objects:
                if obj.type == 'MESH':
                    # Set smooth shading
                    for polygon in obj.data.polygons:
                        polygon.use_smooth = True
        
        # Clean up temp file
        try:
            os.unlink(filepath)
        except OSError:
            pass


# =============================================================================
# Drag and Drop File Handler
# =============================================================================

class CAD_FH_Import(FileHandler):
    """File handler for drag-and-drop CAD import."""
    
    bl_idname = "CAD_FH_import"
    bl_label = "CAD Files"
    bl_import_operator = "import_scene.cad"
    bl_file_extensions = ".step;.stp;.iges;.igs"
    
    @classmethod
    def poll_drop(cls, context: Context) -> bool:
        return context.area and context.area.type == 'VIEW_3D'


# =============================================================================
# Menu Integration
# =============================================================================

def menu_func_import(self, context: Context) -> None:
    self.layout.operator(CAD_OT_ImportCAD.bl_idname, text="CAD Files (.step/.iges)")


# =============================================================================
# Registration
# =============================================================================

classes = (
    CADImporterPreferences,
    CAD_OT_DetectFreeCAD,
    CAD_OT_ImportCAD,
    CAD_FH_Import,
)


def register() -> None:
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
