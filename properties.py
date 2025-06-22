# properties.py - Property Groups and Scene Properties (Hybrid Live Rescale)

import bpy
from bpy.props import (
    BoolProperty, IntProperty, FloatProperty, 
    CollectionProperty, StringProperty, EnumProperty, PointerProperty
)
from bpy.types import PropertyGroup

def update_material_selection(self, context):
    """Called when material selection changes"""
    # Avoid circular imports by importing here
    try:
        from . import panels
        panels.update_material_selection(context)
    except ImportError:
        pass

def update_image_node_selection(self, context):
    """Called when image node selection changes"""
    try:
        from . import panels
        panels.update_image_node_selection(context)
    except ImportError:
        pass

def update_live_rescale_mode(self, context):
    """Called when live rescale mode changes"""
    # Update handlers when switching between global/per-object modes
    try:
        from . import handlers
        handlers.update_live_rescale_handlers(context)
    except ImportError:
        pass

# Property group for material items
class TextureAide_MaterialItem(PropertyGroup):
    """Material list item for UI display"""
    name: StringProperty(
        name="Material Name",
        description="Name of the material"
    )
    material_index: IntProperty(
        name="Material Index", 
        description="Index in object's material slots"
    )

# Property group for image node items  
class TextureAide_ImageNodeItem(PropertyGroup):
    """Image texture node item for UI display"""
    name: StringProperty(
        name="Node Name",
        description="Name of the image texture node"
    )
    node_name: StringProperty(
        name="Node Name",
        description="Internal node name for lookup"
    )
    image_name: StringProperty(
        name="Image Name", 
        description="Name of the image data block"
    )

# Property group for UDIM items (simplified - user controlled)
class TextureAide_UDIMItem(PropertyGroup):
    """UDIM tile item for UI display"""
    udim_number: IntProperty(
        name="UDIM Number",
        description="UDIM tile number (e.g., 1001, 1002)",
        min=1001,
        max=1100
    )
    width: IntProperty(
        name="Width",
        description="Texture width in pixels",
        min=1
    )
    height: IntProperty(
        name="Height", 
        description="Texture height in pixels",
        min=1
    )
    filepath: StringProperty(
        name="File Path",
        description="Full path to the UDIM texture file"
    )
    filename: StringProperty(
        name="File Name",
        description="Filename of the UDIM texture"
    )
    exists: BoolProperty(
        name="File Exists",
        description="Whether the UDIM file exists on disk",
        default=True
    )

# Main scene properties container
class TextureAide_Properties(PropertyGroup):
    """Main property group for TextureAide addon"""
    
    # Collections for UI lists
    material_items: CollectionProperty(
        type=TextureAide_MaterialItem,
        name="Materials",
        description="Available materials on the active object"
    )
    
    image_node_items: CollectionProperty(
        type=TextureAide_ImageNodeItem,
        name="Image Nodes", 
        description="Available image texture nodes in selected material"
    )
    
    udim_items: CollectionProperty(
        type=TextureAide_UDIMItem,
        name="UDIM Tiles",
        description="Available UDIM tiles for selected image"
    )
    
    # Active selection indices
    active_material_index: IntProperty(
        name="Active Material",
        description="Currently selected material",
        default=0,
        update=update_material_selection
    )
    
    active_image_node_index: IntProperty(
        name="Active Image Node",
        description="Currently selected image texture node", 
        default=0,
        update=update_image_node_selection
    )
    
    active_udim_index: IntProperty(
        name="Active UDIM",
        description="Currently selected UDIM tile",
        default=0
    )
    
    # HYBRID LIVE RESCALE SETTINGS
    live_rescale_mode: EnumProperty(
        name="Live Rescale Mode",
        description="How live rescale operates",
        items=[
            ('GLOBAL', "Global", "Single setting affects all mesh objects"),
            ('PER_OBJECT', "Per Object", "Individual control for each object"),
        ],
        default='GLOBAL',
        update=update_live_rescale_mode
    )
    
    global_live_rescale: BoolProperty(
        name="Global Live Rescale",
        description="Enable live rescale for all mesh objects (Global Mode)",
        default=False
    )
    
    default_live_rescale: BoolProperty(
        name="Default Live Rescale",
        description="Default live rescale setting for new objects (Per-Object Mode)",
        default=True
    )
    
    # Scaling settings
    scaling_mode: EnumProperty(
        name="Scaling Mode",
        description="How to determine which UDIM to use for scaling",
        items=[
            ('MANUAL', "Manual Selection", "User manually selects UDIM tile"),
            ('FIRST', "First Available", "Use first UDIM in sequence"),
            ('LARGEST', "Largest Resolution", "Use UDIM with highest resolution"),
            ('SMALLEST', "Smallest Resolution", "Use UDIM with lowest resolution"),
        ],
        default='MANUAL'
    )
    
    pixel_to_mm_ratio: FloatProperty(
        name="Pixel to MM Ratio",
        description="How many pixels equal one millimeter",
        default=1.0,
        min=0.001,
        max=1000.0,
        precision=3
    )
    
    # UI settings
    auto_refresh_lists: BoolProperty(
        name="Auto Refresh Lists",
        description="Automatically refresh lists when objects change",
        default=True
    )
    
    show_missing_files: BoolProperty(
        name="Show Missing Files", 
        description="Show UDIM entries even if files don't exist",
        default=False
    )
    
    show_advanced_settings: BoolProperty(
        name="Show Advanced Settings",
        description="Show advanced scaling and UDIM options",
        default=False
    )
    
    # Info and status
    last_operation: StringProperty(
        name="Last Operation",
        description="Description of the last scaling operation performed"
    )
    
    udim_scan_path: StringProperty(
        name="UDIM Scan Path",
        description="Last path scanned for UDIM files",
        subtype='FILE_PATH'
    )

