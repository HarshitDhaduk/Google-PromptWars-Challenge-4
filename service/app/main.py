"""FastAPI application factory for the Stadium Copilot service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.routes import router
from .config import get_settings
from .core.clock import SimClock
from .core.context import ContextService
from .core.crowd import CrowdSimulator
from .core.routing import Router
from .core.stadium import load_match_fixture, load_repository

logger = logging.getLogger("stadium_copilot")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load fixtures and build every singleton once, before serving."""
    settings = get_settings()
    repo = load_repository()
    match, ticket = load_match_fixture()

    app.state.settings = settings
    app.state.repo = repo
    app.state.clock = SimClock(
        match.kickoff_utc, settings.demo_start_offset_min, settings.demo_speed
    )
    app.state.crowd = CrowdSimulator(repo, seed=settings.crowd_seed)
    app.state.router_engine = Router(repo, app.state.crowd)
    app.state.context = ContextService(repo, match, ticket)
    app.state.provider_name = "gemini" if settings.gemini_api_key else "mock"
    app.state.model_name = settings.gemini_model if settings.gemini_api_key else None
    logger.info("service ready (provider=%s)", app.state.provider_name)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Stadium Copilot Service", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            payload = exc.detail
        else:
            payload = {"code": "http_error", "message": str(exc.detail)}
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": payload},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else {}
        location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        message = str(first.get("msg", "invalid request"))
        if location:
            message = f"{location}: {message}"
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        # Full traceback goes to the server log only; clients get a generic body.
        logger.exception("unhandled error")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An internal error occurred."}},
        )

    app.include_router(router)
    return app


app = create_app()
