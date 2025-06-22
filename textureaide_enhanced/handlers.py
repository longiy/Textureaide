# handlers.py - Event Handlers

import bpy
from bpy.app.handlers import persistent
from typing import Set, Dict, Any

# Global state tracking
_last_active_object = None
_last_texture_dimensions = {}
_last_udim_usage = {}
_handlers_registered = False

def update_live_rescale_handlers(context):
    """Update handlers based on current live rescale settings"""
    global _handlers_registered
    
    props = context.scene.textureaide_props
    
    # Determine if any live rescale is active
    live_rescale_active = False
    
    if props.live_rescale_mode == 'GLOBAL':
        live_rescale_active = props.global_live_rescale
    else:
        # Check if any objects have per-object live rescale enabled
        from .properties import get_objects_with_live_rescale
        live_rescale_active = len(get_objects_with_live_rescale()) > 0
    
    # Add or remove handlers based on state
    if live_rescale_active and not _handlers_registered:
        register_handlers()
    elif not live_rescale_active and _handlers_registered:
        unregister_handlers()

def register_handlers():
    """Register event handlers"""
    global _handlers_registered
    
    if _handlers_registered:
        return
    
    # Add handlers
    if object_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(object_selection_handler)
    
    if texture_change_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(texture_change_handler)
    
    if scene_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(scene_update_handler)
    
    _handlers_registered = True
    print("✓ TextureAide handlers registered")

def unregister_handlers():
    """Unregister event handlers"""
    global _handlers_registered
    
    if not _handlers_registered:
        return
    
    # Remove handlers
    if object_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(object_selection_handler)
    
    if texture_change_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(texture_change_handler)
    
    if scene_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(scene_update_handler)
    
    _handlers_registered = False
    print("✓ TextureAide handlers unregistered")

@persistent
def object_selection_handler(scene, depsgraph):
    """Handle object selection changes"""
    global _last_active_object
    
    try:
        current_object = bpy.context.active_object
        
        # Check if the active object changed
        if current_object != _last_active_object:
            _last_active_object = current_object
            
            # Only refresh if it's a mesh object with materials
            if (current_object and 
                current_object.type == 'MESH' and 
                current_object.material_slots and
                hasattr(bpy.context.scene, 'textureaide_props')):
                
                props = bpy.context.scene.textureaide_props
                if props.auto_refresh_lists:
                    # Import here to avoid circular imports
                    from . import panels
                    panels.update_material_list(current_object, bpy.context)
                    
    except Exception as e:
        print(f"Error in object selection handler: {e}")

@persistent
def texture_change_handler(scene):
    """Handle texture changes for live rescaling"""
    global _last_texture_dimensions
    
    try:
        if not hasattr(scene, 'textureaide_props'):
            return
        
        props = scene.textureaide_props
        
        # Get objects that should be monitored
        monitored_objects = get_monitored_objects(scene, props)
        
        for obj in monitored_objects:
            if process_object_texture_changes(obj, props):
                # Texture changed for this object, apply scaling
                apply_live_scaling(obj, props)
                
    except Exception as e:
        print(f"Error in texture change handler: {e}")

@persistent
def scene_update_handler(scene):
    """Handle general scene updates"""
    try:
        if not hasattr(scene, 'textureaide_props'):
            return
        
        # Update global state
        state = scene.textureaide_state
        state.live_rescale_active = _handlers_registered
        
    except Exception as e:
        print(f"Error in scene update handler: {e}")

def get_monitored_objects(scene, props) -> list:
    """Get list of objects that should be monitored for live rescale"""
    monitored_objects = []
    
    if props.live_rescale_mode == 'GLOBAL':
        if props.global_live_rescale:
            # Monitor all mesh objects
            monitored_objects = [obj for obj in scene.objects if obj.type == 'MESH']
    else:
        # Monitor objects with per-object live rescale enabled
        from .properties import get_object_live_rescale
        monitored_objects = [obj for obj in scene.objects 
                           if obj.type == 'MESH' and get_object_live_rescale(obj)]
    
    return monitored_objects

