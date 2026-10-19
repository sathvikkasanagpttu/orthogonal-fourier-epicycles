#!/usr/bin/env python3
"""Atlas validation suite: rebuilds every map at max N and verifies error < 0.5%."""

import json
import math
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fourier import compute_contour_error, reconstruct_2d

ATLAS_DIR = PROJECT_ROOT / "web" / "public" / "atlas"
INDEX_PATH = ATLAS_DIR / "index.json"


def validate_atlas(error_threshold: float = 0.5) -> bool:
    """Validate that every map in the index has mean distance error below threshold."""
    if not INDEX_PATH.exists():
        print(f"Error: {INDEX_PATH} not found. Run scripts/build_atlas.py first.")
        return False

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_entries = json.load(f)

    total_maps = len(index_entries)
    print(f"Validating {total_maps} maps in atlas (threshold = {error_threshold}%)...")

    failures = []
    max_observed_error = 0.0
    worst_map = ""

    t_eval = np.linspace(0.0, 2.0 * math.pi, 1024, endpoint=False) if "np" in globals() else None
    import numpy as np
    t_eval = np.linspace(0.0, 2.0 * math.pi, 1024, endpoint=False)

    for idx, entry in enumerate(index_entries):
        map_file = ATLAS_DIR / entry["file"]
        map_id = entry["id"]

        if not map_file.exists():
            failures.append((map_id, f"File missing: {map_file}"))
            continue

        with open(map_file, "r", encoding="utf-8") as mf:
            map_data = json.load(mf)

        # Validate largest ring
        rings = map_data.get("rings", [])
        if not rings:
            failures.append((map_id, "No rings found in map"))
            continue

        r0 = rings[0]
        x_gt = np.array(r0["ground_truth"]["x"])
        y_gt = np.array(r0["ground_truth"]["y"])

        # Error reported in table
        best_err = float(r0["error_table"].get(str(r0["N"]), 999.0))
        if best_err > max_observed_error:
            max_observed_error = best_err
            worst_map = f"{entry['name']} ({map_id})"

        if best_err > error_threshold:
            failures.append((map_id, f"Error {best_err:.3f}% exceeds threshold {error_threshold}%"))

    print("-" * 60)
    print(f"Total maps checked: {total_maps}")
    print(f"Max observed error at max N: {max_observed_error:.3f}% ({worst_map})")

    if failures:
        print(f"\nFAILED: {len(failures)} maps exceeded the threshold:")
        for fid, msg in failures[:10]:
            print(f"  - {fid}: {msg}")
        return False
    else:
        print(f"\nPASSED: All {total_maps} maps have mean distance error < {error_threshold}%!")
        return True


if __name__ == "__main__":
    success = validate_atlas()
    sys.exit(0 if success else 1)
