"""PocketSmart AI — FastAPI application factory and entrypoint wiring."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("pocketsmart")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize essential services on server startup (docs: /startup activity)."""
    init_db()
    logger.info(
        "%s v%s started — database ready, Gemini %s",
        settings.APP_NAME, __version__,
        "configured" if settings.gemini_configured else "NOT configured (fallback mode)",
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="AI-powered budget & recommendation assistant for home interiors, parties and jewelry.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    # CORS for the configured frontend origins only.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.mount("/static", StaticFiles(directory="static"), name="static")

    from app.routes import auth, history, home, jewelry, pages, party, recommendations, session

    app.include_router(pages.router)
    app.include_router(auth.router)
    app.include_router(session.router)
    app.include_router(home.router)
    app.include_router(party.router)
    app.include_router(jewelry.router)
    app.include_router(recommendations.router)
    app.include_router(history.router)

    register_exception_handlers(app)
    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Human-readable JSON errors; never leak stack traces."""

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        # Extract the first readable message from pydantic errors.
        first = exc.errors()[0] if exc.errors() else {}
        raw_msg = str(first.get("msg", ""))
        field = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query"))
        friendly = _friendly_validation_message(field, raw_msg)
        return JSONResponse(status_code=422, content={"detail": friendly})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again in a moment."},
        )


def _friendly_validation_message(field: str, msg: str) -> str:
    field_labels = {
        "total_budget": "Budget must be a positive number.",
        "guest_count": "Guest count must be between 1 and 5000.",
        "rooms": "Add at least one room to plan.",
        "email": "Please enter a valid email address.",
        "password": "Password must be at least 8 characters with a letter and a number.",
        "full_name": "Please enter your full name.",
        "occasion": "Please tell us the occasion.",
        "event_type": "Choose an event type.",
    }
    for key, label in field_labels.items():
        if key in field:
            return label
    if "greater than 0" in msg or "Input should be greater than 0" in msg:
        return "Budget must be greater than zero."
    if "least one" in msg:
        return msg
    return "Please check your input and try again." + (f" ({field}: {msg})" if field else "")


app = create_app()


@app.get("/startup", tags=["system"])
def startup_status():
    """Health/config probe for the running application (no secrets exposed)."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": __version__,
        "gemini_configured": settings.gemini_configured,
        "gemini_model": settings.GEMINI_MODEL if settings.gemini_configured else None,
        "database": "connected",
        "docs_url": "/docs",
    }
