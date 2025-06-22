import bpy
import bmesh
from mathutils import Vector
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, IntProperty, CollectionProperty, StringProperty
from bpy.types import PropertyGroup, UIList

# Global variable to store live rescale state
live_rescale_enabled = False
last_texture_dimensions = {}
last_active_object = None

def apply_texture_scaling(obj, tex_width, tex_height):
    """Apply pixel-to-millimeter scaling (hardcoded)"""
    # Convert pixels to millimeters to Blender units (1 Blender unit = 1 meter)
    new_width = tex_width / 1000.0  # mm to meters
    new_height = tex_height / 1000.0  # mm to meters
    
    # Get current object dimensions
    current_dimensions = obj.dimensions.copy()
    
    # Calculate scale factors to achieve exact pixel-to-mm dimensions
    if current_dimensions.x != 0 and current_dimensions.y != 0:
        scale_x = new_width / current_dimensions.x
        scale_y = new_height / current_dimensions.y
        
        obj.scale.x *= scale_x
        obj.scale.y *= scale_y
    
    bpy.context.view_layer.update()

# Property group for material items
class MaterialItem(PropertyGroup):
    name: StringProperty()
    material_index: IntProperty()

# Property group for image node items
class ImageNodeItem(PropertyGroup):
    name: StringProperty()
    node_name: StringProperty()
    image_name: StringProperty()

# Scene properties to store UI state
class TextureScaleProperties(PropertyGroup):
    material_items: CollectionProperty(type=MaterialItem)
    image_node_items: CollectionProperty(type=ImageNodeItem)
    active_material_index: IntProperty(default=0, update=lambda self, context: update_material_selection(context))
    active_image_node_index: IntProperty(default=0)

