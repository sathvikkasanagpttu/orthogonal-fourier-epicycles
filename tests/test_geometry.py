"""Unit tests for geometry, projections, and antimeridian unwrapping."""

import numpy as np
import pytest

from src.geometry import (
    calculate_ring_area,
    filter_and_sort_rings,
    normalize_multi_ring,
    unwrap_antimeridian,
)
from src.projections import (
    project_equal_earth,
    project_lambert_equal_area,
    project_local_equirectangular,
)


def test_unwrap_antimeridian_crosses_east_to_west():
    """Verify that a ring spanning the 180° meridian (e.g. +179° to -179°) is unwrapped without jumps."""
    # Simulates Fiji / Chukotka traversing east to west
    lons = np.array([178.0, 179.0, -179.5, -178.5, 178.0])
    lats = np.array([-16.0, -16.5, -16.8, -16.2, -16.0])
    pts = np.column_stack([lons, lats])

    unwrapped = unwrap_antimeridian(pts)

    # Maximum adjacent difference in longitude must be small, not ~360°
    max_jump = np.max(np.abs(np.diff(unwrapped[:, 0])))
    assert max_jump < 5.0, f"Antimeridian jump not unwrapped: {max_jump}"
    # Verify continuous progression
    assert unwrapped[2, 0] > 180.0, "Negative longitude should be shifted by +360°"


def test_calculate_ring_area():
    """Verify Shoelace area calculation for standard geometric shapes."""
    # Unit square: area = 1.0
    square = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])
    area = calculate_ring_area(square)
    assert np.isclose(area, 1.0, atol=1e-10)

    # Right triangle: base=2, height=3 -> area = 3.0
    triangle = np.array([[0, 0], [2, 0], [0, 3], [0, 0]])
    area_tri = calculate_ring_area(triangle)
    assert np.isclose(area_tri, 3.0, atol=1e-10)


def test_filter_and_sort_rings():
    """Verify that rings are sorted by area descending and filtered by detail level."""
    r_large = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]])  # Area 100
    r_med = np.array([[20, 20], [22, 20], [22, 22], [20, 22], [20, 20]])  # Area 4
    r_tiny = np.array([[30, 30], [30.1, 30], [30.1, 30.1], [30, 30.1], [30, 30]])  # Area 0.01

    rings = [r_med, r_tiny, r_large]

    # 'main' should return only the largest ring
    main_only = filter_and_sort_rings(rings, detail_level="main")
    assert len(main_only) == 1
    assert calculate_ring_area(main_only[0]) == 100.0

    # 'large' should filter out negligible slivers
    large_rings = filter_and_sort_rings(rings, detail_level="large", min_area_ratio=0.01)
    assert len(large_rings) == 2
    assert calculate_ring_area(large_rings[0]) == 100.0
    assert calculate_ring_area(large_rings[1]) == 4.0


def test_normalize_multi_ring():
    """Verify multi-ring normalization keeps all rings in [-0.5, 0.5] preserving relative spacing."""
    r1 = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]])
    r2 = np.array([[4, 0], [6, 0], [6, 2], [4, 2], [4, 0]])

    normed, (cx, cy, max_span) = normalize_multi_ring([r1, r2])

    assert len(normed) == 2
    all_pts = np.vstack(normed)

    assert np.all(all_pts >= -0.5001)
    assert np.all(all_pts <= 0.5001)

    # Relative distance between centers in original vs normalized must be identical up to scale
    dist_orig = 4.0  # Center 1 to center 2
    dist_norm = np.linalg.norm(np.mean(normed[1], axis=0) - np.mean(normed[0], axis=0))
    assert np.isclose(dist_norm, dist_orig / max_span, atol=1e-10)


def test_projections_finite_output():
    """Ensure projection functions map lon/lat to finite numbers without NaNs or Infs."""
    coords = np.array([
        [-120.0, 35.0],
        [0.0, 51.5],
        [77.0, 28.6],
        [139.7, 35.6],
        [175.0, -40.0],
    ])

    proj_eq = project_local_equirectangular(coords, 0.0, 20.0)
    assert np.all(np.isfinite(proj_eq))

    proj_laea = project_lambert_equal_area(coords, 0.0, 20.0)
    assert np.all(np.isfinite(proj_laea))

    proj_earth = project_equal_earth(coords)
    assert np.all(np.isfinite(proj_earth))
