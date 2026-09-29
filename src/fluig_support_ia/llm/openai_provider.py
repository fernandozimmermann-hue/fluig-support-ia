"""Provedor OpenAI (chat completions + embeddings)."""

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from fluig_support_ia.llm.base import LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Implementacao de `LLMProvider` usando a API da OpenAI."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY nao configurada.")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._embedding_model = embedding_model

    @property
    def model(self) -> str:
        """Nome do modelo de chat em uso."""
        return self._model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        """Chama o endpoint de chat completions e normaliza a resposta."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        completion = await self._client.chat.completions.create(**kwargs)
        choice = completion.choices[0].message

        tool_calls: list[ToolCall] = []
        for call in choice.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=_safe_json(call.function.arguments),
                )
            )

        usage = completion.usage
        return LLMResponse(
            content=choice.content or "",
            tool_calls=tool_calls,
            model=completion.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Gera embeddings preservando a ordem da entrada."""
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]


def _safe_json(raw: str | None) -> dict[str, Any]:
    """Converte os argumentos da ferramenta em dict, tolerando JSON invalido."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Argumentos de ferramenta nao sao JSON valido: %r", raw)
        return {}
    return parsed if isinstance(parsed, dict) else {}
