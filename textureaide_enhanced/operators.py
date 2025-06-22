# operators.py - All Operator Classes

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty

from .utils.scaling_utils import apply_texture_scaling, validate_scaling_parameters, get_object_texture_scale_info
from .utils.udim_utils import find_udim_files, select_optimal_udim, get_udim_from_index
from .properties import (
    get_object_live_rescale, set_object_live_rescale, 
    get_object_scaling_mode, get_object_target_udim, set_object_target_udim
)

def get_selected_material_and_node(obj):
    """Get the currently selected material and image node from UI"""
    if not obj or not obj.material_slots:
        return None, None
    
    props = bpy.context.scene.textureaide_props
    
    # Get selected material
    selected_material = None
    if (0 <= props.active_material_index < len(props.material_items) and
        0 <= props.material_items[props.active_material_index].material_index < len(obj.material_slots)):
        selected_material = obj.material_slots[props.material_items[props.active_material_index].material_index].material
    
    if not selected_material or not selected_material.node_tree:
        return selected_material, None
    
    # Get selected image node
    selected_node = None
    if 0 <= props.active_image_node_index < len(props.image_node_items):
        node_item = props.image_node_items[props.active_image_node_index]
        for node in selected_material.node_tree.nodes:
            if node.name == node_item.node_name and node.type == 'TEX_IMAGE':
                selected_node = node
                break
    
    return selected_material, selected_node

