"""Interface de provedor de LLM.

Hoje so existe a implementacao OpenAI. Esta abstracao fina existe para que trocar
ou adicionar um provedor (Bedrock, Azure OpenAI, Anthropic) nao exija mexer no
orquestrador do agente.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class ToolCall:
    """Pedido do modelo para executar uma ferramenta."""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    """Resposta normalizada de uma chamada ao modelo."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def wants_tools(self) -> bool:
        """Indica se o modelo pediu execucao de ferramentas."""
        return bool(self.tool_calls)


@runtime_checkable
class LLMProvider(Protocol):
    """Contrato minimo que o orquestrador espera de um provedor."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Gera uma resposta, possivelmente pedindo chamadas de ferramenta."""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings para uma lista de textos."""
        ...
