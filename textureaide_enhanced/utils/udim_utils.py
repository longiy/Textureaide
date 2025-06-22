# utils/udim_utils.py - UDIM-Specific Utilities

import os
from typing import Dict, List, Tuple, Optional, Set
from .file_utils import scan_udim_directory, validate_udim_path

def parse_udim_number(udim: int) -> Tuple[int, int]:
    """
    Parse UDIM number into U and V tile coordinates
    
    Args:
        udim: UDIM number (e.g., 1001, 1002, 1011)
    
    Returns:
        Tuple of (U, V) coordinates
    
    Example:
        1001 -> (0, 0)
        1002 -> (1, 0)  
        1011 -> (0, 1)
    """
    if udim < 1001:
        raise ValueError(f"Invalid UDIM number: {udim}. Must be >= 1001")
    
    # UDIM formula: 1001 + U + (V * 10)
    # So: udim - 1001 = U + (V * 10)
    offset = udim - 1001
    u = offset % 10
    v = offset // 10
    
    return (u, v)

def create_udim_number(u: int, v: int) -> int:
    """
    Create UDIM number from U and V tile coordinates
    
    Args:
        u: U coordinate (0-9)
        v: V coordinate (0+)
    
    Returns:
        UDIM number
    
    Example:
        (0, 0) -> 1001
        (1, 0) -> 1002
        (0, 1) -> 1011
    """
    if u < 0 or u > 9:
        raise ValueError(f"U coordinate must be 0-9, got {u}")
    if v < 0:
        raise ValueError(f"V coordinate must be >= 0, got {v}")
    
    return 1001 + u + (v * 10)

