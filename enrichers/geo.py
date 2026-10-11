"""
Geospatial and distance calculation utilities.
Uses Haversine formula and Japanese real estate 80m/min walking standard.
"""
import math
from typing import Tuple, Dict, Any, Optional

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in meters.
    """
    r = 6371000 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c

def walking_minutes(meters: float) -> int:
    """
    Japan standard: 80 meters per minute (walk time).
    """
    if meters <= 0:
        return 1
    return max(1, math.ceil(meters / 80.0))

def compute_distance_info(
    origin_lat: float, origin_lng: float,
    target_lat: Optional[float], target_lng: Optional[float],
    fallback_distance_meters: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes precise distance and walking minutes.
    If coordinates are missing, falls back to parsed distance string.
    """
    if target_lat is not None and target_lng is not None:
        dist_m = int(round(haversine_distance(origin_lat, origin_lng, target_lat, target_lng)))
    elif fallback_distance_meters is not None:
        dist_m = fallback_distance_meters
    else:
        dist_m = 500 # reasonable default

    walk_mins = walking_minutes(dist_m)
    return {
        "distance_meters": dist_m,
        "walking_minutes": walk_mins
    }