def process_object_texture_changes(obj, props) -> bool:
    """Check if texture dimensions changed for an object"""
    global _last_texture_dimensions
    
    try:
        # Get selected material and image node
        from .panels import get_selected_material_and_node
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if not selected_material or not selected_node or not selected_node.image:
            return False
        
        image = selected_node.image
        obj_id = obj.as_pointer()
        node_key = f"{obj_id}_{selected_node.name}"
        
        # Get current dimensions (basic check for regular textures)
        if image.source != 'TILED':
            current_dimensions = (image.size[0], image.size[1])
        else:
            # For UDIM textures, we need to check the specific UDIM being used
            from .properties import get_object_target_udim
            from .utils.udim_utils import find_udim_files
            
            target_udim = get_object_target_udim(obj)
            udim_files = find_udim_files(image.filepath)
            
            if target_udim in udim_files:
                udim_info = udim_files[target_udim]
                current_dimensions = (udim_info['width'], udim_info['height'])
            else:
                return False
        
        # Check if dimensions changed
        if (node_key not in _last_texture_dimensions or 
            _last_texture_dimensions[node_key] != current_dimensions):
            
            _last_texture_dimensions[node_key] = current_dimensions
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing texture changes for {obj.name}: {e}")
        return False

def apply_live_scaling(obj, props):
    """Apply live scaling to an object"""
    try:
        from .panels import get_selected_material_and_node
        from .utils.scaling_utils import apply_texture_scaling
        from .utils.udim_utils import find_udim_files, select_optimal_udim
        from .properties import get_object_scaling_mode, get_object_target_udim
        
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if not selected_material or not selected_node or not selected_node.image:
            return
        
        image = selected_node.image
        
        # Determine texture dimensions to use
        if image.source == 'TILED':
            # UDIM texture
            scaling_mode = get_object_scaling_mode(obj)
            udim_files = find_udim_files(image.filepath)
            
            if not udim_files:
                return
            
            if scaling_mode == 'MANUAL':
                # Use object's target UDIM
                target_udim = get_object_target_udim(obj)
                if target_udim in udim_files:
                    udim_info = udim_files[target_udim]
                    tex_width = udim_info['width']
                    tex_height = udim_info['height']
                else:
                    return
            else:
                # Use automatic selection
                target_udim = select_optimal_udim(udim_files, scaling_mode)
                if target_udim and target_udim in udim_files:
                    udim_info = udim_files[target_udim]
                    tex_width = udim_info['width']
                    tex_height = udim_info['height']
                else:
                    return
        else:
            # Regular texture
            tex_width = image.size[0]
            tex_height = image.size[1]
        
        # Apply scaling
        if tex_width > 0 and tex_height > 0:
            apply_texture_scaling(obj, tex_width, tex_height, props.pixel_to_mm_ratio)
            
            # Update last operation
            props.last_operation = f"Live scaled {obj.name} to {tex_width}x{tex_height}px"
            
    except Exception as e:
        print(f"Error applying live scaling to {obj.name}: {e}")

def cleanup_global_state():
    """Clean up global state variables"""
    global _last_active_object, _last_texture_dimensions, _last_udim_usage, _handlers_registered
    
    _last_active_object = None
    _last_texture_dimensions.clear()
    _last_udim_usage.clear()
    _handlers_registered = False

def get_handler_status() -> dict:
    """Get current handler status for debugging"""
    return {
        'handlers_registered': _handlers_registered,
        'object_selection_registered': object_selection_handler in bpy.app.handlers.depsgraph_update_post,
        'texture_change_registered': texture_change_handler in bpy.app.handlers.depsgraph_update_post,
        'scene_update_registered': scene_update_handler in bpy.app.handlers.depsgraph_update_post,
        'tracked_objects': len(_last_texture_dimensions),
        'last_active_object': _last_active_object.name if _last_active_object else None,
    }

# Registration functions
def register():
    """Register handlers (called during addon registration)"""
    print("TextureAide handlers module loaded (handlers registered on-demand)")
    
    # Don't register handlers immediately - they're registered when live rescale is enabled
    # This improves startup performance

def unregister():
    """Unregister handlers (called during addon unregistration)"""
    print("Unregistering TextureAide handlers...")
    
    # Force unregister all handlers
    unregister_handlers()
    cleanup_global_state()
    
    print("✓ TextureAide handlers unregistered")
