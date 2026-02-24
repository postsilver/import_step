"""
CAD Importer for Blender
Import STEP and IGES files using FreeCAD conversion.

Author: posthuman (postsilver)
License: GPL-3.0
Repository: https://github.com/postsilver/import_step
"""

import bpy
import os
import subprocess
import tempfile
import platform
from pathlib import Path

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, FloatProperty, EnumProperty, BoolProperty
from bpy.types import Operator, AddonPreferences, FileHandler


bl_info = {
    "name": "CAD Importer (STEP/IGES)",
    "author": "posthuman",
    "version": (2, 0, 3),
    "blender": (4, 2, 0),
    "location": "File > Import > CAD Files (.step/.stp/.iges/.igs)",
    "description": "Import CAD STEP and IGES files via FreeCAD",
    "warning": "Requires FreeCAD installed",
    "doc_url": "https://github.com/postsilver/import_step",
    "tracker_url": "https://github.com/postsilver/import_step/issues",
    "category": "Import-Export",
}


# =============================================================================
# Constants
# =============================================================================

SUPPORTED_EXTENSIONS = {".step", ".stp", ".iges", ".igs"}

# Quality presets: (deflection_value, description)
QUALITY_PRESETS = {
    'DRAFT':    1.0,
    'STANDARD': 0.1,
    'HIGH':     0.01,
    'ULTRA':    0.001,
}


# =============================================================================
# Utility Functions
# =============================================================================

def find_freecad_automatically():
    """Attempt to find FreeCAD installation automatically."""
    import shutil
    
    system = platform.system()
    
    if system == "Windows":
        candidates = [
            # FreeCAD 1.x (newest)
            r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
            # FreeCAD 0.2x
            r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe",
        ]
        # Check PATH - try multiple variations
        for cmd in ["freecadcmd", "FreeCADCmd", "freecad"]:
            path_result = shutil.which(cmd)
            if path_result:
                candidates.insert(0, path_result)
                break
        # Check AppData for user installs
        appdata = os.environ.get('LOCALAPPDATA', '')
        if appdata:
            candidates.append(os.path.join(appdata, "Programs", "FreeCAD", "bin", "FreeCADCmd.exe"))
            
    elif system == "Darwin":
        candidates = [
            "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
            "/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd",
            "/opt/homebrew/bin/freecadcmd",
            "/usr/local/bin/freecadcmd",
        ]
        for cmd in ["freecadcmd", "FreeCADCmd", "freecad"]:
            path_result = shutil.which(cmd)
            if path_result:
                candidates.insert(0, path_result)
                break
    else:  # Linux
        candidates = [
            "/usr/bin/freecadcmd",
            "/usr/bin/FreeCADCmd",
            "/usr/local/bin/freecadcmd",
            "/snap/freecad/current/usr/bin/freecadcmd",
        ]
        for cmd in ["freecadcmd", "FreeCADCmd", "freecad"]:
            path_result = shutil.which(cmd)
            if path_result:
                candidates.insert(0, path_result)
                break
    
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# =============================================================================
# Addon Preferences
# =============================================================================

class CADImporterPreferences(AddonPreferences):
    bl_idname = __name__
    
    freecad_path: StringProperty(
        name="FreeCAD Path",
        description="Path to FreeCADCmd executable",
        subtype='FILE_PATH',
        default="",
    )
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="FreeCAD Configuration", icon='PREFERENCES')
        
        row = box.row()
        row.prop(self, "freecad_path")
        row.operator("cad_import.detect_freecad", text="", icon='VIEWZOOM')
        
        # Status indicator
        if self.freecad_path and os.path.isfile(self.freecad_path):
            box.label(text="✓ FreeCAD path is valid", icon='CHECKMARK')
        elif self.freecad_path:
            box.label(text="✗ File not found at specified path", icon='ERROR')
        else:
            box.label(text="⚠ Please set FreeCAD path", icon='INFO')
    
    def get_freecad_path(self):
        """Get the FreeCAD path, with auto-detection fallback."""
        if self.freecad_path and os.path.isfile(self.freecad_path):
            return self.freecad_path
        return find_freecad_automatically()


