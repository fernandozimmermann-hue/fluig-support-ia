"""Montagem das dependencias da aplicacao (wiring)."""

import logging
from functools import lru_cache

from fluig_support_ia.agent.orchestrator import SupportAgent
from fluig_support_ia.config import Settings, get_settings
from fluig_support_ia.knowledge.indexer import KnowledgeIndexer
from fluig_support_ia.knowledge.store import InMemoryVectorStore, PgVectorStore, VectorStore
from fluig_support_ia.llm.openai_provider import OpenAIProvider
from fluig_support_ia.tools.fluig_client import FluigClient
from fluig_support_ia.tools.fluig_tools import build_fluig_registry
from fluig_support_ia.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@lru_cache
def get_provider() -> OpenAIProvider:
    """Provedor de LLM (singleton)."""
    settings = get_settings()
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        embedding_model=settings.openai_embedding_model,
    )


@lru_cache
def get_store() -> VectorStore:
    """Armazenamento de vetores conforme a configuracao."""
    settings = get_settings()
    if settings.vector_store == "pgvector":
        return PgVectorStore(settings.database_url, settings.embedding_dimensions)
    logger.warning("VECTOR_STORE=in_memory: a base de conhecimento nao sera persistida.")
    return InMemoryVectorStore()


@lru_cache
def get_indexer() -> KnowledgeIndexer:
    """Indexador da base de conhecimento."""
    return KnowledgeIndexer(store=get_store(), provider=get_provider())


@lru_cache
def get_registry() -> ToolRegistry | None:
    """Registro de ferramentas, ou None se o Fluig nao estiver configurado."""
    settings = get_settings()
    if not settings.fluig_configured:
        logger.warning(
            "Credenciais do Fluig ausentes: o agente respondera sem consultar o ambiente."
        )
        return None

    client = FluigClient(
        base_url=settings.fluig_base_url,
        consumer_key=settings.fluig_consumer_key,
        consumer_secret=settings.fluig_consumer_secret,
        access_token=settings.fluig_access_token,
        token_secret=settings.fluig_token_secret,
        timeout=settings.fluig_timeout_seconds,
        read_only=settings.fluig_read_only,
    )
    return build_fluig_registry(client)


@lru_cache
def get_agent() -> SupportAgent:
    """Agente pronto para uso."""
    settings: Settings = get_settings()
    return SupportAgent(
        provider=get_provider(),
        indexer=get_indexer(),
        registry=get_registry(),
        top_k=settings.retrieval_top_k,
        max_tool_iterations=settings.agent_max_tool_iterations,
        redact_pii=settings.redact_pii,
    )
