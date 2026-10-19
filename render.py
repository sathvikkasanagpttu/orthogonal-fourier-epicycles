#!/usr/bin/env python3
"""CLI tool for rendering Orthogonal Fourier Epicycles animations with Manim.

Usage Examples:
    python render.py --map IND --quality preview
    python render.py --map JPN --detail large --quality low
    python render.py --map WLD --detail main --quality medium
    python render.py --map USA --n-sweep --quality low
    python render.py --all --quality preview
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

QUALITY_FLAGS = {
    "preview": "-ql",
    "low": "-ql",
    "medium": "-qm",
    "high": "-qh",
    "4k": "-qk",
}

SHOWCASE_COUNTRIES = [
    "IND",  # India (Showcase)
    "JPN",  # Japan (Archipelago)
    "USA",  # United States
    "FRA",  # France (Hexagon)
    "NOR",  # Norway (Fractal fjords)
    "WLD",  # World (All land)
]


def render_map(
    map_id: str,
    quality: str = "preview",
    detail: str = "all",
    n_sweep: bool = False,
    active_n: int = 120,
    media_dir: str = "output/videos",
) -> int:
    """Render a single map using Manim."""
    flag = QUALITY_FLAGS.get(quality, "-ql")
    output_dir = ROOT_DIR / media_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["ATLAS_MAP_ID"] = map_id
    env["ATLAS_DETAIL"] = detail
    env["ATLAS_N_SWEEP"] = "1" if n_sweep else "0"
    env["PYTHONPATH"] = str(ROOT_DIR)

    scene_file = ROOT_DIR / "src" / "atlas_scene.py"
    scene_name = "AtlasEpicyclesScene"

    venv_python = ROOT_DIR / ".venv" / "bin" / "python"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    cmd = [
        python_bin,
        "-m",
        "manim",
        flag,
        "--media_dir",
        str(output_dir),
        str(scene_file),
        scene_name,
    ]

    print(f"\n=======================================================")
    print(f"🎬 Rendering {map_id} [Quality: {quality}, Detail: {detail}, Sweep: {n_sweep}]")
    print(f"Command: {' '.join(cmd)}")
    print(f"=======================================================\n")

    res = subprocess.run(cmd, env=env, cwd=str(ROOT_DIR))
    return res.returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render Orthogonal Fourier Epicycles animations for any country using Manim."
    )
    parser.add_argument(
        "--map",
        type=str,
        default="IND",
        help="Country ISO_A3 code (e.g. IND, USA, JPN, FRA, NOR, WLD) or name (default: IND).",
    )
    parser.add_argument(
        "--quality",
        type=str,
        default="preview",
        choices=["preview", "low", "medium", "high", "4k"],
        help="Render quality (default: preview).",
    )
    parser.add_argument(
        "--detail",
        type=str,
        default="all",
        choices=["main", "large", "all"],
        help="Detail level for multi-part shapes (default: all).",
    )
    parser.add_argument(
        "--n-sweep",
        action="store_true",
        help="Animate a harmonic sweep from low N to high N.",
    )
    parser.add_argument(
        "--active-n",
        type=int,
        default=120,
        help="Harmonics count N for fixed-N animation (default: 120).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Batch render a showcase of diverse world shapes (IND, JPN, USA, FRA, NOR, WLD).",
    )
    parser.add_argument(
        "--media-dir",
        type=str,
        default="output/videos",
        help="Output directory for rendered video files (default: output/videos).",
    )

    args = parser.parse_args()

    if args.all:
        print(f"🚀 Batch rendering showcase of {len(SHOWCASE_COUNTRIES)} maps...")
        failed = []
        for mid in SHOWCASE_COUNTRIES:
            code = render_map(
                map_id=mid,
                quality=args.quality,
                detail=args.detail,
                n_sweep=args.n_sweep,
                active_n=args.active_n,
                media_dir=args.media_dir,
            )
            if code != 0:
                failed.append(mid)
        if failed:
            print(f"\n❌ Batch render finished with errors in: {failed}")
            sys.exit(1)
        else:
            print(f"\n✅ All {len(SHOWCASE_COUNTRIES)} showcase videos rendered successfully!")
            sys.exit(0)
    else:
        code = render_map(
            map_id=args.map,
            quality=args.quality,
            detail=args.detail,
            n_sweep=args.n_sweep,
            active_n=args.active_n,
            media_dir=args.media_dir,
        )
        sys.exit(code)


if __name__ == "__main__":
    main()