def generate_udim_sequence(start_udim: int = 1001, count: int = 10) -> List[int]:
    """
    Generate a sequence of UDIM numbers
    
    Args:
        start_udim: Starting UDIM number
        count: Number of UDIMs to generate
    
    Returns:
        List of UDIM numbers
    """
    udims = []
    u, v = parse_udim_number(start_udim)
    
    for i in range(count):
        current_u = (u + i) % 10
        current_v = v + ((u + i) // 10)
        udims.append(create_udim_number(current_u, current_v))
    
    return udims

def find_udim_files(image_path: str) -> Dict[int, Dict]:
    """
    Find all UDIM files for a given image path
    
    Args:
        image_path: Path to image with UDIM pattern
    
    Returns:
        Dictionary mapping UDIM numbers to file info
    """
    if not validate_udim_path(image_path):
        return {}
    
    return scan_udim_directory(image_path)

def get_udim_range(udim_files: Dict[int, Dict]) -> Tuple[int, int]:
    """
    Get the range of UDIM numbers present
    
    Args:
        udim_files: Dictionary from find_udim_files()
    
    Returns:
        Tuple of (min_udim, max_udim)
    """
    if not udim_files:
        return (1001, 1001)
    
    udim_numbers = list(udim_files.keys())
    return (min(udim_numbers), max(udim_numbers))

def get_udim_gaps(udim_files: Dict[int, Dict]) -> List[int]:
    """
    Find missing UDIM numbers in a sequence
    
    Args:
        udim_files: Dictionary from find_udim_files()
    
    Returns:
        List of missing UDIM numbers
    """
    if not udim_files:
        return []
    
    min_udim, max_udim = get_udim_range(udim_files)
    expected_udims = set(range(min_udim, max_udim + 1))
    actual_udims = set(udim_files.keys())
    
    return sorted(list(expected_udims - actual_udims))

def sort_udims_by_resolution(udim_files: Dict[int, Dict], descending: bool = True) -> List[int]:
    """
    Sort UDIM numbers by their resolution (total pixels)
    
    Args:
        udim_files: Dictionary from find_udim_files()
        descending: If True, sort from largest to smallest
    
    Returns:
        List of UDIM numbers sorted by resolution
    """
    def get_pixel_count(udim_info):
        return udim_info.get('width', 0) * udim_info.get('height', 0)
    
    # Create list of (udim_number, pixel_count) tuples
    udim_resolutions = []
    for udim_num, udim_info in udim_files.items():
        pixel_count = get_pixel_count(udim_info)
        udim_resolutions.append((udim_num, pixel_count))
    
    # Sort by pixel count
    udim_resolutions.sort(key=lambda x: x[1], reverse=descending)
    
    # Return just the UDIM numbers
    return [udim_num for udim_num, _ in udim_resolutions]

def select_optimal_udim(udim_files: Dict[int, Dict], mode: str) -> Optional[int]:
    """
    Select the optimal UDIM based on specified criteria
    
    Args:
        udim_files: Dictionary from find_udim_files()
        mode: Selection mode ('FIRST', 'LARGEST', 'SMALLEST')
    
    Returns:
        Selected UDIM number or None if no files
    """
    if not udim_files:
        return None
    
    if mode == 'FIRST':
        # Return the lowest UDIM number
        return min(udim_files.keys())
    
    elif mode == 'LARGEST':
        # Return UDIM with highest resolution
        sorted_udims = sort_udims_by_resolution(udim_files, descending=True)
        return sorted_udims[0] if sorted_udims else None
    
    elif mode == 'SMALLEST':
        # Return UDIM with lowest resolution
        sorted_udims = sort_udims_by_resolution(udim_files, descending=False)
        return sorted_udims[0] if sorted_udims else None
    
    else:
        # Default to first
        return min(udim_files.keys())

def get_udim_from_index(udim_files: Dict[int, Dict], index: int) -> Optional[int]:
    """
    Get UDIM number from list index
    
    Args:
        udim_files: Dictionary from find_udim_files()
        index: Index in sorted UDIM list
    
    Returns:
        UDIM number at index or None if invalid
    """
    if not udim_files:
        return None
    
    sorted_udims = sorted(udim_files.keys())
    
    if 0 <= index < len(sorted_udims):
        return sorted_udims[index]
    
    return None

def validate_udim_sequence(udim_files: Dict[int, Dict]) -> Dict[str, any]:
    """
    Validate UDIM sequence and provide optimization suggestions
    
    Args:
        udim_files: Dictionary from find_udim_files()
    
    Returns:
        Validation result with errors, warnings, and suggestions
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'suggestions': []
    }
    
    if not udim_files:
        result['valid'] = False
        result['errors'].append("No UDIM files found")
        return result
    
    # Check for missing files
    gaps = get_udim_gaps(udim_files)
    if gaps:
        result['warnings'].append(f"Missing UDIM tiles: {gaps}")
        result['suggestions'].append("Consider filling gaps or using non-sequential UDIMs")
    
    # Check resolution consistency
    resolutions = set()
    for udim_info in udim_files.values():
        width = udim_info.get('width', 0)
        height = udim_info.get('height', 0)
        if width > 0 and height > 0:
            resolutions.add((width, height))
    
    if len(resolutions) > 1:
        result['warnings'].append("Inconsistent resolutions across UDIM tiles")
        result['suggestions'].append("Consider standardizing all tiles to same resolution")
    
    # Check for very large textures
    for udim_num, udim_info in udim_files.items():
        width = udim_info.get('width', 0)
        height = udim_info.get('height', 0)
        if width > 8192 or height > 8192:
            result['warnings'].append(f"UDIM {udim_num} has very high resolution: {width}x{height}")
            result['suggestions'].append("Consider using lower resolution for better performance")
    
    # Check for missing files on disk
    missing_files = []
    for udim_num, udim_info in udim_files.items():
        if not udim_info.get('exists', True):
            missing_files.append(udim_num)
    
    if missing_files:
        result['errors'].append(f"UDIM files missing on disk: {missing_files}")
        result['valid'] = False
    
    # Suggestions for optimization
    if len(udim_files) > 20:
        result['suggestions'].append("Large UDIM sequence - consider texture atlasing")
    
    sorted_by_size = sort_udims_by_resolution(udim_files, descending=True)
    if len(sorted_by_size) > 1:
        largest = sorted_by_size[0]
        result['suggestions'].append(f"UDIM {largest} has highest resolution - good for detail scaling")
    
    return result

def get_udim_statistics(udim_files: Dict[int, Dict]) -> Dict[str, any]:
    """
    Get statistical information about UDIM sequence
    
    Args:
        udim_files: Dictionary from find_udim_files()
    
    Returns:
        Dictionary with statistics
    """
    if not udim_files:
        return {
            'count': 0,
            'total_pixels': 0,
            'avg_resolution': (0, 0),
            'min_resolution': (0, 0),
            'max_resolution': (0, 0),
            'udim_range': (1001, 1001),
            'gaps': [],
            'file_sizes': []
        }
    
    # Collect data
    resolutions = []
    total_pixels = 0
    file_sizes = []
    
    for udim_info in udim_files.values():
        width = udim_info.get('width', 0)
        height = udim_info.get('height', 0)
        resolutions.append((width, height))
        total_pixels += width * height
        
        # File size if available
        filepath = udim_info.get('filepath', '')
        if filepath and os.path.exists(filepath):
            try:
                size = os.path.getsize(filepath)
                file_sizes.append(size)
            except:
                pass
    
    # Calculate statistics
    if resolutions:
        widths = [r[0] for r in resolutions]
        heights = [r[1] for r in resolutions]
        
        avg_width = sum(widths) // len(widths)
        avg_height = sum(heights) // len(heights)
        
        min_width, min_height = min(resolutions)
        max_width, max_height = max(resolutions)
    else:
        avg_width = avg_height = 0
        min_width = min_height = 0
        max_width = max_height = 0
    
    return {
        'count': len(udim_files),
        'total_pixels': total_pixels,
        'avg_resolution': (avg_width, avg_height),
        'min_resolution': (min_width, min_height),
        'max_resolution': (max_width, max_height),
        'udim_range': get_udim_range(udim_files),
        'gaps': get_udim_gaps(udim_files),
        'total_file_size': sum(file_sizes) if file_sizes else 0,
        'avg_file_size': sum(file_sizes) // len(file_sizes) if file_sizes else 0
    }

# Export main functions
__all__ = [
    'parse_udim_number',
    'create_udim_number',
    'generate_udim_sequence',
    'find_udim_files',
    'get_udim_range',
    'get_udim_gaps',
    'sort_udims_by_resolution',
    'select_optimal_udim',
    'get_udim_from_index',
    'validate_udim_sequence',
    'get_udim_statistics',
]