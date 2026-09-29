"""Orquestrador: junta RAG, loop de ferramentas e LLM em uma resposta."""

import logging
from typing import Any

from fluig_support_ia.agent.parsing import parse_agent_output
from fluig_support_ia.agent.prompts import build_messages
from fluig_support_ia.agent.redaction import redact_if
from fluig_support_ia.agent.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    ToolCallTrace,
)
from fluig_support_ia.knowledge.indexer import KnowledgeIndexer
from fluig_support_ia.llm.base import LLMProvider
from fluig_support_ia.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

EXCERPT_CHARS = 400


class SupportAgent:
    """Agente de apoio ao N2.

    Fluxo de uma pergunta:
    1. busca trechos relevantes na base de conhecimento (RAG);
    2. monta o prompt com o chamado e o contexto;
    3. deixa o modelo chamar ferramentas de diagnostico enquanto precisar;
    4. converte a resposta final em diagnostico + rascunho ao cliente.
    """

    def __init__(
        self,
        provider: LLMProvider,
        indexer: KnowledgeIndexer,
        registry: ToolRegistry | None = None,
        top_k: int = 6,
        max_tool_iterations: int = 6,
        redact_pii: bool = True,
    ) -> None:
        self._provider = provider
        self._indexer = indexer
        self._registry = registry
        self._top_k = top_k
        self._max_tool_iterations = max_tool_iterations
        self._redact = redact_pii

    async def answer(self, request: ChatRequest) -> ChatResponse:
        """Responde a pergunta do analista."""
        question = redact_if(request.question, self._redact)

        hits = await self._indexer.search(question, top_k=self._top_k)
        citations = [
            Citation(
                source=hit.source,
                title=hit.title,
                url=hit.url,
                excerpt=hit.text[:EXCERPT_CHARS].strip(),
                score=round(hit.score, 4),
            )
            for hit in hits
        ]

        ticket = request.ticket
        if ticket is not None and self._redact:
            ticket = ticket.model_copy(
                update={
                    "error_log": redact_if(ticket.error_log or "", True) or None,
                    "customer": ticket.customer,
                }
            )

        messages: list[dict[str, Any]] = build_messages(
            question=question,
            history=request.history,
            ticket=ticket,
            chunks=[(hit.source, hit.text) for hit in hits],
        )

        tools = (
            self._registry.schemas() if (request.use_tools and self._registry is not None) else None
        )

        traces: list[ToolCallTrace] = []
        final_text = ""
        model_name = ""

        for iteration in range(self._max_tool_iterations):
            response = await self._provider.complete(messages, tools=tools)
            model_name = response.model or model_name

            if not response.wants_tools:
                final_text = response.content
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": _json_dumps(call.arguments),
                            },
                        }
                        for call in response.tool_calls
                    ],
                }
            )

            for call in response.tool_calls:
                assert self._registry is not None  # tools != None garante o registro
                result = await self._registry.execute(call.name, call.arguments)
                summary = redact_if(result.summary, self._redact)

                traces.append(
                    ToolCallTrace(
                        name=call.name,
                        arguments=call.arguments,
                        ok=result.ok,
                        summary=summary,
                    )
                )
                messages.append({"role": "tool", "tool_call_id": call.id, "content": summary})

            logger.info(
                "Iteracao %d: %d ferramenta(s) executada(s)",
                iteration + 1,
                len(response.tool_calls),
            )
        else:
            # Estourou o limite de iteracoes: pede uma conclusao sem ferramentas.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Limite de consultas ao ambiente atingido. Conclua agora com o que "
                        "voce ja tem e diga explicitamente o que ficou sem verificar."
                    ),
                }
            )
            final = await self._provider.complete(messages, tools=None)
            final_text = final.content
            model_name = final.model or model_name

        parsed = parse_agent_output(final_text)
        return ChatResponse(
            diagnosis=str(parsed["diagnosis"]),
            draft_reply=str(parsed["draft_reply"]),
            next_steps=list(parsed["next_steps"]),  # type: ignore[arg-type]
            citations=citations,
            tool_calls=traces,
            confidence=parsed["confidence"],  # type: ignore[arg-type]
            model=model_name,
        )


def _json_dumps(value: dict[str, Any]) -> str:
    """Serializa argumentos de ferramenta para devolver ao historico do modelo."""
    import json

    return json.dumps(value, ensure_ascii=False)
