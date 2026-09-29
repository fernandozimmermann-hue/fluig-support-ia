"""Armazenamento de vetores.

Duas implementacoes:
- `InMemoryVectorStore`: sem dependencia, util para teste e para rodar sem banco.
- `PgVectorStore`: Postgres + pgvector, para uso real.
"""

import json
import math
from typing import Any, Protocol

from fluig_support_ia.knowledge.models import KnowledgeChunk, SearchHit


class VectorStore(Protocol):
    """Contrato de um armazenamento de vetores."""

    async def setup(self) -> None:
        """Cria as estruturas necessarias, se ainda nao existirem."""
        ...

    async def upsert(self, chunks: list[KnowledgeChunk]) -> int:
        """Insere ou atualiza trechos. Retorna a quantidade gravada."""
        ...

    async def search(self, embedding: list[float], top_k: int = 6) -> list[SearchHit]:
        """Busca os trechos mais similares ao vetor informado."""
        ...

    async def delete_source(self, source: str) -> int:
        """Remove todos os trechos de uma fonte. Retorna a quantidade removida."""
        ...

    async def count(self) -> int:
        """Total de trechos indexados."""
        ...


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores de mesmo tamanho."""
    if len(a) != len(b):
        raise ValueError("Vetores de dimensoes diferentes.")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore:
    """Armazenamento em memoria. Nao persiste entre reinicios."""

    def __init__(self) -> None:
        self._chunks: list[KnowledgeChunk] = []

    async def setup(self) -> None:
        """Nada a preparar."""
        return None

    async def upsert(self, chunks: list[KnowledgeChunk]) -> int:
        """Substitui os trechos das fontes recebidas e adiciona os novos."""
        sources = {chunk.source for chunk in chunks}
        self._chunks = [chunk for chunk in self._chunks if chunk.source not in sources]
        self._chunks.extend(chunks)
        return len(chunks)

    async def search(self, embedding: list[float], top_k: int = 6) -> list[SearchHit]:
        """Ordena todos os trechos por similaridade e devolve os melhores."""
        scored = [
            SearchHit(
                source=chunk.source,
                text=chunk.text,
                score=cosine_similarity(embedding, chunk.embedding),
                title=chunk.title,
                url=chunk.url,
            )
            for chunk in self._chunks
        ]
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:top_k]

    async def delete_source(self, source: str) -> int:
        """Remove os trechos de uma fonte."""
        before = len(self._chunks)
        self._chunks = [chunk for chunk in self._chunks if chunk.source != source]
        return before - len(self._chunks)

    async def count(self) -> int:
        """Total de trechos em memoria."""
        return len(self._chunks)


_SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    title       TEXT,
    url         TEXT,
    text        TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    embedding   VECTOR({dimensions}) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, chunk_index)
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
"""


class PgVectorStore:
    """Armazenamento em Postgres com a extensao pgvector."""

    def __init__(self, dsn: str, dimensions: int = 1536) -> None:
        self._dsn = dsn
        self._dimensions = dimensions

    async def _connect(self) -> Any:
        """Abre uma conexao assincrona registrando o tipo vector."""
        from pgvector.psycopg import register_vector_async
        from psycopg import AsyncConnection  # import tardio: dependencia opcional

        conn = await AsyncConnection.connect(self._dsn, autocommit=True)
        await register_vector_async(conn)
        return conn

    async def setup(self) -> None:
        """Cria extensao, tabela e indice."""
        conn = await self._connect()
        try:
            await conn.execute(_SCHEMA.format(dimensions=self._dimensions))
        finally:
            await conn.close()

    async def upsert(self, chunks: list[KnowledgeChunk]) -> int:
        """Grava os trechos, substituindo os de mesma (source, chunk_index)."""
        if not chunks:
            return 0
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO knowledge_chunks
                        (source, chunk_index, title, url, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, chunk_index) DO UPDATE SET
                        title = EXCLUDED.title,
                        url = EXCLUDED.url,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding,
                        created_at = now()
                    """,
                    [
                        (
                            c.source,
                            c.chunk_index,
                            c.title,
                            c.url,
                            c.text,
                            json.dumps(c.metadata, ensure_ascii=False),
                            c.embedding,
                        )
                        for c in chunks
                    ],
                )
            return len(chunks)
        finally:
            await conn.close()

    async def search(self, embedding: list[float], top_k: int = 6) -> list[SearchHit]:
        """Busca por distancia de cosseno, convertida em score de similaridade."""
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT source, title, url, text, 1 - (embedding <=> %s) AS score
                    FROM knowledge_chunks
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (embedding, embedding, top_k),
                )
                rows = await cur.fetchall()
            return [
                SearchHit(source=row[0], title=row[1], url=row[2], text=row[3], score=float(row[4]))
                for row in rows
            ]
        finally:
            await conn.close()

    async def delete_source(self, source: str) -> int:
        """Remove todos os trechos de uma fonte."""
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM knowledge_chunks WHERE source = %s", (source,))
                return cur.rowcount
        finally:
            await conn.close()

    async def count(self) -> int:
        """Total de trechos na tabela."""
        conn = await self._connect()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT count(*) FROM knowledge_chunks")
                row = await cur.fetchone()
            return int(row[0]) if row else 0
        finally:
            await conn.close()
