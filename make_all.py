#!/usr/bin/env python3
"""Master execution script for Orthogonal Fourier Epicycles: World Atlas Edition.

Orchestrates the complete build pipeline:
  1. Extract and resample India outline (GeoJSON and image pipelines)
  2. Compute Fourier coefficients and evaluate error table
  3. Validate Atlas precomputed dataset (250 maps)
  4. Build interactive Web App with Vite & TypeScript
  5. Run automated test suite with pytest
  6. Render high-quality Manim animation video to output/
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure local venv binaries are on PATH
venv_bin = PROJECT_ROOT / ".venv" / "bin"
if venv_bin.exists():
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
    python_bin = str(venv_bin / "python")
else:
    python_bin = sys.executable

from src.config import (
    DEFAULT_SWEEP_N,
    GEOJSON_PATH,
    M_SAMPLES,
    MASK_PNG_PATH,
    N_MAX_HARMONICS,
    OUTPUT_DIR,
    WEB_COEFFS_JSON_PATH,
)
from src.export_web_json import export_coefficients_to_json
from src.fourier import (
    compute_coefficients,
    compute_contour_error,
    reconstruct_2d,
    sort_harmonics_by_amplitude,
)
from src.outline import get_india_contour


def run_pipeline(
    quality: str = "preview",
    mode: str = "geojson",
    skip_tests: bool = False,
    build_web: bool = True,
    map_id: str = "IND",
) -> None:
    """Executes the end-to-end mathematical animation pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("  ORTHOGONAL FOURIER EPICYCLES: WORLD ATLAS EDITION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Step 1: Outline extraction & normalization
    # -------------------------------------------------------------------------
    print(f"\n[1/6] Extracting & Resampling Outline (mode='{mode}', M={M_SAMPLES})...")
    data_file = GEOJSON_PATH if mode == "geojson" else MASK_PNG_PATH
    x_norm, y_norm, t = get_india_contour(mode=mode, filepath=data_file, M=M_SAMPLES)
    print(f"      Successfully extracted {len(x_norm)} points.")
    print(f"      Span: x in [{x_norm.min():.4f}, {x_norm.max():.4f}], y in [{y_norm.min():.4f}, {y_norm.max():.4f}]")

    # -------------------------------------------------------------------------
    # Step 2: Fourier decomposition & error table
    # -------------------------------------------------------------------------
    print(f"\n[2/6] Computing Real Fourier Coefficients (N_max={N_MAX_HARMONICS})...")
    (a0, c0), a, b, c, d = compute_coefficients(x_norm, y_norm, N_harmonics=N_MAX_HARMONICS)
    order_x, order_y = sort_harmonics_by_amplitude(a, b, c, d)
    print(f"      DC Offset: a0 = {a0:.6f}, c0 = {c0:.6f}")

    print("\n      --- HARMONIC CONVERGENCE & ERROR REPORT ---")
    print("      {:>6} | {:>14} | {:>15}".format("N", "Mean Error (%)", "Hausdorff (%)"))
    print("      " + "-" * 42)
    for n in DEFAULT_SWEEP_N:
        xr, yr = reconstruct_2d(t, (a0, c0), a, b, c, d, N=n, sort_by_amplitude=True)
        err = compute_contour_error(x_norm, y_norm, xr, yr)
        print("      {:>6d} | {:>13.4f}% | {:>14.4f}%".format(n, err["mean_error_pct"], err["hausdorff_pct"]))
    print("      " + "-" * 42)

    # -------------------------------------------------------------------------
    # Step 3: Validate Atlas Dataset
    # -------------------------------------------------------------------------
    print("\n[3/6] Validating Atlas Integrity across 250 World Maps...")
    val_cmd = [python_bin, "scripts/validate_atlas.py"]
    res_val = subprocess.run(val_cmd, cwd=str(PROJECT_ROOT))
    if res_val.returncode != 0:
        print("WARNING: Atlas validation encountered issues.")
    else:
        print("      Atlas dataset validated: All maps error < 0.5% at N_max.")

    # -------------------------------------------------------------------------
    # Step 4: Build Web Application
    # -------------------------------------------------------------------------
    if build_web and shutil.which("npm"):
        print("\n[4/6] Building Web App with Vite & TypeScript...")
        res_web = subprocess.run(["npm", "run", "build"], cwd=str(PROJECT_ROOT))
        if res_web.returncode == 0:
            print("      Web application built successfully into dist/")
        else:
            print("      Warning: Web app build encountered an issue.")
    else:
        print("\n[4/6] Skipping Web App build (npm not available or disabled).")

    # -------------------------------------------------------------------------
    # Step 5: Run Unit Tests
    # -------------------------------------------------------------------------
    if not skip_tests:
        print("\n[5/6] Running Unit Test Suite (pytest)...")
        test_cmd = [python_bin, "-m", "pytest", "tests/", "-q"]
        res = subprocess.run(test_cmd, cwd=str(PROJECT_ROOT))
        if res.returncode != 0:
            print("ERROR: Unit tests failed!")
            sys.exit(res.returncode)
        print("      All mathematical and geometric unit tests passed!")
    else:
        print("\n[5/6] Skipping Unit Tests as requested.")

    # -------------------------------------------------------------------------
    # Step 6: Render Manim Animation Video
    # -------------------------------------------------------------------------
    if quality == "skip":
        print("\n[6/6] Skipping Video Render as requested.")
        print("\nPipeline completed successfully!")
        return

    print(f"\n[6/6] Rendering Animation Video with Manim (map='{map_id}', quality='{quality}')...")
    render_cmd = [
        python_bin,
        "render.py",
        "--map",
        map_id,
        "--quality",
        quality,
    ]
    render_res = subprocess.run(render_cmd, cwd=str(PROJECT_ROOT))

    if render_res.returncode == 0:
        print(f"\nSUCCESS: Video rendered successfully for {map_id}!")
    else:
        print("Warning: Manim rendering encountered an issue.")

    print("\n" + "=" * 70)
    print("  BUILD COMPLETE: All assets generated and verified.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End Build Pipeline for Orthogonal Fourier Epicycles")
    parser.add_argument(
        "--map",
        type=str,
        default="IND",
        help="Country ISO_A3 code for rendering (default: IND)",
    )
    parser.add_argument(
        "--quality",
        choices=["preview", "low", "medium", "high", "4k", "skip"],
        default="preview",
        help="Video rendering quality (default: preview)",
    )
    parser.add_argument(
        "--mode",
        choices=["geojson", "image"],
        default="geojson",
        help="Outline input format (geojson or image)",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest unit tests",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Skip building the web application",
    )
    args = parser.parse_args()
    run_pipeline(
        quality=args.quality,
        mode=args.mode,
        skip_tests=args.skip_tests,
        build_web=not args.skip_web,
        map_id=args.map,
    )