# UI List for materials
class MATERIAL_UL_texture_scale_list(UIList):
    """Material list UI"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='MATERIAL')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MATERIAL')

# UI List for image nodes
class IMAGE_UL_texture_scale_list(UIList):
    """Image node list UI"""
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Show node name and image name if available
            if item.image_name:
                layout.label(text=f"{item.name} ({item.image_name})", icon='TEXTURE')
            else:
                layout.label(text=f"{item.name} (No Image)", icon='TEXTURE')
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon='TEXTURE')

def update_material_selection(context):
    """Called when material selection changes"""
    obj = context.active_object
    if not obj or not obj.material_slots:
        return
    
    props = context.scene.texture_scale_props
    
    # Update image node list for the selected material
    if 0 <= props.active_material_index < len(props.material_items):
        mat_item = props.material_items[props.active_material_index]
        if mat_item.material_index < len(obj.material_slots):
            material = obj.material_slots[mat_item.material_index].material
            update_image_node_list(material, context)

# Handler for automatic list refresh on object selection change
@persistent
def object_selection_handler(scene, depsgraph):
    global last_active_object
    
    current_object = bpy.context.active_object
    
    # Check if the active object changed
    if current_object != last_active_object:
        last_active_object = current_object
        
        # Only refresh if it's a mesh object with materials
        if (current_object and 
            current_object.type == 'MESH' and 
            current_object.material_slots):
            update_material_list(current_object, bpy.context)

# Handler for live rescaling
@persistent
def texture_change_handler(scene):
    global live_rescale_enabled, last_texture_dimensions
    
    if not live_rescale_enabled:
        return
    
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        return
    
    # Get selected material and image node
    selected_material, selected_node = get_selected_material_and_node(obj)
    if not selected_material or not selected_node:
        return
    
    if not selected_node.image:
        return
    
    image = selected_node.image
    current_dimensions = (image.size[0], image.size[1])
    obj_id = obj.as_pointer()
    node_key = f"{obj_id}_{selected_node.name}"
    
    # Check if dimensions changed
    if (node_key not in last_texture_dimensions or 
        last_texture_dimensions[node_key] != current_dimensions):
        
        last_texture_dimensions[node_key] = current_dimensions
        
        # Apply scaling logic
        tex_width, tex_height = current_dimensions
        if tex_width > 0 and tex_height > 0:
            aspect_ratio = tex_width / tex_height
            dimensions = obj.dimensions.copy()
            
            if dimensions.x >= dimensions.y:
                new_x = dimensions.x
                new_y = dimensions.x / aspect_ratio
            else:
                new_y = dimensions.y
                new_x = dimensions.y * aspect_ratio
            
            scale_x = new_x / dimensions.x if dimensions.x != 0 else 1
            scale_y = new_y / dimensions.y if dimensions.y != 0 else 1
            
            obj.scale.x *= scale_x
            obj.scale.y *= scale_y
            
            bpy.context.view_layer.update()

def get_selected_material_and_node(obj):
    """Get the currently selected material and image node from UI"""
    if not obj.material_slots:
        return None, None
    
    props = bpy.context.scene.texture_scale_props
    
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

def update_material_list(obj, context):
    """Update the material list for the current object"""
    if not obj or not obj.material_slots:
        return
    
    props = context.scene.texture_scale_props
    props.material_items.clear()
    
    for i, slot in enumerate(obj.material_slots):
        if slot.material:
            item = props.material_items.add()
            item.name = slot.material.name
            item.material_index = i
    
    # Reset active index and update image nodes
    props.active_material_index = 0
    if len(props.material_items) > 0:
        mat_item = props.material_items[0]
        material = obj.material_slots[mat_item.material_index].material
        update_image_node_list(material, context)

def update_image_node_list(material, context):
    """Update the image node list for the selected material"""
    props = context.scene.texture_scale_props
    props.image_node_items.clear()
    
    if not material or not material.node_tree:
        return
    
    image_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE']
    
    for node in image_nodes:
        item = props.image_node_items.add()
        item.name = node.name
        item.node_name = node.name
        item.image_name = node.image.name if node.image else ""
    
    # Reset active image node index
    props.active_image_node_index = 0

# Operator class for the texture scale matching functionality
class MESH_OT_texture_scale_match(bpy.types.Operator):
    """Match object dimensions to selected texture dimensions"""
    bl_idname = "mesh.texture_scale_match"
    bl_label = "Texture Scale Match"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return (context.active_object and 
                context.active_object.type == 'MESH' and
                len(context.active_object.material_slots) > 0)
    
    def execute(self, context):
        obj = context.active_object
        
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
        
        # Get texture dimensions
        image = selected_node.image
        tex_width = image.size[0]
        tex_height = image.size[1]
        
        if tex_width == 0 or tex_height == 0:
            self.report({'ERROR'}, "Invalid texture dimensions")
            return {'CANCELLED'}
        
        # Apply scaling using pixel-to-millimeter conversion
        apply_texture_scaling(obj, tex_width, tex_height)
        
        # Report with real-world dimensions
        width_mm = tex_width
        height_mm = tex_height
        width_m = width_mm / 1000.0
        height_m = height_mm / 1000.0
        self.report({'INFO'}, f"Scaled to real-world size: {width_mm}x{height_mm}mm ({width_m:.3f}x{height_m:.3f}m)")
        
        return {'FINISHED'}

# Operator for toggling live rescale
class MESH_OT_toggle_live_rescale(bpy.types.Operator):
    """Toggle live texture scale matching"""
    bl_idname = "mesh.toggle_live_rescale"
    bl_label = "Toggle Live Rescale"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        global live_rescale_enabled
        
        live_rescale_enabled = not live_rescale_enabled
        
        if live_rescale_enabled:
            # Add handlers if not already present
            if texture_change_handler not in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.append(texture_change_handler)
            if object_selection_handler not in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.append(object_selection_handler)
            self.report({'INFO'}, "Live rescale enabled")
        else:
            # Remove handlers
            if texture_change_handler in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(texture_change_handler)
            if object_selection_handler in bpy.app.handlers.depsgraph_update_post:
                bpy.app.handlers.depsgraph_update_post.remove(object_selection_handler)
            self.report({'INFO'}, "Live rescale disabled")
        
        return {'FINISHED'}

# Operator to refresh lists (kept for compatibility)
class MESH_OT_refresh_lists(bpy.types.Operator):
    """Refresh material and image node lists"""
    bl_idname = "mesh.refresh_texture_lists"
    bl_label = "Refresh Lists"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'MESH':
            update_material_list(obj, context)
        return {'FINISHED'}

# Panel class for the UI
class VIEW3D_PT_texture_scale_panel(bpy.types.Panel):
    """Texture Scale Match Panel"""
    bl_label = "Texture Scale Match"
    bl_idname = "VIEW3D_PT_texture_scale"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_context = "objectmode"
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        props = context.scene.texture_scale_props
        
        if not obj or obj.type != 'MESH':
            layout.label(text="Select a mesh object", icon='ERROR')
            return
        
        if not obj.material_slots:
            layout.label(text="No materials on object", icon='ERROR')
            return
        
        # Materials section with template_list
        layout.label(text="Materials:")
        row = layout.row()
        row.template_list(
            "MATERIAL_UL_texture_scale_list", "",  # UI list class name
            props, "material_items",  # Collection property
            props, "active_material_index",  # Active index property
            rows=3
        )
        
        # Image nodes section with template_list
        layout.label(text="Image Texture Nodes:")
        row = layout.row()
        row.template_list(
            "IMAGE_UL_texture_scale_list", "",  # UI list class name
            props, "image_node_items",  # Collection property
            props, "active_image_node_index",  # Active index property
            rows=3
        )
        
        # Main buttons
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        row.operator("mesh.texture_scale_match", text="Texture Scale Match", icon='TEXTURE')
        
        # Live rescale toggle button
        row = layout.row()
        row.scale_y = 1.5
        global live_rescale_enabled
        if live_rescale_enabled:
            row.operator("mesh.toggle_live_rescale", text="Live Rescale: ON", icon='PLAY', depress=True)
        else:
            row.operator("mesh.toggle_live_rescale", text="Live Rescale: OFF", icon='PAUSE')
        
        # Info section
        layout.separator()
        box = layout.box()
        box.label(text="Current Selection Info:", icon='INFO')
        
        selected_material, selected_node = get_selected_material_and_node(obj)
        
        if selected_material:
            box.label(text=f"Material: {selected_material.name}")
            
            if selected_node:
                node_info = f"Node: {selected_node.name}"
                if selected_node.image:
                    image = selected_node.image
                    box.label(text=node_info)
                    box.label(text=f"Image: {image.name}")
                    box.label(text=f"Size: {image.size[0]}x{image.size[1]}")
                    aspect = image.size[0] / image.size[1] if image.size[1] != 0 else 1
                    box.label(text=f"Aspect: {aspect:.3f}")
                    
                    # Show real-world dimensions (pixel = mm)
                    width_mm = image.size[0]
                    height_mm = image.size[1]
                    width_m = width_mm / 1000.0
                    height_m = height_mm / 1000.0
                    box.label(text=f"Real size: {width_mm}x{height_mm}mm")
                    box.label(text=f"Blender size: {width_m:.3f}x{height_m:.3f}m")
                    
                    # Show live rescale status
                    if live_rescale_enabled:
                        box.label(text="Live rescale: ACTIVE", icon='PLAY')
                    else:
                        box.label(text="Live rescale: INACTIVE", icon='PAUSE')
                else:
                    box.label(text=f"{node_info} (No Image)", icon='ERROR')
            else:
                box.label(text="No image node selected", icon='ERROR')
        else:
            box.label(text="No material selected", icon='ERROR')

# Registration functions
def register():
    bpy.utils.register_class(MaterialItem)
    bpy.utils.register_class(ImageNodeItem)
    bpy.utils.register_class(TextureScaleProperties)
    bpy.utils.register_class(MATERIAL_UL_texture_scale_list)
    bpy.utils.register_class(IMAGE_UL_texture_scale_list)
    bpy.utils.register_class(MESH_OT_texture_scale_match)
    bpy.utils.register_class(MESH_OT_toggle_live_rescale)
    bpy.utils.register_class(MESH_OT_refresh_lists)
    bpy.utils.register_class(VIEW3D_PT_texture_scale_panel)
    
    bpy.types.Scene.texture_scale_props = bpy.props.PointerProperty(type=TextureScaleProperties)
    
    # Add the object selection handler immediately
    if object_selection_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(object_selection_handler)

def unregister():
    global live_rescale_enabled
    
    # Clean up handlers
    if texture_change_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(texture_change_handler)
    if object_selection_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(object_selection_handler)
    
    live_rescale_enabled = False
    
    bpy.utils.unregister_class(MESH_OT_texture_scale_match)
    bpy.utils.unregister_class(MESH_OT_toggle_live_rescale)
    bpy.utils.unregister_class(MESH_OT_refresh_lists)
    bpy.utils.unregister_class(VIEW3D_PT_texture_scale_panel)
    bpy.utils.unregister_class(IMAGE_UL_texture_scale_list)
    bpy.utils.unregister_class(MATERIAL_UL_texture_scale_list)
    bpy.utils.unregister_class(TextureScaleProperties)
    bpy.utils.unregister_class(ImageNodeItem)
    bpy.utils.unregister_class(MaterialItem)
    
    del bpy.types.Scene.texture_scale_props

# This allows you to run the script directly from Blender's text editor
if __name__ == "__main__":
    register()
    print("Enhanced Texture Scale Match add-on registered!")
