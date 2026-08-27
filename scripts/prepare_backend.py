"""Stage runtime packages and artifacts inside backend/ for Vercel deployment."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def prepare_backend() -> None:
    _copy_tree(REPO_ROOT / "engine", BACKEND_ROOT / "engine")

    src_dest = BACKEND_ROOT / "src"
    src_dest.mkdir(parents=True, exist_ok=True)
    for relative in ("__init__.py", "config.py"):
        source = REPO_ROOT / "src" / relative
        if not source.exists():
            raise FileNotFoundError(f"Missing backend source file: {source}")
        shutil.copy2(source, src_dest / relative)

    _copy_tree(REPO_ROOT / "data" / "artifacts", BACKEND_ROOT / "data" / "artifacts")


def main() -> None:
    prepare_backend()
    print(f"Prepared backend runtime at {BACKEND_ROOT}")


if __name__ == "__main__":
    main()
