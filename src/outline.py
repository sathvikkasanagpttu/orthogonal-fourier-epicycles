"""Contour extraction, cleaning, arc-length resampling, and normalization.

Provides two input pipelines:
  1. GeoJSON: loads geospatial polygons and extracts the largest exterior boundary ring.
  2. Raster Image: loads binary silhouette, runs OpenCV contour detection, and flips y.

The output is a clean, closed, uniformly arc-length parameterized curve (x(t), y(t))
scaled to a unit box centered at the origin, with t in [0, 2π).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np


def load_geojson_outline(filepath: Union[str, Path]) -> np.ndarray:
    """Extract the largest exterior polygon boundary ring from a GeoJSON file.

    Args:
        filepath: Path to the GeoJSON file containing Polygon or MultiPolygon features.

    Returns:
        np.ndarray of shape (K, 2) containing coordinate pairs [lon, lat].

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If no valid polygon coordinates are found in the GeoJSON.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"GeoJSON outline file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    polygons = []

    def _extract_from_geometry(geom: dict) -> None:
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])
        if gtype == "Polygon" and coords:
            # coords[0] is the exterior ring
            polygons.append(np.asarray(coords[0], dtype=np.float64))
        elif gtype == "MultiPolygon" and coords:
            for poly in coords:
                if poly:
                    polygons.append(np.asarray(poly[0], dtype=np.float64))
        elif gtype == "GeometryCollection":
            for g in geom.get("geometries", []):
                _extract_from_geometry(g)

    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            geom = feature.get("geometry")
            if geom:
                _extract_from_geometry(geom)
    elif data.get("type") == "Feature":
        geom = data.get("geometry")
        if geom:
            _extract_from_geometry(geom)
    elif "coordinates" in data:
        _extract_from_geometry(data)

    if not polygons:
        raise ValueError(f"No polygon rings could be extracted from: {path}")

    # Estimate ring area via Shoelace formula to select the primary mainland
    def _shoelace_area(pts: np.ndarray) -> float:
        x, y = pts[:, 0], pts[:, 1]
        return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

    largest_ring = max(polygons, key=_shoelace_area)
    return largest_ring


