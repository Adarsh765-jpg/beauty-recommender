"""FastAPI backend for the beauty recommendation system.

Deployed as a Vercel Service. The root ``vercel.json`` rewrites ``/api/*`` to
this service and everything else to the Next.js frontend, so both share one
origin and no CORS configuration is required.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.recommend_service import ArtifactsUnavailableError, recommend
from backend.schemas import ErrorResponse, RecommendRequest, RecommendResponse, supported_values
from engine.artifacts import get_artifacts

BOOT_TIME = time.time()
_ARTIFACTS_READY = False


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _ARTIFACTS_READY
    try:
        get_artifacts()
        _ARTIFACTS_READY = True
    except FileNotFoundError:
        _ARTIFACTS_READY = False
    yield


app = FastAPI(
    title="Beauty Recommender API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ()) if part != "body"),
            "message": error.get("msg", "invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    payload = ErrorResponse(
        error="validation_error",
        detail=cast(list[object], errors),
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    artifacts_ready = _ARTIFACTS_READY
    if not artifacts_ready:
        try:
            get_artifacts()
            artifacts_ready = True
        except FileNotFoundError:
            artifacts_ready = False

    return {
        "status": "ok",
        "service": "beauty-recommender",
        "version": "0.1.0",
        "python": sys.version.split()[0],
        "region": os.environ.get("VERCEL_REGION", "local"),
        "received_path": request.url.path,
        "uptime_seconds": round(time.time() - BOOT_TIME, 3),
        "artifacts_ready": artifacts_ready,
    }


@app.get("/api/schema")
def api_schema() -> dict[str, tuple[str, ...]]:
    return supported_values()


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend_endpoint(body: RecommendRequest) -> RecommendResponse | JSONResponse:
    try:
        return recommend(body)
    except ArtifactsUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="artifacts_unavailable",
                detail=str(exc),
            ).model_dump(),
        )


@app.api_route("/{full_path:path}", methods=["GET", "POST"])
def unmatched(request: Request, full_path: str) -> JSONResponse:
    """Report the path this service actually received."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="no_route",
            detail="Backend service reached, but no route matched.",
            received_path=request.url.path,
        ).model_dump(),
    )