class TEXTUREAIDE_OT_texture_scale_match(Operator):
    """Match object dimensions to selected texture dimensions"""
    bl_idname = "textureaide.texture_scale_match"
    bl_label = "Texture Scale Match"
    bl_description = "Scale object to match texture dimensions"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object and 
                context.active_object.type == 'MESH' and
                len(context.active_object.material_slots) > 0)
    
    def execute(self, context):
        obj = context.active_object
        props = context.scene.textureaide_props
        
        # Get selected material and image node
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if not selected_material:
            self.report({'ERROR'}, "No material selected")
            return {'CANCELLED'}
        
        if not selected_node:
            self.report({'ERROR'}, "No image node selected")
            return {'CANCELLED'}
        
        if not selected_node.image:
            self.report({'ERROR'}, "Selected image node has no image")
            return {'CANCELLED'}
        
        image = selected_node.image
        
        # Handle UDIM vs regular textures
        if image.source == 'TILED':
            return self.handle_udim_scaling(context, obj, image, props)
        else:
            return self.handle_regular_scaling(context, obj, image, props)
    
    def handle_udim_scaling(self, context, obj, image, props):
        """Handle scaling for UDIM textures"""
        # Get UDIM files
        udim_files = find_udim_files(image.filepath)
        
        if not udim_files:
            self.report({'ERROR'}, "No UDIM files found")
            return {'CANCELLED'}
        
        # Determine which UDIM to use based on scaling mode
        scaling_mode = get_object_scaling_mode(obj)
        
        if scaling_mode == 'MANUAL':
            # Use selected UDIM from UI
            if 0 <= props.active_udim_index < len(props.udim_items):
                udim_item = props.udim_items[props.active_udim_index]
                udim_number = udim_item.udim_number
                
                if udim_number not in udim_files:
                    self.report({'ERROR'}, f"UDIM {udim_number} file not found")
                    return {'CANCELLED'}
                
                udim_info = udim_files[udim_number]
                tex_width = udim_info['width']
                tex_height = udim_info['height']
                
                message = f"Scaled using UDIM {udim_number}: {tex_width}x{tex_height}px"
            else:
                self.report({'ERROR'}, "No UDIM selected")
                return {'CANCELLED'}
        
        else:
            # Use automatic UDIM selection
            udim_number = select_optimal_udim(udim_files, scaling_mode)
            
            if not udim_number:
                self.report({'ERROR'}, "Could not determine optimal UDIM")
                return {'CANCELLED'}
            
            udim_info = udim_files[udim_number]
            tex_width = udim_info['width']
            tex_height = udim_info['height']
            
            message = f"Scaled using {scaling_mode.lower()} UDIM {udim_number}: {tex_width}x{tex_height}px"
        
        # Store target UDIM for this object
        set_object_target_udim(obj, udim_number)
        
        return self.apply_scaling(obj, tex_width, tex_height, props, message)
    
    def handle_regular_scaling(self, context, obj, image, props):
        """Handle scaling for regular textures"""
        tex_width = image.size[0]
        tex_height = image.size[1]
        
        if tex_width == 0 or tex_height == 0:
            self.report({'ERROR'}, "Invalid texture dimensions")
            return {'CANCELLED'}
        
        message = f"Scaled to texture size: {tex_width}x{tex_height}px"
        return self.apply_scaling(obj, tex_width, tex_height, props, message)
    
    def apply_scaling(self, obj, tex_width, tex_height, props, message):
        """Apply the actual scaling"""
        # Validate parameters
        validation = validate_scaling_parameters(obj, tex_width, tex_height, props.pixel_to_mm_ratio)
        
        if not validation['can_proceed']:
            for error in validation['errors']:
                self.report({'ERROR'}, error)
            return {'CANCELLED'}
        
        # Show warnings if any
        for warning in validation['warnings']:
            self.report({'WARNING'}, warning)
        
        # Apply scaling
        success = apply_texture_scaling(obj, tex_width, tex_height, props.pixel_to_mm_ratio)
        
        if not success:
            self.report({'ERROR'}, "Failed to apply scaling")
            return {'CANCELLED'}
        
        # Update last operation
        props.last_operation = message
        
        # Report success with real-world dimensions
        width_mm = tex_width / props.pixel_to_mm_ratio
        height_mm = tex_height / props.pixel_to_mm_ratio
        width_m = width_mm / 1000.0
        height_m = height_mm / 1000.0
        
        self.report({'INFO'}, f"{message}")
        self.report({'INFO'}, f"Real-world size: {width_mm:.1f}x{height_mm:.1f}mm ({width_m:.3f}x{height_m:.3f}m)")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_toggle_global_live_rescale(Operator):
    """Toggle global live rescale for all mesh objects"""
    bl_idname = "textureaide.toggle_global_live_rescale"
    bl_label = "Toggle Global Live Rescale"
    bl_description = "Enable/disable live rescale for all mesh objects"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        props = context.scene.textureaide_props
        
        # Toggle global setting
        props.global_live_rescale = not props.global_live_rescale
        
        # Update handlers
        from . import handlers
        handlers.update_live_rescale_handlers(context)
        
        status = "enabled" if props.global_live_rescale else "disabled"
        mesh_count = len([obj for obj in context.scene.objects if obj.type == 'MESH'])
        
        self.report({'INFO'}, f"Global live rescale {status} for {mesh_count} mesh objects")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_toggle_object_live_rescale(Operator):
    """Toggle live rescale for specific object"""
    bl_idname = "textureaide.toggle_object_live_rescale"
    bl_label = "Toggle Object Live Rescale"
    bl_description = "Enable/disable live rescale for specific object"
    bl_options = {'REGISTER'}
    
    object_name: StringProperty(
        name="Object Name",
        description="Name of object to toggle"
    )
    
    enable: BoolProperty(
        name="Enable",
        description="Whether to enable or disable live rescale"
    )
    
    def execute(self, context):
        # Find the object
        obj = None
        if self.object_name:
            obj = context.scene.objects.get(self.object_name)
        else:
            obj = context.active_object
        
        if not obj:
            self.report({'ERROR'}, "Object not found")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'ERROR'}, "Object is not a mesh")
            return {'CANCELLED'}
        
        # Set object-specific live rescale
        set_object_live_rescale(obj, self.enable)
        
        # Update handlers
        from . import handlers
        handlers.update_live_rescale_handlers(context)
        
        status = "enabled" if self.enable else "disabled"
        self.report({'INFO'}, f"Live rescale {status} for object '{obj.name}'")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_copy_global_to_object(Operator):
    """Copy global settings to current object as per-object settings"""
    bl_idname = "textureaide.copy_global_to_object"
    bl_label = "Copy Global Settings to Object"
    bl_description = "Copy current global settings to active object"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        from .properties import copy_global_settings_to_object
        copy_global_settings_to_object(obj)
        
        self.report({'INFO'}, f"Global settings copied to '{obj.name}'")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_clear_object_settings(Operator):
    """Clear per-object settings and revert to global"""
    bl_idname = "textureaide.clear_object_settings"
    bl_label = "Clear Object Settings"
    bl_description = "Remove per-object settings and use global defaults"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        from .properties import clear_object_settings
        clear_object_settings(obj)
        
        self.report({'INFO'}, f"Per-object settings cleared for '{obj.name}'")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_refresh_lists(Operator):
    """Refresh material, image node, and UDIM lists"""
    bl_idname = "textureaide.refresh_lists"
    bl_label = "Refresh Lists"
    bl_description = "Refresh all UI lists for current object"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.active_object
        
        if obj and obj.type == 'MESH':
            # Import here to avoid circular imports
            from . import panels
            panels.update_material_list(obj, context)
            self.report({'INFO'}, "Lists refreshed")
        else:
            self.report({'WARNING'}, "No mesh object selected")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_set_object_target_udim(Operator):
    """Set target UDIM for object (per-object mode)"""
    bl_idname = "textureaide.set_object_target_udim"
    bl_label = "Set Target UDIM"
    bl_description = "Set which UDIM this object should use for scaling"
    bl_options = {'REGISTER', 'UNDO'}
    
    udim_number: IntProperty(
        name="UDIM Number",
        description="Target UDIM number",
        min=1001,
        max=1100,
        default=1001
    )
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'
    
    def execute(self, context):
        obj = context.active_object
        
        set_object_target_udim(obj, self.udim_number)
        
        self.report({'INFO'}, f"Target UDIM set to {self.udim_number} for '{obj.name}'")
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_analyze_udim_sequence(Operator):
    """Analyze UDIM sequence for issues and optimization"""
    bl_idname = "textureaide.analyze_udim_sequence"
    bl_label = "Analyze UDIM Sequence"
    bl_description = "Analyze UDIM files for issues and provide suggestions"
    bl_options = {'REGISTER'}
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH' or not obj.material_slots:
            return False
        
        selected_material, selected_node = get_selected_material_and_node(obj)
        return (selected_node and selected_node.image and 
                selected_node.image.source == 'TILED')
    
    def execute(self, context):
        obj = context.active_object
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if not selected_node or not selected_node.image:
            self.report({'ERROR'}, "No image selected")
            return {'CANCELLED'}
        
        # Analyze UDIM sequence
        from .utils.udim_utils import validate_udim_sequence
        udim_files = find_udim_files(selected_node.image.filepath)
        validation = validate_udim_sequence(udim_files)
        
        # Report results
        if validation['valid']:
            self.report({'INFO'}, f"Found {len(udim_files)} UDIM files")
            
            for warning in validation['warnings']:
                self.report({'WARNING'}, warning)
            
            for suggestion in validation['suggestions']:
                self.report({'INFO'}, f"Suggestion: {suggestion}")
        else:
            for error in validation['errors']:
                self.report({'ERROR'}, error)
        
        return {'FINISHED'}

