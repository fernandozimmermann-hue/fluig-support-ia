"""Testes do indexador com um provedor de LLM falso (sem chamada de rede)."""

from typing import Any

from fluig_support_ia.knowledge.indexer import KnowledgeIndexer
from fluig_support_ia.knowledge.models import Document
from fluig_support_ia.knowledge.store import InMemoryVectorStore
from fluig_support_ia.llm.base import LLMResponse


class FakeProvider:
    """Embedding deterministico e barato: conta letras, sem rede."""

    def __init__(self) -> None:
        self.embed_calls: list[list[str]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        return LLMResponse(content="nao usado", model="fake")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [
            [
                float(text.lower().count("a")),
                float(text.lower().count("e")),
                float(len(text)),
            ]
            for text in texts
        ]


async def test_indexa_documento_e_grava_os_trechos():
    store = InMemoryVectorStore()
    provider = FakeProvider()
    indexer = KnowledgeIndexer(store=store, provider=provider, max_chars=200, overlap=0)

    documento = Document(
        source="bpm/travado.md",
        text="\n\n".join(f"Paragrafo {i} sobre atividade travada." * 4 for i in range(4)),
        title="Processo travado",
    )

    gravados = await indexer.index([documento])
    assert gravados > 1
    assert await store.count() == gravados


async def test_documento_vazio_nao_gera_trecho_nem_chamada_de_embedding():
    provider = FakeProvider()
    indexer = KnowledgeIndexer(store=InMemoryVectorStore(), provider=provider)
    assert await indexer.index([Document(source="vazio.md", text="   ")]) == 0
    assert provider.embed_calls == []


async def test_reindexar_a_mesma_fonte_nao_duplica():
    store = InMemoryVectorStore()
    indexer = KnowledgeIndexer(store=store, provider=FakeProvider(), max_chars=200, overlap=0)
    documento = Document(source="a.md", text="Conteudo de apoio ao suporte.")

    await indexer.index([documento])
    primeiro = await store.count()
    await indexer.index([documento])
    assert await store.count() == primeiro


async def test_search_retorna_o_trecho_mais_parecido_com_metadados():
    store = InMemoryVectorStore()
    indexer = KnowledgeIndexer(store=store, provider=FakeProvider(), max_chars=100, overlap=0)
    await indexer.index(
        [
            Document(source="a.md", text="aaaa aaaa aaaa", title="Doc A", url="https://a"),
            Document(source="b.md", text="eeee eeee eeee", title="Doc B"),
        ]
    )

    hits = await indexer.search("aaaa aaaa aaaa", top_k=1)
    assert len(hits) == 1
    assert hits[0].source == "a.md"
    assert hits[0].title == "Doc A"
    assert hits[0].url == "https://a"


async def test_busca_vazia_nao_chama_o_provedor():
    provider = FakeProvider()
    indexer = KnowledgeIndexer(store=InMemoryVectorStore(), provider=provider)
    assert await indexer.search("   ") == []
    assert provider.embed_calls == []