# Object-specific properties (stored as custom properties on objects)
# These will be accessed via obj["textureaide_*"] pattern

def get_object_live_rescale(obj) -> bool:
    """Get live rescale setting for specific object"""
    if not obj:
        return False
    
    props = bpy.context.scene.textureaide_props
    
    if props.live_rescale_mode == 'GLOBAL':
        return props.global_live_rescale
    else:
        # Per-object mode
        return obj.get("textureaide_live_rescale", props.default_live_rescale)

def set_object_live_rescale(obj, enabled: bool) -> None:
    """Set live rescale setting for specific object"""
    if not obj:
        return
    
    obj["textureaide_live_rescale"] = enabled
    
    # Also store scaling preferences per object
    if "textureaide_scaling_mode" not in obj:
        props = bpy.context.scene.textureaide_props
        obj["textureaide_scaling_mode"] = props.scaling_mode
        obj["textureaide_target_udim"] = 1001

def get_object_scaling_mode(obj) -> str:
    """Get scaling mode for specific object"""
    if not obj:
        return 'MANUAL'
    
    props = bpy.context.scene.textureaide_props
    
    if props.live_rescale_mode == 'GLOBAL':
        return props.scaling_mode
    else:
        return obj.get("textureaide_scaling_mode", props.scaling_mode)

def get_object_target_udim(obj) -> int:
    """Get target UDIM for specific object"""
    if not obj:
        return 1001
    
    return obj.get("textureaide_target_udim", 1001)

def set_object_target_udim(obj, udim: int) -> None:
    """Set target UDIM for specific object"""
    if not obj:
        return
    
    obj["textureaide_target_udim"] = udim

# Global state tracking
class TextureAide_GlobalState(PropertyGroup):
    """Global state tracking for the addon"""
    
    last_active_object: StringProperty(
        name="Last Active Object",
        description="Name of the last active object processed"
    )
    
    handlers_registered: BoolProperty(
        name="Handlers Registered",
        description="Whether event handlers are currently registered",
        default=False
    )
    
    live_rescale_active: BoolProperty(
        name="Live Rescale Active",
        description="Whether live rescale is currently monitoring changes",
        default=False
    )

# Utility functions for object property management
def copy_global_settings_to_object(obj) -> None:
    """Copy current global settings to object as per-object settings"""
    if not obj:
        return
    
    props = bpy.context.scene.textureaide_props
    
    # Copy current global settings
    obj["textureaide_live_rescale"] = props.global_live_rescale
    obj["textureaide_scaling_mode"] = props.scaling_mode
    obj["textureaide_target_udim"] = 1001  # Default

def clear_object_settings(obj) -> None:
    """Clear per-object settings from object"""
    if not obj:
        return
    
    settings_keys = [
        "textureaide_live_rescale",
        "textureaide_scaling_mode", 
        "textureaide_target_udim"
    ]
    
    for key in settings_keys:
        if key in obj:
            del obj[key]

def get_objects_with_live_rescale() -> list:
    """Get list of objects that have live rescale enabled"""
    objects = []
    props = bpy.context.scene.textureaide_props
    
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and get_object_live_rescale(obj):
            objects.append(obj)
    
    return objects

# Registration
classes = [
    TextureAide_MaterialItem,
    TextureAide_ImageNodeItem, 
    TextureAide_UDIMItem,
    TextureAide_Properties,
    TextureAide_GlobalState,
]

def register():
    """Register all property classes"""
    print("Registering TextureAide properties...")
    
    # Register property group classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add properties to scene
    bpy.types.Scene.textureaide_props = PointerProperty(
        type=TextureAide_Properties,
        name="TextureAide Properties",
        description="TextureAide addon properties"
    )
    
    bpy.types.Scene.textureaide_state = PointerProperty(
        type=TextureAide_GlobalState,
        name="TextureAide State", 
        description="TextureAide global state tracking"
    )
    
    print("✓ TextureAide properties registered")

def unregister():
    """Unregister all property classes"""
    print("Unregistering TextureAide properties...")
    
    # Remove scene properties
    if hasattr(bpy.types.Scene, 'textureaide_props'):
        del bpy.types.Scene.textureaide_props
    
    if hasattr(bpy.types.Scene, 'textureaide_state'):
        del bpy.types.Scene.textureaide_state
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Warning: Could not unregister {cls}: {e}")
    
    print("✓ TextureAide properties unregistered")