class TEXTUREAIDE_OT_batch_apply_settings(Operator):
    """Apply current settings to multiple selected objects"""
    bl_idname = "textureaide.batch_apply_settings"
    bl_label = "Batch Apply Settings"
    bl_description = "Apply current scaling settings to all selected mesh objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return len([obj for obj in context.selected_objects if obj.type == 'MESH']) > 1
    
    def execute(self, context):
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if len(mesh_objects) < 2:
            self.report({'ERROR'}, "Select at least 2 mesh objects")
            return {'CANCELLED'}
        
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        # Get settings from active object
        props = context.scene.textureaide_props
        
        success_count = 0
        error_count = 0
        
        for obj in mesh_objects:
            if obj == active_obj:
                continue  # Skip active object
            
            try:
                # Copy live rescale setting
                active_live_rescale = get_object_live_rescale(active_obj)
                set_object_live_rescale(obj, active_live_rescale)
                
                # Copy scaling mode and target UDIM if in per-object mode
                if props.live_rescale_mode == 'PER_OBJECT':
                    obj["textureaide_scaling_mode"] = get_object_scaling_mode(active_obj)
                    obj["textureaide_target_udim"] = get_object_target_udim(active_obj)
                
                success_count += 1
                
            except Exception as e:
                print(f"Error applying settings to {obj.name}: {e}")
                error_count += 1
        
        # Update handlers
        from . import handlers
        handlers.update_live_rescale_handlers(context)
        
        self.report({'INFO'}, f"Applied settings to {success_count} objects")
        
        if error_count > 0:
            self.report({'WARNING'}, f"Failed to update {error_count} objects")
        
        return {'FINISHED'}

# Registration
classes = [
    TEXTUREAIDE_OT_texture_scale_match,
    TEXTUREAIDE_OT_toggle_global_live_rescale,
    TEXTUREAIDE_OT_toggle_object_live_rescale,
    TEXTUREAIDE_OT_copy_global_to_object,
    TEXTUREAIDE_OT_clear_object_settings,
    TEXTUREAIDE_OT_refresh_lists,
    TEXTUREAIDE_OT_set_object_target_udim,
    TEXTUREAIDE_OT_analyze_udim_sequence,
    TEXTUREAIDE_OT_batch_apply_settings,
]

def register():
    """Register all operator classes"""
    print("Registering TextureAide operators...")
    
    for cls in classes:
        bpy.utils.register_class(cls)
    
    print("✓ TextureAide operators registered")

def unregister():
    """Unregister all operator classes"""
    print("Unregistering TextureAide operators...")
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Warning: Could not unregister {cls}: {e}")
    
    print("✓ TextureAide operators unregistered")