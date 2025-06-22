# utils/scaling_utils.py - Texture Scaling Mathematics

import bpy
from mathutils import Vector
from typing import Tuple, Optional

def pixels_to_blender_units(pixels: int, pixel_to_mm_ratio: float = 1.0) -> float:
    """
    Convert pixels to Blender units (meters)
    
    Args:
        pixels: Number of pixels
        pixel_to_mm_ratio: How many pixels equal one millimeter
    
    Returns:
        Size in Blender units (meters)
    """
    # Convert pixels to millimeters, then to meters
    millimeters = pixels / pixel_to_mm_ratio
    meters = millimeters / 1000.0
    return meters

def blender_units_to_pixels(blender_units: float, pixel_to_mm_ratio: float = 1.0) -> int:
    """
    Convert Blender units (meters) to pixels
    
    Args:
        blender_units: Size in Blender units (meters)
        pixel_to_mm_ratio: How many pixels equal one millimeter
    
    Returns:
        Number of pixels
    """
    # Convert meters to millimeters, then to pixels
    millimeters = blender_units * 1000.0
    pixels = millimeters * pixel_to_mm_ratio
    return int(pixels)

def calculate_real_world_size(width_pixels: int, height_pixels: int, pixel_to_mm_ratio: float = 1.0) -> Tuple[float, float]:
    """
    Calculate real-world dimensions from pixel dimensions
    
    Args:
        width_pixels: Width in pixels
        height_pixels: Height in pixels
        pixel_to_mm_ratio: How many pixels equal one millimeter
    
    Returns:
        Tuple of (width_meters, height_meters)
    """
    width_meters = pixels_to_blender_units(width_pixels, pixel_to_mm_ratio)
    height_meters = pixels_to_blender_units(height_pixels, pixel_to_mm_ratio)
    return (width_meters, height_meters)

def calculate_scale_factors(obj, target_width: float, target_height: float) -> Tuple[float, float]:
    """
    Calculate scale factors needed to achieve target dimensions
    
    Args:
        obj: Blender object
        target_width: Target width in Blender units
        target_height: Target height in Blender units
    
    Returns:
        Tuple of (scale_x, scale_y) factors
    """
    if not obj:
        return (1.0, 1.0)
    
    current_dimensions = obj.dimensions.copy()
    
    # Avoid division by zero
    if current_dimensions.x == 0 or current_dimensions.y == 0:
        return (1.0, 1.0)
    
    scale_x = target_width / current_dimensions.x
    scale_y = target_height / current_dimensions.y
    
    return (scale_x, scale_y)

def apply_texture_scaling(obj, tex_width: int, tex_height: int, pixel_to_mm_ratio: float = 1.0) -> bool:
    """
    Apply texture-based scaling to an object
    
    Args:
        obj: Blender object to scale
        tex_width: Texture width in pixels
        tex_height: Texture height in pixels
        pixel_to_mm_ratio: Pixel to millimeter conversion ratio
    
    Returns:
        True if scaling was successful, False otherwise
    """
    if not obj or obj.type != 'MESH':
        return False
    
    try:
        # Calculate target dimensions in Blender units
        target_width, target_height = calculate_real_world_size(
            tex_width, tex_height, pixel_to_mm_ratio
        )
        
        # Calculate scale factors
        scale_x, scale_y = calculate_scale_factors(obj, target_width, target_height)
        
        # Apply scaling
        obj.scale.x *= scale_x
        obj.scale.y *= scale_y
        
        # Update view layer
        bpy.context.view_layer.update()
        
        return True
        
    except Exception as e:
        print(f"Error applying texture scaling: {e}")
        return False

def get_object_texture_scale_info(obj, tex_width: int, tex_height: int, pixel_to_mm_ratio: float = 1.0) -> dict:
    """
    Get scaling information without applying it
    
    Args:
        obj: Blender object
        tex_width: Texture width in pixels
        tex_height: Texture height in pixels
        pixel_to_mm_ratio: Pixel to millimeter conversion ratio
    
    Returns:
        Dictionary with scaling information
    """
    info = {
        'current_dimensions': (0, 0, 0),
        'target_dimensions': (0, 0),
        'scale_factors': (1.0, 1.0),
        'texture_size_mm': (0, 0),
        'texture_size_m': (0, 0),
        'valid': False
    }
    
    if not obj or obj.type != 'MESH':
        return info
    
    try:
        # Current object dimensions
        current_dims = obj.dimensions.copy()
        info['current_dimensions'] = (current_dims.x, current_dims.y, current_dims.z)
        
        # Target dimensions
        target_width, target_height = calculate_real_world_size(
            tex_width, tex_height, pixel_to_mm_ratio
        )
        info['target_dimensions'] = (target_width, target_height)
        
        # Scale factors
        scale_x, scale_y = calculate_scale_factors(obj, target_width, target_height)
        info['scale_factors'] = (scale_x, scale_y)
        
        # Texture size information
        width_mm = tex_width / pixel_to_mm_ratio
        height_mm = tex_height / pixel_to_mm_ratio
        info['texture_size_mm'] = (width_mm, height_mm)
        info['texture_size_m'] = (target_width, target_height)
        
        info['valid'] = True
        
    except Exception as e:
        print(f"Error calculating scaling info: {e}")
    
    return info

