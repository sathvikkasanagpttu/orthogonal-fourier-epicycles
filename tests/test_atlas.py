"""Integration test suite validating atlas compilation, index structure, and reconstruction."""

import json
from pathlib import Path
import numpy as np
import pytest

from src.fourier import compute_contour_error, reconstruct_2d

ATLAS_DIR = Path(__file__).resolve().parent.parent / "web" / "public" / "atlas"
INDEX_PATH = ATLAS_DIR / "index.json"


def test_atlas_index_schema():
    """Verify atlas index contains required keys and valid entries."""
    assert INDEX_PATH.exists(), "atlas/index.json is missing!"

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    assert len(entries) >= 200, f"Expected >= 200 maps, got {len(entries)}"

    required_keys = {"id", "name", "continent", "aspect", "ring_count", "centroid", "file"}
    for entry in entries:
        missing = required_keys - set(entry.keys())
        assert not missing, f"Entry {entry.get('id')} missing keys: {missing}"
        assert entry["ring_count"] >= 1


def test_representative_maps_reconstruction():
    """Verify Fourier reconstruction error on representative nations (IND, USA, JPN, BRA, CHL)."""
    target_ids = ["IND", "USA", "JPN", "BRA", "CHL", "WORLD"]

    for map_id in target_ids:
        map_path = ATLAS_DIR / "world.json" if map_id == "WORLD" else ATLAS_DIR / "maps" / f"{map_id}.json"
        if not map_path.exists():
            continue

        with open(map_path, "r", encoding="utf-8") as f:
            map_data = json.load(f)

        r0 = map_data["rings"][0]
        N_max = r0["N"]

        # Reconstruct largest ring
        t_eval = np.linspace(0.0, 2 * np.pi, 512, endpoint=False)
        a0 = r0["x_chain"]["a0"]
        c0 = r0["y_chain"]["c0"]
        a = np.array(r0["x_chain"]["a"])
        b = np.array(r0["x_chain"]["b"])
        c = np.array(r0["y_chain"]["c"])
        d = np.array(r0["y_chain"]["d"])

        xr, yr = reconstruct_2d(t_eval, (a0, c0), a, b, c, d, N=N_max, sort_by_amplitude=True)

        gt_x = np.array(r0["ground_truth"]["x"])
        gt_y = np.array(r0["ground_truth"]["y"])

        err = compute_contour_error(gt_x, gt_y, xr, yr)["mean_error_pct"]
        assert err < 0.2, f"Reconstruction error for {map_id} is too high: {err:.3f}%"
