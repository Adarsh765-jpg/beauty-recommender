"""Vercel serverless entrypoint for the recommendation API.

Routes must carry the full ``/api`` prefix: Vercel routes any request under
``/api`` to this function without stripping the path segment.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from fastapi import FastAPI

BOOT_TIME = time.time()

app = FastAPI(
    title="Beauty Recommender API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "beauty-recommender",
        "version": "0.1.0",
        "python": sys.version.split()[0],
        "region": os.environ.get("VERCEL_REGION", "local"),
        "uptime_seconds": round(time.time() - BOOT_TIME, 3),
    }
