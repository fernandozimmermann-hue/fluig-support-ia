"""Testes do orquestrador com LLM e ferramentas falsas (sem rede)."""

from typing import Any

from fluig_support_ia.agent.orchestrator import SupportAgent
from fluig_support_ia.agent.schemas import ChatRequest, TicketContext
from fluig_support_ia.knowledge.indexer import KnowledgeIndexer
from fluig_support_ia.knowledge.models import Document
from fluig_support_ia.knowledge.store import InMemoryVectorStore
from fluig_support_ia.llm.base import LLMResponse, ToolCall
from fluig_support_ia.tools.registry import Tool, ToolRegistry, ToolResult

RESPOSTA_FINAL = """\
## Diagnostico
Responsavel inativo [fonte: a.md].

## Proximos passos
- Reativar o usuario

## Rascunho ao cliente
Ola, ajustamos o responsavel.

## Confianca
alta - confirmado no ambiente.
"""


class ScriptedProvider:
    """Devolve respostas pre-programadas e registra o que recebeu."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


async def _indexer_com_conteudo() -> KnowledgeIndexer:
    store = InMemoryVectorStore()
    indexer = KnowledgeIndexer(store=store, provider=ScriptedProvider([]), max_chars=400, overlap=0)
    await indexer.index(
        [Document(source="a.md", text="Atividade travada por responsavel inativo.")]
    )
    return indexer


def _registry_com(nome: str, resultado: ToolResult) -> ToolRegistry:
    async def handler() -> ToolResult:
        return resultado

    registry = ToolRegistry()
    registry.register(
        Tool(
            name=nome,
            description="ferramenta de teste",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=handler,
        )
    )
    return registry


async def test_resposta_direta_sem_ferramentas():
    provider = ScriptedProvider([LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o")])
    agent = SupportAgent(provider=provider, indexer=await _indexer_com_conteudo())

    resposta = await agent.answer(ChatRequest(question="Por que a solicitacao travou?"))

    assert "Responsavel inativo" in resposta.diagnosis
    assert resposta.draft_reply == "Ola, ajustamos o responsavel."
    assert resposta.next_steps == ["Reativar o usuario"]
    assert resposta.confidence == "alta"
    assert resposta.model == "gpt-4o"
    assert resposta.tool_calls == []


async def test_cita_as_fontes_recuperadas():
    provider = ScriptedProvider([LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o")])
    agent = SupportAgent(provider=provider, indexer=await _indexer_com_conteudo())

    resposta = await agent.answer(ChatRequest(question="Por que travou?"))
    assert [c.source for c in resposta.citations] == ["a.md"]


async def test_executa_ferramenta_pedida_e_registra_o_rastro():
    provider = ScriptedProvider(
        [
            LLMResponse(tool_calls=[ToolCall(id="c1", name="diagnostico", arguments={})]),
            LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o"),
        ]
    )
    agent = SupportAgent(
        provider=provider,
        indexer=await _indexer_com_conteudo(),
        registry=_registry_com("diagnostico", ToolResult(ok=True, summary="ambiente ok")),
    )

    resposta = await agent.answer(ChatRequest(question="Verifique o ambiente."))

    assert len(resposta.tool_calls) == 1
    assert resposta.tool_calls[0].name == "diagnostico"
    assert resposta.tool_calls[0].ok
    assert len(provider.calls) == 2
    assert any(m.get("role") == "tool" for m in provider.calls[1]["messages"])


async def test_falha_de_ferramenta_nao_interrompe_a_resposta():
    provider = ScriptedProvider(
        [
            LLMResponse(tool_calls=[ToolCall(id="c1", name="diagnostico", arguments={})]),
            LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o"),
        ]
    )
    agent = SupportAgent(
        provider=provider,
        indexer=await _indexer_com_conteudo(),
        registry=_registry_com("diagnostico", ToolResult.failure("Fluig fora do ar")),
    )

    resposta = await agent.answer(ChatRequest(question="Verifique o ambiente."))
    assert resposta.tool_calls[0].ok is False
    assert resposta.diagnosis


async def test_use_tools_false_nao_envia_ferramentas_ao_modelo():
    provider = ScriptedProvider([LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o")])
    agent = SupportAgent(
        provider=provider,
        indexer=await _indexer_com_conteudo(),
        registry=_registry_com("diagnostico", ToolResult(ok=True, summary="ok")),
    )

    await agent.answer(ChatRequest(question="Somente teoria.", use_tools=False))
    assert provider.calls[0]["tools"] is None


async def test_limite_de_iteracoes_forca_uma_conclusao():
    provider = ScriptedProvider(
        [LLMResponse(tool_calls=[ToolCall(id="c1", name="diagnostico", arguments={})])]
    )
    agent = SupportAgent(
        provider=provider,
        indexer=await _indexer_com_conteudo(),
        registry=_registry_com("diagnostico", ToolResult(ok=True, summary="ok")),
        max_tool_iterations=2,
    )

    resposta = await agent.answer(ChatRequest(question="Loop infinito?"))
    # 2 iteracoes com ferramenta + 1 chamada final de conclusao
    assert len(provider.calls) == 3
    assert provider.calls[-1]["tools"] is None
    assert len(resposta.tool_calls) == 2


async def test_pii_do_log_do_chamado_e_mascarada_antes_de_ir_ao_modelo():
    provider = ScriptedProvider([LLMResponse(content=RESPOSTA_FINAL, model="gpt-4o")])
    agent = SupportAgent(provider=provider, indexer=await _indexer_com_conteudo(), redact_pii=True)

    await agent.answer(
        ChatRequest(
            question="Erro com o usuario joao@empresa.com.br",
            ticket=TicketContext(error_log="login=joao@empresa.com.br senha=Secreta123"),
        )
    )

    enviado = provider.calls[0]["messages"][-1]["content"]
    assert "joao@empresa.com.br" not in enviado
    assert "Secreta123" not in enviado
    assert "REDACTED" in enviado
