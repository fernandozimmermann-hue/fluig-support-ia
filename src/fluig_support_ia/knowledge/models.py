"""Estruturas de dados da base de conhecimento."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Document:
    """Um documento antes de ser dividido em trechos."""

    source: str
    text: str
    title: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeChunk:
    """Um trecho indexado, com seu vetor."""

    source: str
    text: str
    embedding: list[float]
    chunk_index: int = 0
    title: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchHit:
    """Resultado de busca semantica."""

    source: str
    text: str
    score: float
    title: str | None = None
    url: str | None = None
