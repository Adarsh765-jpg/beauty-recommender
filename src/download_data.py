"""Download Sephora dataset files into data/raw/."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve

from src.config import (
    DATA_RAW,
    GITHUB_BASE_URL,
    PRODUCT_INFO_FILENAME,
    REVIEWS_FILENAME,
)

FILES = {
    PRODUCT_INFO_FILENAME: f"{GITHUB_BASE_URL}/{PRODUCT_INFO_FILENAME}",
    REVIEWS_FILENAME: f"{GITHUB_BASE_URL}/{REVIEWS_FILENAME}",
}


def download_all(dest: Path = DATA_RAW) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for filename, url in FILES.items():
        target = dest / filename
        if target.exists():
            print(f"skip {filename} (already exists)")
            continue
        print(f"downloading {filename}...")
        urlretrieve(url, target)
        print(f"  saved {target.stat().st_size:,} bytes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Sephora dataset CSVs")
    parser.add_argument(
        "--dest",
        type=Path,
        default=DATA_RAW,
        help="Directory to write raw CSV files",
    )
    args = parser.parse_args()
    download_all(args.dest)


if __name__ == "__main__":
    main()