class CAD_OT_DetectFreeCAD(Operator):
    """Automatically detect FreeCAD installation"""
    bl_idname = "cad_import.detect_freecad"
    bl_label = "Auto-detect FreeCAD"
    bl_options = {'INTERNAL'}
    
    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences
        detected = find_freecad_automatically()
        
        if detected:
            prefs.freecad_path = detected
            self.report({'INFO'}, f"Found FreeCAD: {detected}")
        else:
            self.report({'WARNING'}, "Could not auto-detect FreeCAD. Please set path manually.")
        
        return {'FINISHED'}


# =============================================================================
# Main Import Operator
# =============================================================================

class CAD_OT_ImportCAD(Operator, ImportHelper):
    """Import CAD files (STEP/IGES) using FreeCAD"""
    bl_idname = "import_scene.cad"
    bl_label = "Import CAD"
    bl_options = {'UNDO', 'PRESET'}
    
    filter_glob: StringProperty(
        default="*.step;*.stp;*.iges;*.igs;*.STEP;*.STP;*.IGES;*.IGS",
        options={'HIDDEN'},
    )
    
    quality: EnumProperty(
        name="Quality",
        description="Mesh quality (lower = more detail)",
        items=[
            ('DRAFT', "Draft", "Fast preview, low detail (deflection=1.0)"),
            ('STANDARD', "Standard", "Balanced quality (deflection=0.1)"),
            ('HIGH', "High", "High detail (deflection=0.01)"),
            ('ULTRA', "Ultra", "Maximum detail (deflection=0.001)"),
        ],
        default='STANDARD',
    )
    
    scale: FloatProperty(
        name="Scale",
        description="Scale factor for imported geometry",
        default=1.0,
        min=0.0001,
        max=10000.0,
    )
    
    smooth_shading: BoolProperty(
        name="Smooth Shading",
        description="Apply smooth shading to imported meshes",
        default=True,
    )
    
    preserve_hierarchy: BoolProperty(
        name="Preserve Hierarchy",
        description="Preserve CAD assembly hierarchy structure",
        default=True,
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "quality")
        layout.prop(self, "scale")
        layout.prop(self, "smooth_shading")
        layout.prop(self, "preserve_hierarchy")
    
    def execute(self, context):
        # Validate file
        filepath = Path(self.filepath)
        if not filepath.exists():
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}
        
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.report({'ERROR'}, f"Unsupported format: {filepath.suffix}")
            return {'CANCELLED'}
        
        # Get FreeCAD path
        prefs = context.preferences.addons[__name__].preferences
        freecad_path = prefs.get_freecad_path()
        
        if not freecad_path:
            self.report({'ERROR'}, "FreeCAD not found. Set path in addon preferences.")
            return {'CANCELLED'}
        
        # Get deflection from quality preset
        deflection = QUALITY_PRESETS.get(self.quality, 0.1)
        
        # Set wait cursor
        context.window.cursor_set('WAIT')
        
        try:
            success = self._convert_and_import(
                context, 
                freecad_path, 
                str(filepath), 
                deflection
            )
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}
        finally:
            context.window.cursor_set('DEFAULT')
        
        if success:
            self.report({'INFO'}, f"Imported: {filepath.name}")
            return {'FINISHED'}
        else:
            return {'CANCELLED'}
    
    def _convert_and_import(self, context, freecad_path, input_path, deflection):
        """Convert CAD file and import into Blender."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate FreeCAD script with hierarchy preservation
            script_path = os.path.join(temp_dir, "convert.py")
            
            if self.preserve_hierarchy:
                script = self._generate_hierarchy_script(input_path, temp_dir, deflection)
            else:
                script = self._generate_simple_script(input_path, temp_dir, deflection)
            
            # Write script
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            # Run FreeCAD
            print(f"Running FreeCAD: {freecad_path}")
            print(f"Script: {script_path}")
            
            # CRITICAL FIX: Proper command-line invocation for different platforms
            # Try different invocation methods for compatibility
            commands_to_try = []
            
            if platform.system() == "Windows":
                # Windows: Most accept script directly, but some need flags
                commands_to_try = [
                    [freecad_path, script_path],
                    [freecad_path, "-c", script_path],
                ]
            else:
                # Linux/macOS: Pass script directly — do NOT use -c flag.
                # On Linux, freecadcmd -c opens an interactive Python console
                # after script execution, causing subprocess.run to block
                # indefinitely until the timeout is reached.
                commands_to_try = [
                    [freecad_path, script_path],
                ]
            
            result = None
            last_error = None
            
            for cmd in commands_to_try:
                try:
                    print(f"Trying command: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600,  # 10 minutes for large assemblies
                    )
                    
                    # Check if it worked (return code 0 or output contains SUCCESS)
                    if result.returncode == 0 or "SUCCESS" in result.stdout:
                        print(f"Command succeeded!")
                        break
                    else:
                        last_error = f"Command failed with return code {result.returncode}"
                        print(f"Command failed, trying next variant...")
                        
                except subprocess.TimeoutExpired:
                    self.report({'ERROR'}, "FreeCAD conversion timed out (10 min limit)")
                    return False
                except FileNotFoundError:
                    self.report({'ERROR'}, f"FreeCAD not found: {freecad_path}")
                    return False
                except Exception as e:
                    last_error = str(e)
                    continue
            
            if result is None:
                self.report({'ERROR'}, f"All FreeCAD invocation methods failed: {last_error}")
                return False
            
            print(f"FreeCAD stdout:\n{result.stdout}")
            if result.stderr:
                print(f"FreeCAD stderr:\n{result.stderr}")
            print(f"Return code: {result.returncode}")
            
            # Import based on mode
            if self.preserve_hierarchy:
                return self._import_with_hierarchy(temp_dir)
            else:
                return self._import_simple(temp_dir)
    
    def _generate_simple_script(self, input_path, temp_dir, deflection):
        """Generate FreeCAD script for simple import (single mesh)."""
        output_path = os.path.join(temp_dir, "output.stl")
        
        return f'''# FreeCAD conversion script
import sys
print("FreeCAD script starting...")

try:
    import FreeCAD
    import Part
    import Mesh
    import MeshPart
    print("Modules imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import modules: {{e}}")
    sys.exit(1)

input_path = {repr(input_path)}
output_path = {repr(output_path)}
deflection = {deflection}

print(f"Input: {{input_path}}")
print(f"Output: {{output_path}}")
print(f"Deflection: {{deflection}}")

try:
    print("Reading CAD file...")
    shape = Part.read(input_path)
    print(f"Shape loaded: {{shape}}")
    
    print("Tessellating...")
    mesh = Mesh.Mesh(shape.tessellate(deflection))
    print(f"Mesh created: {{mesh.CountFacets}} faces, {{mesh.CountPoints}} vertices")
    
    if mesh.CountFacets == 0:
        print("ERROR: Tessellation produced empty mesh")
        sys.exit(1)
    
    print("Exporting to STL...")
    mesh.write(output_path)
    print("Export complete!")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("SUCCESS")
'''
    
    def _generate_hierarchy_script(self, input_path, temp_dir, deflection):
        """Generate FreeCAD script for hierarchical import."""
        
        return f'''# FreeCAD hierarchical conversion script
import sys
import os
import json
print("FreeCAD hierarchical script starting...")

try:
    import FreeCAD
    import Part
    import Mesh
    import Import
    print("Modules imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import modules: {{e}}")
    sys.exit(1)

input_path = {repr(input_path)}
output_dir = {repr(temp_dir)}
deflection = {deflection}

print(f"Input: {{input_path}}")
print(f"Output directory: {{output_dir}}")
print(f"Deflection: {{deflection}}")

def sanitize_name(name):
    """Sanitize object name for file system."""
    import re
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip()
    return name if name else "unnamed"

def process_object(obj, parent_path="", hierarchy=None, obj_counter=None, name_counts=None):
    """Recursively process objects and build hierarchy."""
    if hierarchy is None:
        hierarchy = []
    if obj_counter is None:
        obj_counter = {{'count': 0}}
    if name_counts is None:
        name_counts = {{}}
    
    # Generate unique name
    base_name = sanitize_name(obj.Label if hasattr(obj, 'Label') else f"object_{{obj_counter['count']}}")
    
    # Add numeric suffix if name already used
    if base_name in name_counts:
        name_counts[base_name] += 1
        obj_name = f"{{base_name}}_{{name_counts[base_name]}}"
    else:
        name_counts[base_name] = 0
        obj_name = base_name
    
    obj_id = f"{{parent_path}}/{{obj_name}}" if parent_path else obj_name
    
    print(f"Processing: {{obj_id}}")
    
    node = {{
        'name': obj_name,
        'id': obj_id,
        'type': obj.TypeId if hasattr(obj, 'TypeId') else 'Unknown',
        'children': []
    }}
    
    # Process shape if it exists
    if hasattr(obj, 'Shape') and obj.Shape and not obj.Shape.isNull():
        try:
            obj_counter['count'] += 1
            filename = f"part_{{obj_counter['count']:04d}}_{{obj_name}}.stl"
            filepath = os.path.join(output_dir, filename)
            
            print(f"  Tessellating shape...")
            mesh = Mesh.Mesh(obj.Shape.tessellate(deflection))
            
            if mesh.CountFacets > 0:
                print(f"  Writing {{mesh.CountFacets}} faces to {{filename}}")
                mesh.write(filepath)
                
                # Verify file was written and has size > 0
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    node['mesh_file'] = filename
                    node['has_geometry'] = True
                else:
                    print(f"  Warning: STL file is empty or wasn't created")
                    node['has_geometry'] = False
            else:
                print(f"  Skipping empty mesh")
                node['has_geometry'] = False
        except Exception as e:
            print(f"  Warning: Failed to export shape: {{e}}")
            node['has_geometry'] = False
    else:
        node['has_geometry'] = False
    
    # Process children
    if hasattr(obj, 'OutList'):
        for child in obj.OutList:
            child_node = process_object(child, obj_id, None, obj_counter, name_counts)
            if child_node:
                node['children'].append(child_node)
    
    hierarchy.append(node)
    return node

try:
    print("Opening document...")
    Import.open(input_path)
    doc = FreeCAD.ActiveDocument
    
    if not doc:
        print("ERROR: No active document")
        sys.exit(1)
    
    print(f"Document opened: {{doc.Name}}")
    print(f"Objects in document: {{len(doc.Objects)}}")
    
    # Build hierarchy
    hierarchy = []
    obj_counter = {{'count': 0}}
    name_counts = {{}}
    
    # CRITICAL FIX: Better root object detection
    # Method 1: Find objects with no incoming dependencies
    roots = []
    for obj in doc.Objects:
        # Check if object has no incoming links (is a root)
        if hasattr(obj, "InList") and len(obj.InList) == 0:
            roots.append(obj)
        # Also include known top-level container types
        elif hasattr(obj, "TypeId") and obj.TypeId in {{"App::Part", "PartDesign::Body", "App::Link", "Part::Compound"}}:
            # But only if not already in roots
            if obj not in roots:
                roots.append(obj)
    
    # Fallback: if no roots found, process all objects
    if not roots:
        print("Warning: No clear root objects found, processing all objects")
        roots = doc.Objects
    
    print(f"Processing {{len(roots)}} root objects")
    
    for obj in roots:
        process_object(obj, "", hierarchy, obj_counter, name_counts)
    
    # Save hierarchy to JSON
    hierarchy_path = os.path.join(output_dir, "hierarchy.json")
    with open(hierarchy_path, 'w') as f:
        json.dump(hierarchy, f, indent=2)
    
    print(f"Hierarchy saved: {{hierarchy_path}}")
    print(f"Total parts exported: {{obj_counter['count']}}")
    
    FreeCAD.closeDocument(doc.Name)
    
except Exception as e:
    print(f"ERROR: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("SUCCESS")
'''
    
    def _import_simple(self, temp_dir):
        """Import single STL file."""
        output_path = os.path.join(temp_dir, "output.stl")
        
        if not os.path.exists(output_path):
            self.report({'ERROR'}, "Conversion failed - no output file created")
            return False
        
        # Check file size
        if os.path.getsize(output_path) == 0:
            self.report({'ERROR'}, "Conversion produced empty file")
            return False
        
        print(f"Importing STL: {output_path}")
        
        # Track new objects
        before = set(bpy.data.objects)
        
        # Import STL
        bpy.ops.wm.stl_import(filepath=output_path, global_scale=self.scale)
        
        # Find new objects
        after = set(bpy.data.objects)
        new_objects = after - before
        
        # Apply smooth shading if requested
        if self.smooth_shading:
            for obj in new_objects:
                if obj.type == 'MESH':
                    # Use mesh.shade_smooth() for Blender 4.1+
                    if hasattr(obj.data, 'shade_smooth'):
                        obj.data.shade_smooth()
                    else:
                        # Fallback for older versions
                        for poly in obj.data.polygons:
                            poly.use_smooth = True
        
        print(f"Imported {len(new_objects)} object(s)")
        return True
    
    def _import_with_hierarchy(self, temp_dir):
        """Import STL files with hierarchy preservation."""
        import json
        
        hierarchy_path = os.path.join(temp_dir, "hierarchy.json")
        
        if not os.path.exists(hierarchy_path):
            self.report({'ERROR'}, "Hierarchy file not created")
            return False
        
        # Load hierarchy
        with open(hierarchy_path, 'r') as f:
            hierarchy = json.load(f)
        
        print(f"Loaded hierarchy with {len(hierarchy)} root objects")
        
        # Create collection for import
        filename = Path(self.filepath).stem
        collection = bpy.data.collections.new(f"CAD_{filename}")
        bpy.context.scene.collection.children.link(collection)
        
        # Track used names to ensure uniqueness
        used_names = set()
        
        # Import hierarchy recursively
        def import_node(node, parent_collection):
            """Recursively import nodes and create hierarchy."""
            node_collection = None
            node_name = node['name']
            
            # Ensure unique name in Blender
            original_name = node_name
            counter = 1
            while node_name in used_names:
                node_name = f"{original_name}_{counter}"
                counter += 1
            used_names.add(node_name)
            
            # Import mesh if exists
            if node.get('has_geometry') and node.get('mesh_file'):
                mesh_path = os.path.join(temp_dir, node['mesh_file'])
                
                if os.path.exists(mesh_path) and os.path.getsize(mesh_path) > 0:
                    # Track existing objects
                    before = set(bpy.data.objects)
                    
                    # Import STL
                    bpy.ops.wm.stl_import(filepath=mesh_path, global_scale=self.scale)
                    
                    # Find new object
                    after = set(bpy.data.objects)
                    new_objects = list(after - before)
                    
                    if new_objects:
                        obj = new_objects[0]
                        obj.name = node_name
                        
                        # Apply smooth shading
                        if self.smooth_shading and obj.type == 'MESH':
                            if hasattr(obj.data, 'shade_smooth'):
                                obj.data.shade_smooth()
                            else:
                                for poly in obj.data.polygons:
                                    poly.use_smooth = True
                        
                        # Link to parent collection
                        # Unlink from all collections first
                        for coll in obj.users_collection:
                            coll.objects.unlink(obj)
                        
                        parent_collection.objects.link(obj)
            
            # Create collection for children if needed
            if node.get('children'):
                node_collection = bpy.data.collections.new(node_name)
                parent_collection.children.link(node_collection)
                
                # Process children
                for child in node['children']:
                    import_node(child, node_collection)
            
            return node_collection
        
        # Import all root nodes
        for root in hierarchy:
            import_node(root, collection)
        
        print(f"Hierarchy import complete")
        return True


# =============================================================================
# Drag and Drop Handler
# =============================================================================

class CAD_FH_Import(FileHandler):
    bl_idname = "CAD_FH_import"
    bl_label = "CAD Files"
    bl_import_operator = "import_scene.cad"
    bl_file_extensions = ".step;.stp;.iges;.igs"
    
    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type == 'VIEW_3D'


# =============================================================================
# Menu
# =============================================================================

def menu_func_import(self, context):
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

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()