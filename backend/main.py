"""FastAPI backend for the beauty recommendation system.

Deployed as a Vercel Service. The root ``vercel.json`` rewrites ``/api/*`` to
this service and everything else to the Next.js frontend, so both share one
origin and no CORS configuration is required.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BOOT_TIME = time.time()

app = FastAPI(
    title="Beauty Recommender API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "beauty-recommender",
        "version": "0.1.0",
        "python": sys.version.split()[0],
        "region": os.environ.get("VERCEL_REGION", "local"),
        "received_path": request.url.path,
        "uptime_seconds": round(time.time() - BOOT_TIME, 3),
    }


@app.api_route("/{full_path:path}", methods=["GET", "POST"])
def unmatched(request: Request, full_path: str) -> JSONResponse:
    """Report the path this service actually received.

    Vercel rewrites into a service are final: an unmatched route returns this
    service's own 404 rather than falling through to the frontend. Echoing the
    received path turns a silent routing mismatch into a legible one.
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": "no_route",
            "detail": "Backend service reached, but no route matched.",
            "received_path": request.url.path,
        },
    )
