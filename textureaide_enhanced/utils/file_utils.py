# utils/file_utils.py - File System Operations

import os
import re
from typing import Dict, List, Tuple, Optional, Union
import bpy

# Try to import PIL for better image format support
try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def get_image_dimensions(filepath: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Get image dimensions from file
    
    Args:
        filepath: Path to image file
    
    Returns:
        Tuple of (width, height) or (None, None) if failed
    """
    if not os.path.exists(filepath):
        return None, None
    
    try:
        if PIL_AVAILABLE:
            # Use PIL for better format support
            with PILImage.open(filepath) as img:
                return img.width, img.height
        else:
            # Fallback: use Blender's image loader
            # Note: This temporarily loads the image into Blender
            temp_image = bpy.data.images.load(filepath, check_existing=False)
            width, height = temp_image.size
            bpy.data.images.remove(temp_image)
            return width, height
            
    except Exception as e:
        print(f"Could not read image dimensions from {filepath}: {e}")
        return None, None

def validate_udim_path(filepath: str) -> bool:
    """
    Validate if a filepath could contain UDIM sequences
    
    Args:
        filepath: Path to check
    
    Returns:
        True if path could contain UDIMs
    """
    if not filepath:
        return False
    
    # Check if file contains UDIM patterns
    udim_patterns = [
        r'<UDIM>',           # Mari/Blender format
        r'\d{4}',            # 1001, 1002 format
        r'u\d+_v\d+',        # u1_v1 format
    ]
    
    basename = os.path.basename(filepath)
    
    for pattern in udim_patterns:
        if re.search(pattern, basename):
            return True
    
    return False

def scan_udim_directory(base_filepath: str) -> Dict[int, Dict[str, Union[str, int]]]:
    """
    Scan directory for UDIM files and return their information
    
    Args:
        base_filepath: Base path with UDIM pattern (e.g., "/path/texture_<UDIM>.exr")
    
    Returns:
        Dictionary mapping UDIM numbers to file information
        {1001: {'filepath': '...', 'filename': '...', 'width': 4096, 'height': 4096}}
    """
    udim_files = {}
    
    if not base_filepath:
        return udim_files
    
    # Resolve Blender's relative paths
    abs_path = bpy.path.abspath(base_filepath)
    directory = os.path.dirname(abs_path)
    
    if not os.path.exists(directory):
        print(f"Directory does not exist: {directory}")
        return udim_files
    
    try:
        basename = os.path.basename(abs_path)
        
        if '<UDIM>' in basename:
            # Handle <UDIM> pattern (e.g., "texture_<UDIM>.exr")
            udim_files = _scan_udim_pattern(directory, basename)
        else:
            # Try to detect UDIM numbers in existing filename
            udim_files = _scan_numeric_pattern(directory, basename)
            
    except Exception as e:
        print(f"Error scanning UDIM directory {directory}: {e}")
    
    return udim_files

def _scan_udim_pattern(directory: str, basename: str) -> Dict[int, Dict[str, Union[str, int]]]:
    """Scan directory using <UDIM> pattern"""
    udim_files = {}
    
    # Create regex pattern from filename
    file_pattern = basename.replace('<UDIM>', r'(\d{4})')
    regex = re.compile(file_pattern)
    
    try:
        for filename in os.listdir(directory):
            match = regex.match(filename)
            if match:
                udim_number = int(match.group(1))
                
                # Validate UDIM number range
                if 1001 <= udim_number <= 1100:
                    filepath = os.path.join(directory, filename)
                    width, height = get_image_dimensions(filepath)
                    
                    udim_files[udim_number] = {
                        'filepath': filepath,
                        'filename': filename,
                        'width': width or 0,
                        'height': height or 0,
                        'exists': True
                    }
    except OSError as e:
        print(f"Error reading directory {directory}: {e}")
    
    return udim_files

def _scan_numeric_pattern(directory: str, basename: str) -> Dict[int, Dict[str, Union[str, int]]]:
    """Scan directory for files with UDIM numbers"""
    udim_files = {}
    
    # Look for 4-digit numbers that could be UDIMs
    udim_pattern = re.compile(r'(\d{4})')
    
    try:
        for filename in os.listdir(directory):
            # Check if filename has similar pattern to basename
            if _files_similar_pattern(basename, filename):
                matches = udim_pattern.findall(filename)
                
                for match in matches:
                    udim_number = int(match)
                    
                    # Check if it's in valid UDIM range
                    if 1001 <= udim_number <= 1100:
                        filepath = os.path.join(directory, filename)
                        width, height = get_image_dimensions(filepath)
                        
                        udim_files[udim_number] = {
                            'filepath': filepath,
                            'filename': filename, 
                            'width': width or 0,
                            'height': height or 0,
                            'exists': True
                        }
                        break  # Only use first valid UDIM number found
                        
    except OSError as e:
        print(f"Error reading directory {directory}: {e}")
    
    return udim_files

def _files_similar_pattern(basename: str, filename: str) -> bool:
    """Check if two filenames have similar patterns (ignoring UDIM numbers)"""
    # Remove UDIM numbers and compare structure
    base_clean = re.sub(r'\d{4}', 'XXXX', basename)
    file_clean = re.sub(r'\d{4}', 'XXXX', filename)
    
    return base_clean == file_clean

def get_supported_image_formats() -> List[str]:
    """Get list of supported image file extensions"""
    # Common image formats supported by Blender and PIL
    formats = [
        '.exr', '.hdr', '.tiff', '.tif', '.png', '.jpg', '.jpeg',
        '.tga', '.bmp', '.cin', '.dpx', '.psd', '.jp2'
    ]
    
    if PIL_AVAILABLE:
        # PIL supports additional formats
        formats.extend(['.webp', '.ico', '.pcx', '.ppm', '.pgm', '.pbm'])
    
    return sorted(set(formats))

def filter_image_files(file_list: List[str]) -> List[str]:
    """Filter list to only include supported image files"""
    supported_formats = get_supported_image_formats()
    
    filtered_files = []
    for filepath in file_list:
        _, ext = os.path.splitext(filepath.lower())
        if ext in supported_formats:
            filtered_files.append(filepath)
    
    return filtered_files

def get_file_info(filepath: str) -> Dict[str, Union[str, int, bool]]:
    """
    Get comprehensive file information
    
    Args:
        filepath: Path to file
    
    Returns:
        Dictionary with file information
    """
    info = {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'exists': os.path.exists(filepath),
        'size_bytes': 0,
        'width': 0,
        'height': 0,
        'format': 'unknown'
    }
    
    if info['exists']:
        try:
            info['size_bytes'] = os.path.getsize(filepath)
            
            width, height = get_image_dimensions(filepath)
            info['width'] = width or 0
            info['height'] = height or 0
            
            _, ext = os.path.splitext(filepath)
            info['format'] = ext.lower().lstrip('.')
            
        except Exception as e:
            print(f"Error getting file info for {filepath}: {e}")
    
    return info

# Export main functions
__all__ = [
    'get_image_dimensions',
    'validate_udim_path', 
    'scan_udim_directory',
    'get_supported_image_formats',
    'filter_image_files',
    'get_file_info',
    'PIL_AVAILABLE',
]
