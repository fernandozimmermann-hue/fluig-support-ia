import pytest

from fluig_support_ia.knowledge.models import KnowledgeChunk
from fluig_support_ia.knowledge.store import InMemoryVectorStore, cosine_similarity


def _chunk(source: str, text: str, embedding: list[float], index: int = 0) -> KnowledgeChunk:
    return KnowledgeChunk(source=source, text=text, embedding=embedding, chunk_index=index)


def test_cosseno_de_vetores_identicos_e_um():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosseno_de_vetores_ortogonais_e_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosseno_com_vetor_nulo_nao_divide_por_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosseno_exige_mesma_dimensao():
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 2.0])


async def test_upsert_e_count():
    store = InMemoryVectorStore()
    gravados = await store.upsert([_chunk("a.md", "texto", [1.0, 0.0])])
    assert gravados == 1
    assert await store.count() == 1


async def test_upsert_da_mesma_fonte_substitui_os_trechos_anteriores():
    store = InMemoryVectorStore()
    await store.upsert([_chunk("a.md", "antigo", [1.0, 0.0], 0)])
    await store.upsert(
        [_chunk("a.md", "novo 1", [1.0, 0.0], 0), _chunk("a.md", "novo 2", [0.0, 1.0], 1)]
    )
    assert await store.count() == 2
    hits = await store.search([1.0, 0.0], top_k=5)
    assert "antigo" not in [hit.text for hit in hits]


async def test_search_ordena_por_similaridade_e_respeita_top_k():
    store = InMemoryVectorStore()
    await store.upsert(
        [
            _chunk("perto.md", "perto", [1.0, 0.0]),
            _chunk("meio.md", "meio", [0.7, 0.7]),
            _chunk("longe.md", "longe", [0.0, 1.0]),
        ]
    )
    hits = await store.search([1.0, 0.0], top_k=2)
    assert [hit.source for hit in hits] == ["perto.md", "meio.md"]
    assert hits[0].score > hits[1].score


async def test_search_em_base_vazia_retorna_lista_vazia():
    assert await InMemoryVectorStore().search([1.0, 0.0]) == []


async def test_delete_source_remove_apenas_a_fonte_indicada():
    store = InMemoryVectorStore()
    await store.upsert([_chunk("a.md", "a", [1.0, 0.0]), _chunk("b.md", "b", [0.0, 1.0])])
    assert await store.delete_source("a.md") == 1
    assert await store.count() == 1
    assert (await store.search([0.0, 1.0]))[0].source == "b.md"
