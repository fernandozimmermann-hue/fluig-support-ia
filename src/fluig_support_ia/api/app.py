"""Aplicacao FastAPI: API do agente + portal web estatico."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fluig_support_ia import __version__
from fluig_support_ia.api.routes import chat, health, knowledge
from fluig_support_ia.config import get_settings
from fluig_support_ia.logging_setup import setup_logging

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Prepara a base de conhecimento na subida, sem impedir o start em caso de falha."""
    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY ausente: as rotas do agente responderao 503.")

    from fluig_support_ia.api.deps import get_store

    try:
        await get_store().setup()
        logger.info("Base de conhecimento pronta (%s).", settings.vector_store)
    except Exception as exc:  # noqa: BLE001 - app sobe e /ready reporta o problema
        logger.error("Nao foi possivel preparar a base de conhecimento: %s", exc)

    yield


def create_app() -> FastAPI:
    """Fabrica da aplicacao."""
    app = FastAPI(
        title="Fluig Support IA",
        description="Agente de apoio ao diagnostico e a resposta ao cliente no suporte Fluig.",
        version=__version__,
        lifespan=lifespan,
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(knowledge.router, prefix="/api")

    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            """Serve o portal web."""
            return FileResponse(WEB_DIR / "index.html")

    return app


app = create_app()
