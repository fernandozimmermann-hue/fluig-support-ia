"""Rotas de saude e diagnostico da propria aplicacao."""

from typing import Any

from fastapi import APIRouter

from fluig_support_ia import __version__
from fluig_support_ia.api.deps import get_registry, get_store
from fluig_support_ia.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness: mostra o que esta configurado e se a base responde."""
    settings = get_settings()
    registry = get_registry()

    knowledge: dict[str, Any] = {"store": settings.vector_store}
    try:
        knowledge["chunks"] = await get_store().count()
        knowledge["ok"] = True
    except Exception as exc:  # noqa: BLE001 - readiness nunca deve estourar
        knowledge["ok"] = False
        knowledge["error"] = f"{type(exc).__name__}: {exc}"

    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.app_env,
        "openai_configured": bool(settings.openai_api_key),
        "fluig_configured": settings.fluig_configured,
        "fluig_read_only": settings.fluig_read_only,
        "tools": registry.names if registry else [],
        "knowledge": knowledge,
    }
