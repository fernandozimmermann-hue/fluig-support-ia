"""Rota de conversa com o agente."""

import logging

from fastapi import APIRouter, HTTPException

from fluig_support_ia.agent.schemas import ChatRequest, ChatResponse
from fluig_support_ia.api.deps import get_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Recebe a pergunta do analista e devolve diagnostico + rascunho ao cliente."""
    try:
        return await get_agent().answer(request)
    except ValueError as exc:
        # Ex.: OPENAI_API_KEY ausente.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Falha ao processar a pergunta")
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao processar a pergunta: {type(exc).__name__}",
        ) from exc
