#!/usr/bin/env python
"""Indexa os documentos de conhecimento na base vetorial.

Uso:
    python scripts/ingest.py
    python scripts/ingest.py --dir data/knowledge --max-chars 1500
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fluig_support_ia.config import get_settings
from fluig_support_ia.knowledge.indexer import KnowledgeIndexer
from fluig_support_ia.knowledge.loaders import load_directory
from fluig_support_ia.knowledge.store import (
    InMemoryVectorStore,
    PgVectorStore,
    VectorStore,
)
from fluig_support_ia.llm.openai_provider import OpenAIProvider
from fluig_support_ia.logging_setup import setup_logging


async def main() -> int:
    """Carrega, divide, vetoriza e grava os documentos."""
    parser = argparse.ArgumentParser(description="Indexa a base de conhecimento do agente.")
    parser.add_argument("--dir", default="data/knowledge", help="Diretorio com os documentos.")
    parser.add_argument("--max-chars", type=int, default=1200, help="Tamanho maximo do trecho.")
    parser.add_argument("--overlap", type=int, default=150, help="Sobreposicao entre trechos.")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.openai_api_key:
        print("ERRO: OPENAI_API_KEY nao configurada (veja o .env).", file=sys.stderr)
        return 1

    directory = Path(args.dir)
    try:
        documents = load_directory(directory)
    except FileNotFoundError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    if not documents:
        print(f"Nenhum documento .md/.txt encontrado em {directory}.")
        return 0

    store: VectorStore = (
        PgVectorStore(settings.database_url, settings.embedding_dimensions)
        if settings.vector_store == "pgvector"
        else InMemoryVectorStore()
    )
    if settings.vector_store == "in_memory":
        print("AVISO: VECTOR_STORE=in_memory. A indexacao nao sera persistida.", file=sys.stderr)

    await store.setup()

    indexer = KnowledgeIndexer(
        store=store,
        provider=OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            embedding_model=settings.openai_embedding_model,
        ),
        max_chars=args.max_chars,
        overlap=args.overlap,
    )

    chunks = await indexer.index(documents)
    print(f"OK: {len(documents)} documento(s), {chunks} trecho(s) indexado(s).")
    print(f"Total na base: {await store.count()} trecho(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
