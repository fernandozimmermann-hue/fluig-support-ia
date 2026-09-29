"""Indexacao e busca na base de conhecimento."""

import logging

from fluig_support_ia.knowledge.chunking import chunk_text
from fluig_support_ia.knowledge.models import Document, KnowledgeChunk, SearchHit
from fluig_support_ia.knowledge.store import VectorStore
from fluig_support_ia.llm.base import LLMProvider

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 64


class KnowledgeIndexer:
    """Transforma documentos em trechos vetorizados e consulta a base."""

    def __init__(
        self,
        store: VectorStore,
        provider: LLMProvider,
        max_chars: int = 1200,
        overlap: int = 150,
    ) -> None:
        self._store = store
        self._provider = provider
        self._max_chars = max_chars
        self._overlap = overlap

    async def index(self, documents: list[Document]) -> int:
        """Indexa uma lista de documentos. Retorna o total de trechos gravados."""
        total = 0
        for document in documents:
            chunks = chunk_text(document.text, self._max_chars, self._overlap)
            if not chunks:
                continue

            embeddings: list[list[float]] = []
            for start in range(0, len(chunks), EMBED_BATCH_SIZE):
                batch = chunks[start : start + EMBED_BATCH_SIZE]
                embeddings.extend(await self._provider.embed([c.text for c in batch]))

            written = await self._store.upsert(
                [
                    KnowledgeChunk(
                        source=document.source,
                        text=chunk.text,
                        embedding=embedding,
                        chunk_index=chunk.index,
                        title=document.title,
                        url=document.url,
                        metadata=document.metadata,
                    )
                    for chunk, embedding in zip(chunks, embeddings, strict=True)
                ]
            )
            total += written
            logger.info("Indexado %s (%d trechos)", document.source, written)
        return total

    async def search(self, query: str, top_k: int = 6) -> list[SearchHit]:
        """Busca semantica a partir de uma pergunta em texto."""
        if not query.strip():
            return []
        vectors = await self._provider.embed([query])
        if not vectors:
            return []
        return await self._store.search(vectors[0], top_k=top_k)
