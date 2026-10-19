#!/usr/bin/env python3
"""Master execution script for Orthogonal Fourier Epicycles.

Orchestrates the complete build pipeline:
  1. Extract and resample India outline (GeoJSON and image pipelines)
  2. Compute Fourier coefficients and evaluate error table
  3. Export client-side JSON for interactive web visualizer
  4. Run automated test suite with pytest
  5. Render high-quality Manim animation video to output/
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Set project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure local venv binaries (e.g. ffmpeg) are on PATH
venv_bin = PROJECT_ROOT / ".venv" / "bin"
if venv_bin.exists():
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

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


def run_pipeline(quality: str = "high", mode: str = "geojson", skip_tests: bool = False) -> None:
    """Executes the end-to-end mathematical animation pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70)
    print("  ORTHOGONAL FOURIER EPICYCLES — END-TO-END MASTER PIPELINE")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # Step 1: Outline extraction & normalization
    # -------------------------------------------------------------------------
    print(f"\n[1/5] Extracting & Resampling Outline (mode='{mode}', M={M_SAMPLES})...")
    data_file = GEOJSON_PATH if mode == "geojson" else MASK_PNG_PATH
    x_norm, y_norm, t = get_india_contour(mode=mode, filepath=data_file, M=M_SAMPLES)
    print(f"      Successfully extracted {len(x_norm)} points.")
    print(f"      Span: x in [{x_norm.min():.4f}, {x_norm.max():.4f}], y in [{y_norm.min():.4f}, {y_norm.max():.4f}]")

    # -------------------------------------------------------------------------
    # Step 2: Fourier decomposition & error table
    # -------------------------------------------------------------------------
    print(f"\n[2/5] Computing Real Fourier Coefficients (N_max={N_MAX_HARMONICS})...")
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
    # Step 3: Export Web JSON
    # -------------------------------------------------------------------------
    print(f"\n[3/5] Exporting Web JSON -> {WEB_COEFFS_JSON_PATH}...")
    export_coefficients_to_json(WEB_COEFFS_JSON_PATH, N_max=N_MAX_HARMONICS, M=M_SAMPLES)

    # -------------------------------------------------------------------------
    # Step 4: Run Unit Tests
    # -------------------------------------------------------------------------
    if not skip_tests:
        print("\n[4/5] Running Unit Test Suite (pytest)...")
        test_cmd = [sys.executable, "-m", "pytest", "tests/test_fourier.py", "-q"]
        res = subprocess.run(test_cmd, cwd=str(PROJECT_ROOT))
        if res.returncode != 0:
            print("ERROR: Unit tests failed!")
            sys.exit(res.returncode)
        print("      All mathematical and geometric unit tests passed!")
    else:
        print("\n[4/5] Skipping Unit Tests as requested.")

    # -------------------------------------------------------------------------
    # Step 5: Render Manim Animation Video
    # -------------------------------------------------------------------------
    if quality == "skip":
        print("\n[5/5] Skipping Video Render as requested.")
        print("\nPipeline completed successfully!")
        return

    print(f"\n[5/5] Rendering Animation Video with Manim (quality='{quality}')...")
    manim_flags = {
        "preview": ["-ql", "-r", "480,854", "--fps", "15"],
        "medium": ["-qm"],
        "high": ["-qh"],
        "4k": ["-qk"],
    }.get(quality, ["-qh"])

    cmd = [
        sys.executable,
        "-m",
        "manim",
        *manim_flags,
        "src/scene.py",
        "OrthogonalEpicycles",
        "--media_dir",
        str(OUTPUT_DIR / "media"),
    ]
    print(f"      Command: {' '.join(cmd)}")
    render_res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if render_res.returncode == 0:
        # Find rendered mp4 in output/media
        rendered_files = list((OUTPUT_DIR / "media").rglob("*.mp4"))
        if rendered_files:
            latest_video = max(rendered_files, key=lambda p: p.stat().st_mtime)
            final_dst = OUTPUT_DIR / "OrthogonalFourierEpicycles_India.mp4"
            shutil.copy2(latest_video, final_dst)
            size_mb = final_dst.stat().st_size / (1024 * 1024)
            print(f"\nSUCCESS: Video saved to: {final_dst} ({size_mb:.2f} MB)")
    else:
        print("Warning: Manim rendering encountered an issue.")

    print("\n" + "=" * 70)
    print("  BUILD COMPLETE: All assets generated and verified.")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End Build Pipeline for Orthogonal Fourier Epicycles")
    parser.add_argument(
        "--quality",
        choices=["preview", "medium", "high", "4k", "skip"],
        default="preview",
        help="Video rendering quality (preview, medium, high=1080p60, 4k=2160p60, skip)",
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
    args = parser.parse_args()
    run_pipeline(quality=args.quality, mode=args.mode, skip_tests=args.skip_tests)
