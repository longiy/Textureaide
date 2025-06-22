# panels.py - UI Panels and Lists

import bpy
from bpy.types import Panel, UIList

from .utils.udim_utils import find_udim_files
from .properties import get_object_live_rescale, get_objects_with_live_rescale

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

def update_material_selection(context):
    """Called when material selection changes"""
    obj = context.active_object
    if not obj or not obj.material_slots:
        return
    
    props = context.scene.textureaide_props
    
    # Update image node list for the selected material
    if 0 <= props.active_material_index < len(props.material_items):
        mat_item = props.material_items[props.active_material_index]
        if mat_item.material_index < len(obj.material_slots):
            material = obj.material_slots[mat_item.material_index].material
            update_image_node_list(material, context)

def update_image_node_selection(context):
    """Called when image node selection changes"""
    update_udim_list(context)

def update_material_list(obj, context):
    """Update the material list for the current object"""
    if not obj or not obj.material_slots:
        return
    
    props = context.scene.textureaide_props
    props.material_items.clear()
    
    for i, slot in enumerate(obj.material_slots):
        if slot.material:
            item = props.material_items.add()
            item.name = slot.material.name
            item.material_index = i
    
    # Reset active index and update dependent lists
    props.active_material_index = 0
    if len(props.material_items) > 0:
        mat_item = props.material_items[0]
        material = obj.material_slots[mat_item.material_index].material
        update_image_node_list(material, context)

def update_image_node_list(material, context):
    """Update the image node list for the selected material"""
    props = context.scene.textureaide_props
    props.image_node_items.clear()
    
    if not material or not material.node_tree:
        return
    
    image_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE']
    
    for node in image_nodes:
        item = props.image_node_items.add()
        item.name = node.name
        item.node_name = node.name
        item.image_name = node.image.name if node.image else ""
    
    # Reset active image node index and update UDIM list
    props.active_image_node_index = 0
    update_udim_list(context)

def update_udim_list(context):
    """Update the UDIM list for the selected image node (simplified)"""
    props = context.scene.textureaide_props
    props.udim_items.clear()
    
    obj = context.active_object
    if not obj:
        return
    
    selected_material, selected_node = get_selected_material_and_node(obj)
    if not selected_node or not selected_node.image:
        return
    
    # Only process UDIM images
    if selected_node.image.source != 'TILED':
        return
    
    # Get UDIM files from disk
    udim_files = find_udim_files(selected_node.image.filepath)
    
    # Populate UDIM list (user controlled - no UV analysis)
    for udim_num in sorted(udim_files.keys()):
        item = props.udim_items.add()
        item.udim_number = udim_num
        item.width = udim_files[udim_num].get('width', 0)
        item.height = udim_files[udim_num].get('height', 0)
        item.filepath = udim_files[udim_num].get('filepath', '')
        item.filename = udim_files[udim_num].get('filename', '')
        item.exists = udim_files[udim_num].get('exists', True)

# UI List for materials
class TEXTUREAIDE_UL_material_list(UIList):
    """Material list UI"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='MATERIAL')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MATERIAL')

# UI List for image nodes
class TEXTUREAIDE_UL_image_node_list(UIList):
    """Image node list UI"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.image_name:
                layout.label(text=f"{item.name} ({item.image_name})", icon='TEXTURE')
            else:
                layout.label(text=f"{item.name} (No Image)", icon='TEXTURE')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='TEXTURE')

