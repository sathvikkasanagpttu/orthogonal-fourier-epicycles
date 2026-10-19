#!/usr/bin/env python3
"""Build the complete Fourier World Atlas: Countries, Continents, and World.

Transforms Natural Earth vector boundary datasets into a lightweight,
projection-corrected, multi-ring Fourier coefficient atlas.
Outputs:
  - web/public/atlas/index.json
  - web/public/atlas/maps/<ISO_A3>.json
  - web/public/atlas/world.json
  - web/public/atlas/continents/<id>.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fourier import (
    compute_coefficients,
    compute_contour_error,
    reconstruct_2d,
    sort_harmonics_by_amplitude,
    to_amplitude_phase,
)
from src.geometry import (
    calculate_ring_area,
    extract_all_rings_from_geometry,
    filter_and_sort_rings,
    normalize_multi_ring,
    simplify_ring,
)
from src.outline import clean_contour, resample_arc_length
from src.projections import project_coordinates

# Output directories
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
WEB_ATLAS_DIR = PROJECT_ROOT / "web" / "public" / "atlas"
MAPS_DIR = WEB_ATLAS_DIR / "maps"
CONTINENTS_DIR = WEB_ATLAS_DIR / "continents"


def process_ring_to_fourier(
    coords: np.ndarray,
    ring_id: int,
    area_ratio: float,
    max_N: int = 1000,
) -> Dict[str, Any]:
    """Process a single 2D polygon ring into its Fourier series representation and error curve."""
    cleaned = clean_contour(coords)

    # Adaptive M and N based on ring size
    if area_ratio > 0.15:
        M = 4096
        N_target = min(max_N, 1000)
    elif area_ratio > 0.02:
        M = 2048
        N_target = min(max_N, 500)
    elif area_ratio > 0.005:
        M = 1024
        N_target = min(max_N, 200)
    else:
        M = 512
        N_target = min(max_N, 100)

    xr, yr = resample_arc_length(cleaned, M=M)
    t = np.linspace(0.0, 2.0 * math.pi, M, endpoint=False)

    (a0, c0), a, b, c, d = compute_coefficients(xr, yr, N_harmonics=N_target)
    order_x, order_y = sort_harmonics_by_amplitude(a, b, c, d)
    Rx, phix = to_amplitude_phase(a, b)
    Ry, phiy = to_amplitude_phase(c, d)

    # Compute error table across sweep N
    test_ns = [1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000]
    test_ns = [n for n in test_ns if n <= N_target]
    if N_target not in test_ns:
        test_ns.append(N_target)

    error_table = {}
    for n in test_ns:
        x_rec, y_rec = reconstruct_2d(t, (a0, c0), a, b, c, d, N=n, sort_by_amplitude=True)
        err = compute_contour_error(xr, yr, x_rec, y_rec)["mean_error_pct"]
        error_table[str(n)] = round(err, 4)

    # Subsample ground truth for lightweight vector preview
    stride = max(1, M // 512)
    x_sub = [round(float(v), 5) for v in xr[::stride]]
    y_sub = [round(float(v), 5) for v in yr[::stride]]

    return {
        "ring_id": ring_id,
        "area_ratio": round(float(area_ratio), 4),
        "M": M,
        "N": N_target,
        "ground_truth": {"x": x_sub, "y": y_sub},
        "error_table": error_table,
        "x_chain": {
            "a0": round(float(a0), 6),
            "a": [round(float(v), 6) for v in a],
            "b": [round(float(v), 6) for v in b],
            "R": [round(float(v), 6) for v in Rx],
            "phi": [round(float(v), 6) for v in phix],
            "order": [int(idx) for idx in order_x],
        },
        "y_chain": {
            "c0": round(float(c0), 6),
            "c": [round(float(v), 6) for v in c],
            "d": [round(float(v), 6) for v in d],
            "R": [round(float(v), 6) for v in Ry],
            "phi": [round(float(v), 6) for v in phiy],
            "order": [int(idx) for idx in order_y],
        },
    }


def build_atlas(boundary_view: str = "de_facto", max_countries: Optional[int] = None) -> None:
    """Build the complete multi-ring atlas for all countries, continents, and world."""
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    CONTINENTS_DIR.mkdir(parents=True, exist_ok=True)

    countries_file = RAW_DATA_DIR / "ne_50m_admin_0_countries.geojson"
    land_file = RAW_DATA_DIR / "ne_50m_land.geojson"

    if not countries_file.exists():
        print(f"Error: {countries_file} not found. Run scripts/fetch_data.py first.")
        sys.exit(1)

    print(f"Loading countries from: {countries_file.name}")
    with open(countries_file, "r", encoding="utf-8") as f:
        countries_data = json.load(f)

    index_entries = []
    continents_dict: Dict[str, List[dict]] = {}

    features = countries_data.get("features", [])
    if max_countries:
        features = features[:max_countries]

    total_countries = len(features)
    print(f"\nProcessing {total_countries} national boundaries...")

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})

        # Identifiers
        iso_a3 = props.get("ISO_A3", "")
        if not iso_a3 or iso_a3 == "-99":
            iso_a3 = props.get("ADM0_A3", "") or props.get("SOV_A3", f"MAP_{idx:03d}")

        name = props.get("NAME_LONG") or props.get("NAME") or iso_a3
        continent = props.get("CONTINENT", "Other")

        sys.stdout.write(f"\r  [{idx+1:3d}/{total_countries:3d}] Processing {name[:24]:<24} ({iso_a3})...")
        sys.stdout.flush()

        # Handle India sovereign boundary POV override if requested
        if iso_a3 in ("IND", "IND_POV") and boundary_view == "sovereign_in":
            sovereign_geojson = PROJECT_ROOT / "data" / "india_outline.geojson"
            if sovereign_geojson.exists():
                with open(sovereign_geojson, "r", encoding="utf-8") as gf:
                    ind_d = json.load(gf)
                    geom = ind_d["features"][0]["geometry"]

        # Extract all exterior rings
        raw_rings = extract_all_rings_from_geometry(geom)
        if not raw_rings:
            continue

        # Project coordinates (local equirectangular by default)
        center_lon = float(props.get("LABEL_X", np.mean(raw_rings[0][:, 0])))
        center_lat = float(props.get("LABEL_Y", np.mean(raw_rings[0][:, 1])))

        proj_rings = [
            project_coordinates(r, projection_name="equirectangular", center_lon=center_lon, center_lat=center_lat)
            for r in raw_rings
        ]

        # Simplify rings slightly to eliminate micro-jitter
        tol = 0.003
        simplified_rings = [simplify_ring(r, tolerance=tol) for r in proj_rings]

        # Sort and filter rings
        filtered_rings = filter_and_sort_rings(simplified_rings, detail_level="all", min_area_ratio=0.002, max_rings=15)
        if not filtered_rings:
            continue

        # Shared bounding box normalization
        norm_rings, (cx, cy, max_span) = normalize_multi_ring(filtered_rings)

        all_norm_pts = np.vstack(norm_rings)
        span_x = float(all_norm_pts[:, 0].max() - all_norm_pts[:, 0].min())
        span_y = float(all_norm_pts[:, 1].max() - all_norm_pts[:, 1].min())
        aspect = round(span_x / max(1e-6, span_y), 3)

        # Process each ring into Fourier components
        areas = [calculate_ring_area(r) for r in norm_rings]
        tot_area = sum(areas) if sum(areas) > 0 else 1.0

        ring_payloads = []
        for r_idx, r_coords in enumerate(norm_rings):
            a_ratio = areas[r_idx] / tot_area
            payload = process_ring_to_fourier(r_coords, ring_id=r_idx, area_ratio=a_ratio, max_N=1000)
            ring_payloads.append(payload)

        # Map document
        map_doc = {
            "id": iso_a3,
            "name": name,
            "continent": continent,
            "centroid": [round(center_lon, 3), round(center_lat, 3)],
            "aspect": aspect,
            "ring_count": len(ring_payloads),
            "rings": ring_payloads,
        }

        map_path = MAPS_DIR / f"{iso_a3}.json"
        with open(map_path, "w", encoding="utf-8") as f_out:
            json.dump(map_doc, f_out, separators=(",", ":"))

        # Add to index
        index_entry = {
            "id": iso_a3,
            "name": name,
            "continent": continent,
            "aspect": aspect,
            "ring_count": len(ring_payloads),
            "centroid": [round(center_lon, 2), round(center_lat, 2)],
            "file": f"maps/{iso_a3}.json",
            "best_error": ring_payloads[0]["error_table"].get("1000", 0.02),
        }
        index_entries.append(index_entry)

        # Collect for continent compilation
        if continent not in continents_dict:
            continents_dict[continent] = []
        continents_dict[continent].extend(filtered_rings)

    print("\nNational maps compiled successfully.")

    # -------------------------------------------------------------------------
    # World Map Compilation (from ne_50m_land.geojson)
    # -------------------------------------------------------------------------
    if land_file.exists():
        print("\nProcessing World Landmasses (Equal Earth projection)...")
        with open(land_file, "r", encoding="utf-8") as f:
            land_data = json.load(f)

        world_rings = []
        for lf in land_data.get("features", []):
            world_rings.extend(extract_all_rings_from_geometry(lf.get("geometry", {})))

        # Project via Equal Earth
        proj_world = [project_coordinates(r, projection_name="equal_earth") for r in world_rings]
        simp_world = [simplify_ring(r, tolerance=0.04) for r in proj_world]
        filtered_world = filter_and_sort_rings(simp_world, detail_level="large", min_area_ratio=0.005, max_rings=20)
        norm_world, _ = normalize_multi_ring(filtered_world)

        world_areas = [calculate_ring_area(r) for r in norm_world]
        tot_w_area = sum(world_areas) or 1.0

        world_ring_payloads = [
            process_ring_to_fourier(r, ring_id=i, area_ratio=world_areas[i]/tot_w_area, max_N=1000)
            for i, r in enumerate(norm_world)
        ]

        world_doc = {
            "id": "WORLD",
            "name": "World (All Land)",
            "continent": "Global",
            "aspect": 2.05,
            "ring_count": len(world_ring_payloads),
            "rings": world_ring_payloads,
        }
        with open(WEB_ATLAS_DIR / "world.json", "w", encoding="utf-8") as wf:
            json.dump(world_doc, wf, separators=(",", ":"))

        # Prepend World to index
        index_entries.insert(0, {
            "id": "WORLD",
            "name": "World (All Land)",
            "continent": "Global",
            "aspect": 2.05,
            "ring_count": len(world_ring_payloads),
            "centroid": [0.0, 0.0],
            "file": "world.json",
            "best_error": world_ring_payloads[0]["error_table"].get("1000", 0.05),
        })
        print("World map compiled successfully.")

    # -------------------------------------------------------------------------
    # Continent Compilations
    # -------------------------------------------------------------------------
    print("\nProcessing Continental Boundaries...")
    continent_slugs = {
        "Africa": "africa",
        "Asia": "asia",
        "Europe": "europe",
        "North America": "north-america",
        "South America": "south-america",
        "Oceania": "oceania",
        "Antarctica": "antarctica",
    }

    for cont_name, slug in continent_slugs.items():
        if cont_name in continents_dict and continents_dict[cont_name]:
            cont_rings = filter_and_sort_rings(continents_dict[cont_name], detail_level="large", min_area_ratio=0.008, max_rings=15)
            norm_c_rings, _ = normalize_multi_ring(cont_rings)
            c_areas = [calculate_ring_area(r) for r in norm_c_rings]
            tot_c_area = sum(c_areas) or 1.0

            c_payloads = [
                process_ring_to_fourier(r, ring_id=i, area_ratio=c_areas[i]/tot_c_area, max_N=1000)
                for i, r in enumerate(norm_c_rings)
            ]

            c_doc = {
                "id": f"CONT_{slug.upper()}",
                "name": f"Continent: {cont_name}",
                "continent": cont_name,
                "aspect": 1.2,
                "ring_count": len(c_payloads),
                "rings": c_payloads,
            }
            c_path = CONTINENTS_DIR / f"{slug}.json"
            with open(c_path, "w", encoding="utf-8") as cf:
                json.dump(c_doc, cf, separators=(",", ":"))

            index_entries.insert(1, {
                "id": f"CONT_{slug.upper()}",
                "name": f"Continent: {cont_name}",
                "continent": "Continents",
                "aspect": 1.2,
                "ring_count": len(c_payloads),
                "centroid": [0.0, 0.0],
                "file": f"continents/{slug}.json",
                "best_error": c_payloads[0]["error_table"].get("1000", 0.05),
            })

    # Save index.json
    index_path = WEB_ATLAS_DIR / "index.json"
    with open(index_path, "w", encoding="utf-8") as f_idx:
        json.dump(index_entries, f_idx, indent=2)

    index_size_kb = index_path.stat().st_size / 1024.0
    print(f"\nSaved atlas index to {index_path} ({index_size_kb:.1f} KB, {len(index_entries)} total maps)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Fourier World Atlas")
    parser.add_argument("--boundary-view", choices=["de_facto", "sovereign_in"], default="de_facto")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of countries (for quick testing)")
    args = parser.parse_args()
    build_atlas(boundary_view=args.boundary_view, max_countries=args.limit)
