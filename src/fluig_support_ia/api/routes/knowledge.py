"""Rotas de administracao da base de conhecimento."""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from fluig_support_ia.api.deps import get_indexer, get_store
from fluig_support_ia.config import get_settings
from fluig_support_ia.knowledge.loaders import load_directory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

KNOWLEDGE_DIR = Path("data/knowledge")


class ReindexRequest(BaseModel):
    """Pedido de reindexacao do diretorio local de conhecimento."""

    directory: str = Field(default=str(KNOWLEDGE_DIR))


class SearchRequest(BaseModel):
    """Busca direta na base, sem passar pelo LLM de resposta."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)


@router.post("/reindex")
async def reindex(request: ReindexRequest) -> dict[str, Any]:
    """Recarrega e reindexa os documentos do diretorio informado."""
    directory = Path(request.directory)
    try:
        documents = load_directory(directory)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not documents:
        return {"documents": 0, "chunks": 0, "detail": "Nenhum documento suportado encontrado."}

    await get_store().setup()
    chunks = await get_indexer().index(documents)
    return {"documents": len(documents), "chunks": chunks}


@router.post("/search")
async def search(request: SearchRequest) -> dict[str, Any]:
    """Consulta semantica na base, util para depurar a qualidade do RAG."""
    hits = await get_indexer().search(request.query, top_k=request.top_k)
    return {
        "hits": [
            {
                "source": hit.source,
                "title": hit.title,
                "url": hit.url,
                "score": round(hit.score, 4),
                "text": hit.text,
            }
            for hit in hits
        ]
    }


@router.get("/stats")
async def stats() -> dict[str, Any]:
    """Quantidade de trechos indexados e backend em uso."""
    return {
        "store": get_settings().vector_store,
        "chunks": await get_store().count(),
    }