# UI List for UDIM tiles
class TEXTUREAIDE_UL_udim_list(UIList):
    """UDIM tile list UI"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            
            # Show UDIM number
            row.label(text=f"UDIM {item.udim_number}", icon='UV')
            
            # Show resolution
            if item.width > 0 and item.height > 0:
                row.label(text=f"{item.width}x{item.height}")
            else:
                row.label(text="Unknown", icon='ERROR')
            
            # Show file status
            if not item.exists:
                row.label(text="Missing", icon='CANCEL')
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='UV')

# Main panel
class TEXTUREAIDE_PT_main_panel(Panel):
    """Enhanced TextureAide Main Panel with Hybrid Live Rescale"""
    bl_label = "TextureAide (UDIM)"
    bl_idname = "TEXTUREAIDE_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_context = "objectmode"
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        props = context.scene.textureaide_props
        
        if not obj or obj.type != 'MESH':
            layout.label(text="Select a mesh object", icon='ERROR')
            return
        
        if not obj.material_slots:
            layout.label(text="No materials on object", icon='ERROR')
            return
        
        # Live Rescale Mode Selection
        self.draw_live_rescale_section(layout, props, obj, context)
        
        layout.separator()
        
        # Materials section
        layout.label(text="Materials:")
        layout.template_list(
            "TEXTUREAIDE_UL_material_list", "",
            props, "material_items",
            props, "active_material_index",
            rows=3
        )
        
        # Image nodes section
        layout.label(text="Image Texture Nodes:")
        layout.template_list(
            "TEXTUREAIDE_UL_image_node_list", "",
            props, "image_node_items",
            props, "active_image_node_index",
            rows=3
        )
        
        # UDIM section
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if selected_node and selected_node.image:
            if selected_node.image.source == 'TILED':
                self.draw_udim_section(layout, props, selected_node)
            else:
                self.draw_regular_texture_section(layout, selected_node)
        
        # Main scaling controls
        layout.separator()
        self.draw_scaling_controls(layout, props, obj)
        
        # Settings and info
        self.draw_settings_section(layout, props)
        
        # Info section
        layout.separator()
        self.draw_info_section(layout, obj, selected_material, selected_node, props)
    
    def draw_live_rescale_section(self, layout, props, obj, context):
        """Draw hybrid live rescale controls"""
        box = layout.box()
        box.label(text="Live Rescale:", icon='PLAY')
        
        # Mode selection
        row = box.row()
        row.prop(props, "live_rescale_mode", expand=True)
        
        if props.live_rescale_mode == 'GLOBAL':
            # Global mode controls
            col = box.column()
            row = col.row()
            row.scale_y = 1.5
            
            if props.global_live_rescale:
                row.operator("textureaide.toggle_global_live_rescale", 
                           text="Global Live Rescale: ON", icon='PLAY', depress=True)
            else:
                row.operator("textureaide.toggle_global_live_rescale", 
                           text="Global Live Rescale: OFF", icon='PAUSE')
            
            # Show affected objects count
            mesh_count = len([o for o in context.scene.objects if o.type == 'MESH'])
            if props.global_live_rescale:
                col.label(text=f"Monitoring {mesh_count} mesh objects", icon='INFO')
            else:
                col.label(text=f"{mesh_count} mesh objects available", icon='INFO')
        
        else:
            # Per-object mode controls
            col = box.column()
            
            # Current object control
            row = col.row()
            row.scale_y = 1.5
            
            current_enabled = get_object_live_rescale(obj)
            op = row.operator("textureaide.toggle_object_live_rescale", 
                            text=f"'{obj.name}': ON" if current_enabled else f"'{obj.name}': OFF",
                            icon='PLAY' if current_enabled else 'PAUSE',
                            depress=current_enabled)
            op.object_name = obj.name
            op.enable = not current_enabled
            
            # Show other objects with live rescale
            enabled_objects = get_objects_with_live_rescale()
            other_objects = [o for o in enabled_objects if o != obj]
            
            if other_objects:
                col.separator()
                col.label(text="Other Objects with Live Rescale:")
                for other_obj in other_objects[:5]:  # Limit display
                    col.label(text=f"• {other_obj.name}", icon='CHECKMARK')
                
                if len(other_objects) > 5:
                    col.label(text=f"... and {len(other_objects) - 5} more")
            
            # Per-object utilities
            col.separator()
            row = col.row()
            row.operator("textureaide.copy_global_to_object", text="Copy Global", icon='DUPLICATE')
            row.operator("textureaide.clear_object_settings", text="Clear", icon='X')
    
    def draw_udim_section(self, layout, props, selected_node):
        """Draw UDIM-specific controls"""
        layout.separator()
        layout.label(text="UDIM Tiles:", icon='UV')
        
        # UDIM list
        layout.template_list(
            "TEXTUREAIDE_UL_udim_list", "",
            props, "udim_items",
            props, "active_udim_index",
            rows=4
        )
        
        # UDIM controls
        if props.udim_items:
            row = layout.row()
            row.operator("textureaide.analyze_udim_sequence", text="Analyze", icon='ANALYZER')
        
        # Scaling mode for UDIMs
        layout.prop(props, "scaling_mode")
    
    def draw_regular_texture_section(self, layout, selected_node):
        """Draw regular texture info"""
        box = layout.box()
        box.label(text="Regular Texture", icon='TEXTURE')
        image = selected_node.image
        box.label(text=f"Size: {image.size[0]}x{image.size[1]}")
    
    def draw_scaling_controls(self, layout, props, obj):
        """Draw main scaling controls"""
        row = layout.row()
        row.scale_y = 2.0
        
        # Dynamic button text
        if props.scaling_mode == 'MANUAL':
            button_text = "Scale to Selected"
        elif props.scaling_mode == 'FIRST':
            button_text = "Scale to First UDIM"
        elif props.scaling_mode == 'LARGEST':
            button_text = "Scale to Largest UDIM"
        elif props.scaling_mode == 'SMALLEST':
            button_text = "Scale to Smallest UDIM"
        else:
            button_text = "Apply Texture Scaling"
        
        row.operator("textureaide.texture_scale_match", text=button_text, icon='MESH_CUBE')
        
        # Pixel ratio setting
        layout.prop(props, "pixel_to_mm_ratio")
    
    def draw_settings_section(self, layout, props):
        """Draw settings and advanced options"""
        layout.separator()
        
        # Settings header
        row = layout.row()
        row.prop(props, "show_advanced_settings", 
                text="Advanced Settings", icon='TRIA_DOWN' if props.show_advanced_settings else 'TRIA_RIGHT')
        
        if props.show_advanced_settings:
            box = layout.box()
            
            # Auto refresh
            box.prop(props, "auto_refresh_lists")
            
            # Show missing files
            box.prop(props, "show_missing_files")
            
            # Refresh button
            box.operator("textureaide.refresh_lists", text="Refresh Lists", icon='FILE_REFRESH')
            
            # Batch operations
            box.separator()
            box.label(text="Batch Operations:")
            box.operator("textureaide.batch_apply_settings", text="Apply to Selected", icon='DUPLICATE')
    
    def draw_info_section(self, layout, obj, selected_material, selected_node, props):
        """Draw information and status"""
        box = layout.box()
        box.label(text="Information:", icon='INFO')
        
        # Object info
        if obj:
            dims = obj.dimensions
            box.label(text=f"Object: {obj.name}")
            box.label(text=f"Size: {dims.x:.3f} × {dims.y:.3f} × {dims.z:.3f}m")
        
        # Material info
        if selected_material:
            box.label(text=f"Material: {selected_material.name}")
        
        # Image info
        if selected_node and selected_node.image:
            image = selected_node.image
            box.label(text=f"Image: {image.name}")
            if image.source == 'TILED':
                box.label(text="Type: UDIM Texture")
                if props.udim_items:
                    box.label(text=f"UDIM Count: {len(props.udim_items)}")
            else:
                box.label(text=f"Size: {image.size[0]}×{image.size[1]}px")
        
        # Last operation
        if props.last_operation:
            box.separator()
            box.label(text="Last Operation:", icon='CHECKMARK')
            box.label(text=props.last_operation)

# Registration
classes = [
    TEXTUREAIDE_UL_material_list,
    TEXTUREAIDE_UL_image_node_list,
    TEXTUREAIDE_UL_udim_list,
    TEXTUREAIDE_PT_main_panel,
]

def register():
    """Register all panel classes"""
    print("Registering TextureAide panels...")
    
    for cls in classes:
        bpy.utils.register_class(cls)
    
    print("✓ TextureAide panels registered")

def unregister():
    """Unregister all panel classes"""
    print("Unregistering TextureAide panels...")
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Warning: Could not unregister {cls}: {e}")
    
    print("✓ TextureAide panels unregistered")