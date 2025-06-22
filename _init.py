# __init__.py - Enhanced TextureAide Main Entry Point (Hybrid Live Rescale)

bl_info = {
    "name": "Enhanced TextureAide (UDIM Hybrid)",
    "author": "Enhanced TextureAide Team",
    "version": (2, 1, 0),
    "blender": (4, 3, 0),
    "location": "3D Viewport > Sidebar > Tool Tab",
    "description": "Match object dimensions to texture dimensions with UDIM support and hybrid live rescale",
    "category": "Mesh",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
}

import bpy
from typing import List, Type

# Store references to modules for proper unregistration
_modules = []
_handlers_registered = False

def get_addon_modules() -> List[str]:
    """Get list of addon modules to register"""
    return [
        "properties",
        "operators", 
        "panels",
        "handlers",
    ]

def register_module(module_name: str) -> None:
    """Register a single module"""
    try:
        module = __import__(f"{__name__}.{module_name}", fromlist=[module_name])
        if hasattr(module, 'register'):
            module.register()
            _modules.append(module)
            print(f"✓ Registered {module_name}")
        else:
            print(f"⚠ Module {module_name} has no register function")
    except Exception as e:
        print(f"✗ Failed to register {module_name}: {e}")
        raise

def unregister_module(module) -> None:
    """Unregister a single module"""
    try:
        if hasattr(module, 'unregister'):
            module.unregister()
            print(f"✓ Unregistered {module.__name__}")
        else:
            print(f"⚠ Module {module.__name__} has no unregister function")
    except Exception as e:
        print(f"✗ Failed to unregister {module.__name__}: {e}")

def register():
    """Register all addon components"""
    global _modules, _handlers_registered
    
    print("=" * 60)
    print("Registering Enhanced TextureAide (UDIM Hybrid)")
    print("=" * 60)
    
    # Clear any existing registrations
    _modules.clear()
    
    # Register modules in dependency order
    module_names = get_addon_modules()
    
    for module_name in module_names:
        try:
            register_module(module_name)
        except Exception as e:
            print(f"✗ Critical error registering {module_name}: {e}")
            # Cleanup any partially registered modules
            unregister()
            raise
    
    _handlers_registered = True
    
    print("=" * 60)
    print("✓ Enhanced TextureAide registration complete!")
    print("")
    print("Features:")
    print("• Hybrid Live Rescale (Global + Per-Object modes)")
    print("• UDIM texture support with file system analysis")
    print("• User-controlled UDIM tile selection")
    print("• Pixel-to-millimeter scaling")
    print("• Batch operations for multiple objects")
    print("• Real-time texture change monitoring")
    print("")
    print("Location: 3D Viewport > Sidebar > Tool Tab > TextureAide (UDIM)")
    print("=" * 60)

def unregister():
    """Unregister all addon components"""
    global _modules, _handlers_registered
    
    print("=" * 60)
    print("Unregistering Enhanced TextureAide (UDIM Hybrid)")
    print("=" * 60)
    
    # Unregister in reverse order (handlers first, properties last)
    for module in reversed(_modules):
        unregister_module(module)
    
    _modules.clear()
    _handlers_registered = False
    
    print("✓ Enhanced TextureAide unregistration complete!")
    print("=" * 60)

# Reload support for development
if "bpy" in locals():
    import importlib
    
    # List of modules that might need reloading
    reload_modules = [
        "properties",
        "operators",
        "panels", 
        "handlers",
        "utils.file_utils",
        "utils.udim_utils", 
        "utils.scaling_utils",
    ]
    
    print("Reloading Enhanced TextureAide modules...")
    for module_name in reload_modules:
        try:
            if module_name in locals():
                importlib.reload(locals()[module_name])
                print(f"↻ Reloaded {module_name}")
        except Exception as e:
            print(f"⚠ Could not reload {module_name}: {e}")

# Development helper functions
def get_addon_info():
    """Get addon information for debugging"""
    return {
        "name": bl_info["name"],
        "version": bl_info["version"],
        "blender_version": bl_info["blender"],
        "modules_registered": len(_modules),
        "handlers_active": _handlers_registered,
        "features": [
            "Hybrid Live Rescale",
            "UDIM Support", 
            "File System Analysis",
            "Batch Operations",
            "Real-time Monitoring"
        ]
    }

def get_handler_status():
    """Get handler status for debugging"""
    try:
        from . import handlers
        return handlers.get_handler_status()
    except ImportError:
        return {"error": "Handlers module not available"}

def reset_addon_state():
    """Reset addon state (for debugging)"""
    try:
        # Clear any custom properties from selected objects
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                keys_to_remove = [key for key in obj.keys() if key.startswith("textureaide_")]
                for key in keys_to_remove:
                    del obj[key]
        
        # Reset scene properties
        if hasattr(bpy.context.scene, 'textureaide_props'):
            props = bpy.context.scene.textureaide_props
            props.global_live_rescale = False
            props.live_rescale_mode = 'GLOBAL'
            props.last_operation = ""
        
        print("✓ Addon state reset")
        
    except Exception as e:
        print(f"✗ Error resetting addon state: {e}")

# Test function for development
if __name__ == "__main__":
    print("Enhanced TextureAide - Direct execution")
    print("Use as Blender addon for full functionality")
    print(f"Version: {bl_info['version']}")
    print(f"Blender: {bl_info['blender']}+")