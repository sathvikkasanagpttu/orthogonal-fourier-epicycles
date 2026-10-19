#!/usr/bin/env python3
"""Fetch raw Natural Earth vector boundary datasets (1:50m Admin 0 Countries & Land).

Saves to data/raw/ with local caching and offline fallback support.
"""

from __future__ import annotations

import argparse
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Remote URLs (Natural Earth Vector GeoJSON via official GitHub mirror)
URLS = {
    "countries": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson",
    "land": "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson",
}


def download_with_progress(url: str, dest_path: Path) -> None:
    """Download file with visual progress, using certifi SSL or curl fallback."""
    print(f"Downloading: {url}")
    print(f"Destination: {dest_path}")

    # Method 1: Python urllib with certifi SSL context
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "OrthogonalEpicyclesAtlas/1.0"})
        with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp, open(dest_path, "wb") as out_file:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            block_size = 65536
            while True:
                buffer = resp.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100.0
                    sys.stdout.write(f"\r  Progress: {pct:5.1f}% [{downloaded/(1024*1024):5.1f}MB]")
                    sys.stdout.flush()
        print(f"\nSaved successfully to: {dest_path} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
        return
    except Exception as e:
        print(f"\nUrllib failed ({e}), attempting curl fallback...")

    # Method 2: System curl fallback
    if shutil.which("curl"):
        res = subprocess.run(["curl", "-sL", url, "-o", str(dest_path)])
        if res.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 1000:
            print(f"Saved via curl successfully to: {dest_path} ({dest_path.stat().st_size / (1024*1024):.2f} MB)")
            return

    raise RuntimeError(f"Could not download {url}")


def fetch_all(force: bool = False) -> None:
    """Download countries and land boundaries if missing."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for key, url in URLS.items():
        filename = f"ne_50m_admin_0_{key}.geojson" if key == "countries" else f"ne_50m_{key}.geojson"
        dest = RAW_DATA_DIR / filename

        if dest.exists() and not force:
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"Dataset already cached: {dest.name} ({size_mb:.2f} MB). Use --force to re-download.")
        else:
            download_with_progress(url, dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Natural Earth geospatial datasets")
    parser.add_argument("--force", action="store_true", help="Force re-download of existing cached files")
    args = parser.parse_args()
    fetch_all(force=args.force)