def validate_scaling_parameters(obj, tex_width: int, tex_height: int, pixel_to_mm_ratio: float = 1.0) -> dict:
    """
    Validate scaling parameters before applying
    
    Args:
        obj: Blender object
        tex_width: Texture width in pixels
        tex_height: Texture height in pixels
        pixel_to_mm_ratio: Pixel to millimeter conversion ratio
    
    Returns:
        Validation result dictionary
    """
    result = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'can_proceed': False
    }
    
    # Check object
    if not obj:
        result['errors'].append("No object provided")
        return result
    
    if obj.type != 'MESH':
        result['errors'].append("Object is not a mesh")
        return result
    
    # Check texture dimensions
    if tex_width <= 0 or tex_height <= 0:
        result['errors'].append("Invalid texture dimensions")
        return result
    
    if tex_width > 16384 or tex_height > 16384:
        result['warnings'].append("Very large texture dimensions detected")
    
    # Check pixel ratio
    if pixel_to_mm_ratio <= 0:
        result['errors'].append("Invalid pixel to millimeter ratio")
        return result
    
    if pixel_to_mm_ratio > 100:
        result['warnings'].append("Very high pixel density - object will be very small")
    
    if pixel_to_mm_ratio < 0.01:
        result['warnings'].append("Very low pixel density - object will be very large")
    
    # Check object dimensions
    current_dims = obj.dimensions.copy()
    if current_dims.x == 0 or current_dims.y == 0:
        result['errors'].append("Object has zero dimensions")
        return result
    
    # Check scale factors
    target_width, target_height = calculate_real_world_size(
        tex_width, tex_height, pixel_to_mm_ratio
    )
    scale_x, scale_y = calculate_scale_factors(obj, target_width, target_height)
    
    if scale_x > 1000 or scale_y > 1000:
        result['warnings'].append("Very large scale factors - object will become huge")
    
    if scale_x < 0.001 or scale_y < 0.001:
        result['warnings'].append("Very small scale factors - object will become tiny")
    
    # If we got here, basic validation passed
    result['valid'] = True
    result['can_proceed'] = len(result['errors']) == 0
    
    return result

def calculate_aspect_ratio(width: int, height: int) -> float:
    """
    Calculate aspect ratio from dimensions
    
    Args:
        width: Width value
        height: Height value
    
    Returns:
        Aspect ratio (width/height)
    """
    if height == 0:
        return 1.0
    return width / height

def preserve_aspect_ratio_scaling(obj, target_size: float, dimension: str = 'larger') -> bool:
    """
    Scale object preserving aspect ratio based on one dimension
    
    Args:
        obj: Blender object
        target_size: Target size for the specified dimension
        dimension: Which dimension to use ('larger', 'smaller', 'width', 'height')
    
    Returns:
        True if scaling was successful
    """
    if not obj or obj.type != 'MESH':
        return False
    
    try:
        current_dims = obj.dimensions.copy()
        
        if dimension == 'larger':
            reference_dim = max(current_dims.x, current_dims.y)
        elif dimension == 'smaller':
            reference_dim = min(current_dims.x, current_dims.y)
        elif dimension == 'width':
            reference_dim = current_dims.x
        elif dimension == 'height':
            reference_dim = current_dims.y
        else:
            return False
        
        if reference_dim == 0:
            return False
        
        scale_factor = target_size / reference_dim
        
        obj.scale.x *= scale_factor
        obj.scale.y *= scale_factor
        
        bpy.context.view_layer.update()
        return True
        
    except Exception as e:
        print(f"Error in aspect ratio scaling: {e}")
        return False

def get_texture_density(obj, tex_width: int, tex_height: int) -> dict:
    """
    Calculate texture density (pixels per Blender unit)
    
    Args:
        obj: Blender object
        tex_width: Texture width in pixels
        tex_height: Texture height in pixels
    
    Returns:
        Dictionary with density information
    """
    density_info = {
        'pixels_per_unit_x': 0,
        'pixels_per_unit_y': 0,
        'avg_pixels_per_unit': 0,
        'valid': False
    }
    
    if not obj or obj.type != 'MESH':
        return density_info
    
    try:
        dims = obj.dimensions.copy()
        
        if dims.x > 0 and dims.y > 0:
            density_info['pixels_per_unit_x'] = tex_width / dims.x
            density_info['pixels_per_unit_y'] = tex_height / dims.y
            density_info['avg_pixels_per_unit'] = (
                density_info['pixels_per_unit_x'] + 
                density_info['pixels_per_unit_y']
            ) / 2
            density_info['valid'] = True
            
    except Exception as e:
        print(f"Error calculating texture density: {e}")
    
    return density_info

# Export main functions
__all__ = [
    'pixels_to_blender_units',
    'blender_units_to_pixels',
    'calculate_real_world_size',
    'calculate_scale_factors',
    'apply_texture_scaling',
    'get_object_texture_scale_info',
    'validate_scaling_parameters',
    'calculate_aspect_ratio',
    'preserve_aspect_ratio_scaling',
    'get_texture_density',
]
