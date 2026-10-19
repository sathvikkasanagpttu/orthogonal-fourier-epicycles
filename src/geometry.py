"""Geospatial geometry utilities: antimeridian unwrapping, multi-ring decomposition, and simplification.

Features:
  - Antimeridian unwrapping for Russia, Alaska, Fiji, Kiribati (prevents seam slicing)
  - Multi-part polygon extraction (islands, archipelagos, exclaves)
  - Detail-level filtering: 'main' (largest only), 'large' (significant islands), 'all'
  - Shared bounding box normalization across multiple rings (preserves geographic relative placement)
  - Douglas-Peucker simplification tailored to feature scale
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

import numpy as np
from shapely.geometry import MultiPolygon, Polygon


def unwrap_antimeridian(coords: np.ndarray) -> np.ndarray:
    """Unwrap coordinates that cross the 180° antimeridian to ensure spatial continuity.

    Detects longitudinal jumps greater than 180° and adjusts adjacent coordinates
    by ±360° so that the boundary does not erroneously slash across the globe.

    Args:
        coords: Array of shape (K, 2) with columns [lon, lat].

    Returns:
        np.ndarray of shape (K, 2) with continuous longitudes.
    """
    pts = np.asarray(coords, dtype=np.float64).copy()
    if len(pts) < 2:
        return pts

    lons = pts[:, 0]
    unwrapped_lons = np.empty_like(lons)
    unwrapped_lons[0] = lons[0]

    offset = 0.0
    for i in range(1, len(lons)):
        diff = (lons[i] + offset) - unwrapped_lons[i - 1]
        if diff > 180.0:
            offset -= 360.0
        elif diff < -180.0:
            offset += 360.0
        unwrapped_lons[i] = lons[i] + offset

    pts[:, 0] = unwrapped_lons
    return pts


def calculate_ring_area(coords: np.ndarray) -> float:
    """Compute enclosed area of a 2D planar polygon ring using the Shoelace formula."""
    pts = np.asarray(coords, dtype=np.float64)
    if len(pts) < 3:
        return 0.0
    x, y = pts[:, 0], pts[:, 1]
    return float(0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def extract_all_rings_from_geometry(geom: dict) -> List[np.ndarray]:
    """Extract all exterior polygon rings from a GeoJSON geometry dictionary.

    Args:
        geom: GeoJSON geometry dictionary (Polygon or MultiPolygon).

    Returns:
        List of np.ndarray arrays of shape (K, 2) in [lon, lat].
    """
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    raw_rings = []

    if gtype == "Polygon" and coords:
        # coords[0] is the exterior boundary ring
        raw_rings.append(np.asarray(coords[0], dtype=np.float64))
    elif gtype == "MultiPolygon" and coords:
        for poly_coords in coords:
            if poly_coords and len(poly_coords[0]) >= 3:
                raw_rings.append(np.asarray(poly_coords[0], dtype=np.float64))
    elif gtype == "GeometryCollection":
        for sub_geom in geom.get("geometries", []):
            raw_rings.extend(extract_all_rings_from_geometry(sub_geom))

    # Unwrap antimeridian on every ring
    unwrapped_rings = []
    for ring in raw_rings:
        clean_ring = unwrap_antimeridian(ring)
        unwrapped_rings.append(clean_ring)

    return unwrapped_rings


def simplify_ring(coords: np.ndarray, tolerance: float = 0.01) -> np.ndarray:
    """Simplify polygon ring using Douglas-Peucker algorithm while preserving topology."""
    pts = np.asarray(coords, dtype=np.float64)
    if len(pts) <= 10 or tolerance <= 0:
        return pts

    try:
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        simplified = poly.simplify(tolerance, preserve_topology=True)
        if simplified.is_empty:
            return pts
        if hasattr(simplified, "exterior"):
            return np.asarray(simplified.exterior.coords, dtype=np.float64)
        elif hasattr(simplified, "geoms") and simplified.geoms:
            largest = max(simplified.geoms, key=lambda p: p.area)
            return np.asarray(largest.exterior.coords, dtype=np.float64)
    except Exception:
        pass

    return pts


def filter_and_sort_rings(
    rings: List[np.ndarray],
    detail_level: str = "large",
    min_area_ratio: float = 0.002,
    max_rings: int = 15,
) -> List[np.ndarray]:
    """Filter and sort polygon rings by area for multi-ring reconstruction.

    Args:
        rings: List of projected rings (each shape (K, 2)).
        detail_level: 'main' (largest only), 'large' (major islands/exclaves), 'all'.
        min_area_ratio: Minimum ratio of total country area a ring must possess.
        max_rings: Maximum ring count limit to ensure high frame rates.

    Returns:
        List of filtered polygon rings sorted by descending area.
    """
    if not rings:
        return []

    # Calculate areas
    areas = [calculate_ring_area(r) for r in rings]
    total_area = sum(areas)
    if total_area <= 0:
        return [rings[0]]

    # Pair each ring with its area and sort descending
    sorted_pairs = sorted(zip(rings, areas), key=lambda x: x[1], reverse=True)

    if detail_level == "main":
        return [sorted_pairs[0][0]]

    filtered_rings = []
    for r, a in sorted_pairs:
        if detail_level == "all":
            if a >= total_area * (min_area_ratio * 0.1) or len(filtered_rings) == 0:
                filtered_rings.append(r)
        else:  # "large" (default)
            if a >= total_area * min_area_ratio or len(filtered_rings) == 0:
                filtered_rings.append(r)
        if len(filtered_rings) >= max_rings:
            break

    return filtered_rings


def normalize_multi_ring(
    rings: List[np.ndarray],
) -> Tuple[List[np.ndarray], Tuple[float, float, float]]:
    """Normalize multiple rings sharing a unified bounding box centered at (0, 0).

    Preserves exact relative geographic positions, spacing, and scales between islands.

    Args:
        rings: List of projected coordinate arrays (each shape (K, 2)).

    Returns:
        Tuple of:
          - normalized_rings: List of normalized rings in [-0.5, 0.5] unit box.
          - metadata: (global_cx, global_cy, global_max_span)
    """
    if not rings:
        raise ValueError("Cannot normalize an empty list of rings.")

    all_pts = np.vstack(rings)
    min_x, max_x = np.min(all_pts[:, 0]), np.max(all_pts[:, 0])
    min_y, max_y = np.min(all_pts[:, 1]), np.max(all_pts[:, 1])

    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    max_span = max(max_x - min_x, max_y - min_y)
    if max_span <= 0:
        max_span = 1.0

    normalized_rings = [
        np.column_stack([(r[:, 0] - cx) / max_span, (r[:, 1] - cy) / max_span])
        for r in rings
    ]
    return normalized_rings, (cx, cy, max_span)
