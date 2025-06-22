# utils/__init__.py - Utils Package Initialization

"""
Enhanced TextureAide Utils Package

This package contains utility modules for:
- File system operations (file_utils.py)
- UDIM-specific utilities (udim_utils.py) 
- Texture scaling mathematics (scaling_utils.py)
"""

# Import main utility functions for easy access
from .file_utils import (
    get_image_dimensions,
    validate_udim_path,
    scan_udim_directory,
    get_supported_image_formats,
    PIL_AVAILABLE
)

from .udim_utils import (
    parse_udim_number,
    create_udim_number,
    find_udim_files,
    get_udim_range
)

from .scaling_utils import (
    pixels_to_blender_units,
    calculate_real_world_size,
    apply_texture_scaling,
    validate_scaling_parameters
)

# Package version
__version__ = "2.1.0"

# Export commonly used functions
__all__ = [
    # File utilities
    'get_image_dimensions',
    'validate_udim_path', 
    'scan_udim_directory',
    'get_supported_image_formats',
    'PIL_AVAILABLE',
    
    # UDIM utilities
    'parse_udim_number',
    'create_udim_number',
    'find_udim_files',
    'get_udim_range',
    
    # Scaling utilities
    'pixels_to_blender_units',
    'calculate_real_world_size',
    'apply_texture_scaling',
    'validate_scaling_parameters',
]