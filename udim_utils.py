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
        return udim_info.get('width', 0) * udim_info.get('height', 0# utils/udim_utils.py - UDIM-Specific Utilities

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
    offset = udim