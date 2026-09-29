"""Contratos de entrada e saida do agente (usados tambem pela API)."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Uma mensagem do historico da conversa."""

    role: Literal["user", "assistant"]
    content: str


class TicketContext(BaseModel):
    """Dados do chamado que o analista N2 esta tratando."""

    ticket_id: str | None = None
    customer: str | None = None
    fluig_version: str | None = None
    module: str | None = Field(
        default=None,
        description="Ex.: BPM, ECM, Identity, Analytics, Portal, Dataset",
    )
    error_log: str | None = None


class ChatRequest(BaseModel):
    """Pergunta do analista para o agente."""

    question: str = Field(min_length=1)
    history: list[Message] = Field(default_factory=list)
    ticket: TicketContext | None = None
    use_tools: bool = Field(
        default=True,
        description="Permite ao agente consultar a API do Fluig durante o diagnostico.",
    )


class Citation(BaseModel):
    """Referencia a um trecho da base de conhecimento usado na resposta."""

    source: str
    title: str | None = None
    url: str | None = None
    excerpt: str
    score: float


class ToolCallTrace(BaseModel):
    """Registro de uma ferramenta que o agente executou."""

    name: str
    arguments: dict[str, Any]
    ok: bool
    summary: str


class ChatResponse(BaseModel):
    """Resposta do agente, separada em diagnostico interno e rascunho ao cliente."""

    diagnosis: str = Field(description="Analise tecnica destinada ao analista N2.")
    draft_reply: str = Field(description="Rascunho de resposta para enviar ao cliente.")
    next_steps: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    confidence: Literal["alta", "media", "baixa"] = "media"
    model: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