def load_image_outline(filepath: Union[str, Path], threshold: int = 127) -> np.ndarray:
    """Extract the largest contour from a black-and-white silhouette image using OpenCV.

    Flips the vertical axis so that positive y points upwards (cartesian coordinate system),
    matching standard mathematical orientation.

    Args:
        filepath: Path to the image file.
        threshold: Binarization threshold value (0-255).

    Returns:
        np.ndarray of shape (K, 2) containing [x, y] coordinates.

    Raises:
        FileNotFoundError: If the image file cannot be read.
        ValueError: If no contours are detected in the image.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Image outline file not found at: {path}")

    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"OpenCV could not decode image at: {path}")

    # Binary thresholding: ensure silhouette is white (255) on black (0)
    _, binary = cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)

    # Invert if the image background is light
    # Check four corners to determine background polarity
    h, w = binary.shape
    corners = [binary[0, 0], binary[0, w - 1], binary[h - 1, 0], binary[h - 1, w - 1]]
    if np.mean(corners) > 127:
        binary = cv2.bitwise_not(binary)

    # Find external contours with full point precision
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise ValueError(f"No contours found in image: {path}")

    # Find largest contour by enclosing area
    largest_contour = max(contours, key=cv2.contourArea)
    pts = largest_contour.squeeze().astype(np.float64)  # Shape (K, 2), columns [x, y]

    if pts.ndim != 2 or pts.shape[0] < 3:
        raise ValueError("Detected contour has insufficient points.")

    # Flip y so cartesian upwards is positive
    pts[:, 1] = float(h) - pts[:, 1]
    return pts


def clean_contour(points: np.ndarray, tol: float = 1e-7) -> np.ndarray:
    """Deduplicate consecutive points and ensure strict curve closure.

    Args:
        points: Input contour array of shape (K, 2).
        tol: Euclidean distance tolerance below which adjacent points are merged.

    Returns:
        np.ndarray of shape (P, 2) with deduplicated points where points[0] == points[-1].
    """
    pts = np.asarray(points, dtype=np.float64)
    if pts.shape[0] < 3:
        raise ValueError("Contour must contain at least 3 points.")

    # Remove consecutive duplicate or near-duplicate points
    diffs = np.diff(pts, axis=0)
    dists = np.hypot(diffs[:, 0], diffs[:, 1])
    keep = np.insert(dists > tol, 0, True)
    clean_pts = pts[keep]

    # Ensure curve is strictly closed (first point == last point)
    start_end_dist = np.hypot(clean_pts[0, 0] - clean_pts[-1, 0], clean_pts[0, 1] - clean_pts[-1, 1])
    if start_end_dist > tol:
        clean_pts = np.vstack([clean_pts, clean_pts[0]])

    return clean_pts


def resample_arc_length(points: np.ndarray, M: int = 8192) -> Tuple[np.ndarray, np.ndarray]:
    """Resample a closed parametric curve uniformly by arc length.

    Uses cumulative euclidean chord-length parametrization and piecewise linear
    interpolation to ensure that the parameter t is proportional to distance traveled.

    Args:
        points: Array of shape (K, 2) representing the closed contour.
        M: Number of output resampled vertices.

    Returns:
        Tuple of (x, y) arrays, each of length M, uniformly sampled along the perimeter.
    """
    pts = np.asarray(points, dtype=np.float64)
    diffs = np.diff(pts, axis=0)
    segment_lengths = np.hypot(diffs[:, 0], diffs[:, 1])
    cumulative_length = np.insert(np.cumsum(segment_lengths), 0, 0.0)
    total_perimeter = cumulative_length[-1]

    if total_perimeter <= 0.0:
        raise ValueError("Contour perimeter must be strictly positive.")

    # Uniformly spaced target arc lengths in [0, total_perimeter)
    # endpoint=False ensures periodic boundary conditions: index 0 and index M wrap smoothly
    target_lengths = np.linspace(0.0, total_perimeter, M, endpoint=False)

    x_resampled = np.interp(target_lengths, cumulative_length, pts[:, 0])
    y_resampled = np.interp(target_lengths, cumulative_length, pts[:, 1])

    return x_resampled, y_resampled


def normalize_contour(
    x: np.ndarray, y: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[float, float, float]]:
    """Center contour at the origin and scale to fit inside a unit box [-0.5, 0.5].

    Preserves aspect ratio identically across both axes.

    Args:
        x: Raw x-coordinates of length M.
        y: Raw y-coordinates of length M.

    Returns:
        Tuple of:
          - x_norm: Normalized x-coordinates of length M.
          - y_norm: Normalized y-coordinates of length M.
          - t: Parameter array in [0, 2π) of length M, t[i] = 2π * i / M.
          - metadata: (center_x, center_y, max_span) for inverse projection if needed.
    """
    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    span_x = max_x - min_x
    span_y = max_y - min_y
    max_span = max(span_x, span_y)

    if max_span <= 0:
        raise ValueError("Contour has zero spatial extent.")

    # Shift to center at (0, 0) and scale to unit dimension
    x_norm = (x - center_x) / max_span
    y_norm = (y - center_y) / max_span

    M = len(x)
    t = np.linspace(0.0, 2.0 * np.pi, M, endpoint=False)

    return x_norm, y_norm, t, (center_x, center_y, max_span)


def get_india_contour(
    mode: str = "geojson",
    filepath: Union[str, Path, None] = None,
    M: int = 8192,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convenience pipeline to load, clean, resample, and normalize India's outline.

    Args:
        mode: Either 'geojson' or 'image'.
        filepath: Optional path to data file; defaults to config paths.
        M: Number of arc-length sample vertices.

    Returns:
        Tuple (x_norm, y_norm, t) with x, y in [-0.5, 0.5] and t in [0, 2π).
    """
    if mode == "geojson":
        if filepath is None:
            from .config import GEOJSON_PATH
            filepath = GEOJSON_PATH
        raw_pts = load_geojson_outline(filepath)
    elif mode == "image":
        if filepath is None:
            from .config import MASK_PNG_PATH
            filepath = MASK_PNG_PATH
        raw_pts = load_image_outline(filepath)
    else:
        raise ValueError(f"Unknown mode '{mode}'. Choose 'geojson' or 'image'.")

    cleaned = clean_contour(raw_pts)
    x_res, y_res = resample_arc_length(cleaned, M=M)
    x_norm, y_norm, t, _ = normalize_contour(x_res, y_res)

    return x_norm, y_norm, t


if __name__ == "__main__":
    print("Testing outline extraction pipelines...")
    from .config import GEOJSON_PATH, MASK_PNG_PATH

    if GEOJSON_PATH.exists():
        xg, yg, tg = get_india_contour(mode="geojson", filepath=GEOJSON_PATH, M=8192)
        print(f"[GeoJSON mode] Loaded M={len(xg)} points. Bounds: x=[{xg.min():.3f}, {xg.max():.3f}], y=[{yg.min():.3f}, {yg.max():.3f}]")

    if MASK_PNG_PATH.exists():
        xi, yi, ti = get_india_contour(mode="image", filepath=MASK_PNG_PATH, M=8192)
        print(f"[Image mode]   Loaded M={len(xi)} points. Bounds: x=[{xi.min():.3f}, {xi.max():.3f}], y=[{yi.min():.3f}, {yi.max():.3f}]")

    print("Contour processing pipelines verified successfully!")
