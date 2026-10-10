from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as api_router
from app.config import settings
from app.services.dashboard_auth import authentication_configured, token_subject

app = FastAPI(
    title="UrbanMind AI",
    version="1.0.0",
    description="UrbanMind AI prediction, digital twin simulation, Pareto optimization, explainability, and urban memory services.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )


app.include_router(api_router)


@app.middleware("http")
async def dashboard_authentication(request: Request, call_next: Any) -> Any:
    path = request.url.path
    public_paths = {"/api/v1/auth/config", "/api/v1/auth/login"}
    if (
        request.method != "OPTIONS"
        and path.startswith("/api/v1/")
        and path not in public_paths
        and settings.AUTH_REQUIRED
    ):
        if not authentication_configured():
            return JSONResponse(
                status_code=503,
                content={"detail": "Dashboard authentication is required but not configured."},
            )
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        subject = token_subject(token) if scheme.lower() == "bearer" else None
        if subject is None:
            return JSONResponse(status_code=401, content={"detail": "A valid bearer token is required."})
        request.state.authenticated_user = subject
    response = await call_next(request)
    return response


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "project": "UrbanMind AI",
        "status": "ready",
        "phase": "PHASE 13 — Explainability and decision pipeline",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "UrbanMind AI"}


@app.get("/ready")
async def readiness() -> dict[str, str]:
    return {"status": "ready", "service": "UrbanMind AI"}
