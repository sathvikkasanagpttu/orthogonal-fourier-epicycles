"""Cartographic projection engines for country, continental, and global map boundaries.

Provides:
  - Local Equirectangular (scaled by cos(mean_latitude))
  - Lambert Azimuthal Equal-Area (LAEA centered on country centroid)
  - Equal Earth & Robinson projections for World and Continent maps
"""

from __future__ import annotations

import math
from typing import Optional, Tuple, Union

import numpy as np

try:
    import pyproj
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False


def project_local_equirectangular(
    coords: np.ndarray,
    center_lon: Optional[float] = None,
    center_lat: Optional[float] = None,
) -> np.ndarray:
    """Project lon/lat coordinates onto a conformal local equirectangular plane.

    Args:
        coords: Array of shape (K, 2) in decimal degrees [lon, lat].
        center_lon: Reference longitude in degrees. If None, uses mean of coords.
        center_lat: Reference latitude in degrees. If None, uses mean of coords.

    Returns:
        np.ndarray of shape (K, 2) in normalized Cartesian coordinates.
    """
    pts = np.asarray(coords, dtype=np.float64)
    lons = pts[:, 0]
    lats = pts[:, 1]

    if center_lon is None:
        center_lon = float(np.mean(lons))
    if center_lat is None:
        center_lat = float(np.mean(lats))

    # Convert center latitude to radians for aspect scaling
    phi0 = math.radians(center_lat)
    cos_phi0 = math.cos(phi0)
    if abs(cos_phi0) < 1e-6:
        cos_phi0 = 1e-6  # Prevent division by zero near poles

    # x = (lon - lon0) * cos(lat0), y = lat - lat0 (all in degrees)
    x = (lons - center_lon) * cos_phi0
    y = lats - center_lat
    return np.column_stack([x, y])


def project_lambert_equal_area(
    coords: np.ndarray,
    center_lon: Optional[float] = None,
    center_lat: Optional[float] = None,
) -> np.ndarray:
    """Project lon/lat coordinates using Lambert Azimuthal Equal-Area (LAEA).

    Preserves true relative area across all continental and national scales.
    Uses pyproj if available, with an analytic closed-form spherical fallback.
    """
    pts = np.asarray(coords, dtype=np.float64)
    lons = pts[:, 0]
    lats = pts[:, 1]

    if center_lon is None:
        center_lon = float(np.mean(lons))
    if center_lat is None:
        center_lat = float(np.mean(lats))

    if HAS_PYPROJ:
        try:
            proj = pyproj.Proj(proj="laea", lat_0=center_lat, lon_0=center_lon, datum="WGS84")
            x, y = proj(lons, lats)
            return np.column_stack([x, y])
        except Exception:
            pass

    # Analytic closed-form spherical LAEA fallback
    lam = np.radians(lons)
    phi = np.radians(lats)
    lam0 = math.radians(center_lon)
    phi0 = math.radians(center_lat)

    dlam = lam - lam0
    denom = 1.0 + np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(dlam)
    # Clip denom to avoid division by zero or negative near antipode
    denom = np.clip(denom, 1e-8, 2.0)
    k_prime = np.sqrt(2.0 / denom)

    x = k_prime * np.cos(phi) * np.sin(dlam)
    y = k_prime * (np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(dlam))
    return np.column_stack([x, y])


def project_equal_earth(coords: np.ndarray) -> np.ndarray:
    """Project coordinates using the Equal Earth projection (suitable for World / Continents)."""
    pts = np.asarray(coords, dtype=np.float64)
    lons = pts[:, 0]
    lats = pts[:, 1]

    if HAS_PYPROJ:
        try:
            proj = pyproj.Proj(proj="eqearth", datum="WGS84")
            x, y = proj(lons, lats)
            return np.column_stack([x, y])
        except Exception:
            pass

    # Closed-form Equal Earth equations (Šavrič et al. 2018)
    lam = np.radians(lons)
    phi = np.radians(lats)

    A1 = 1.340264
    A2 = -0.081106
    A3 = 0.000893
    A4 = 0.003796
    M = np.sqrt(3.0) / 2.0

    theta = np.arcsin(M * np.sin(phi))
    theta2 = theta * theta
    theta6 = theta2 * theta2 * theta2
    theta8 = theta6 * theta2

    num_x = 2.0 * np.sqrt(3.0) * lam * np.cos(theta)
    den_x = 3.0 * (9.0 * A4 * theta8 + 7.0 * A3 * theta6 + 3.0 * A2 * theta2 + A1)
    x = num_x / den_x
    y = theta * (A1 + A2 * theta2 + A3 * theta6 + A4 * theta8)

    return np.column_stack([x, y])


def project_coordinates(
    coords: np.ndarray,
    projection_name: str = "equirectangular",
    center_lon: Optional[float] = None,
    center_lat: Optional[float] = None,
) -> np.ndarray:
    """Universal dispatcher for cartographic projections."""
    name = projection_name.lower().strip()
    if name in ("equirectangular", "local", "plate_carree"):
        return project_local_equirectangular(coords, center_lon, center_lat)
    elif name in ("laea", "lambert", "equal_area"):
        return project_lambert_equal_area(coords, center_lon, center_lat)
    elif name in ("equal_earth", "world", "continents"):
        return project_equal_earth(coords)
    elif name in ("robinson",):
        if HAS_PYPROJ:
            try:
                proj = pyproj.Proj(proj="robin", datum="WGS84")
                return np.column_stack(proj(coords[:, 0], coords[:, 1]))
            except Exception:
                pass
        return project_equal_earth(coords)
    else:
        return project_local_equirectangular(coords, center_lon, center_lat)
