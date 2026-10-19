"""Export Fourier coefficients and outline data to web/coefficients.json for the interactive web viewer."""

import json
from pathlib import Path
import numpy as np

from .config import (
    DEFAULT_SWEEP_N,
    GEOJSON_PATH,
    M_SAMPLES,
    N_MAX_HARMONICS,
    WEB_COEFFS_JSON_PATH,
    WEB_DIR,
)
from .fourier import (
    compute_coefficients,
    compute_contour_error,
    reconstruct_2d,
    sort_harmonics_by_amplitude,
    to_amplitude_phase,
)
from .outline import get_india_contour


def export_coefficients_to_json(
    output_path: Path = WEB_COEFFS_JSON_PATH,
    N_max: int = N_MAX_HARMONICS,
    M: int = M_SAMPLES,
) -> Path:
    """Precompute and serialize Fourier series parameters and error tables for client-side rendering."""
    print("Extracting India outline...")
    x_norm, y_norm, t = get_india_contour(mode="geojson", filepath=GEOJSON_PATH, M=M)

    print(f"Computing Fourier series coefficients up to N = {N_max}...")
    (a0, c0), a, b, c, d = compute_coefficients(x_norm, y_norm, N_harmonics=N_max)

    print("Sorting harmonics by descending amplitude...")
    order_x, order_y = sort_harmonics_by_amplitude(a, b, c, d)
    R_x, phi_x = to_amplitude_phase(a, b)
    R_y, phi_y = to_amplitude_phase(c, d)

    print("Precomputing error curve table...")
    test_n_values = [1, 2, 3, 5, 10, 20, 25, 50, 100, 200, 300, 500, 750, 1000]
    error_table = {}
    for n in test_n_values:
        xr, yr = reconstruct_2d(t, (a0, c0), a, b, c, d, N=n, sort_by_amplitude=True)
        err = compute_contour_error(x_norm, y_norm, xr, yr)["mean_error_pct"]
        error_table[str(n)] = round(err, 4)

    # Subsample ground truth points for lightweight JSON delivery (e.g. 1024 points for fast web rendering)
    stride = max(1, M // 1024)
    x_sampled = [round(float(v), 5) for v in x_norm[::stride]]
    y_sampled = [round(float(v), 5) for v in y_norm[::stride]]

    payload = {
        "metadata": {
            "title": "Orthogonal Fourier Epicycles - India Outline",
            "M_samples": M,
            "N_harmonics": N_max,
            "center": [round(a0, 6), round(c0, 6)],
        },
        "ground_truth": {
            "x": x_sampled,
            "y": y_sampled,
        },
        "error_table": error_table,
        "x_chain": {
            "a0": round(float(a0), 6),
            "a": [round(float(v), 6) for v in a],
            "b": [round(float(v), 6) for v in b],
            "R": [round(float(v), 6) for v in R_x],
            "phi": [round(float(v), 6) for v in phi_x],
            "order": [int(idx) for idx in order_x],
        },
        "y_chain": {
            "c0": round(float(c0), 6),
            "c": [round(float(v), 6) for v in c],
            "d": [round(float(v), 6) for v in d],
            "R": [round(float(v), 6) for v in R_y],
            "phi": [round(float(v), 6) for v in phi_y],
            "order": [int(idx) for idx in order_y],
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))

    size_kb = output_path.stat().st_size / 1024.0
    print(f"Exported JSON successfully to {output_path} ({size_kb:.1f} KB)")
    return output_path


if __name__ == "__main__":
    export_coefficients_to_json()
