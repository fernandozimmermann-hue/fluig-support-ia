"""Carregamento de documentos do diretorio local de conhecimento."""

import logging
from pathlib import Path

from fluig_support_ia.knowledge.models import Document

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset({".md", ".markdown", ".txt"})

_FRONT_MATTER_KEYS = ("title", "url")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Le um front matter simples (`chave: valor`) delimitado por `---`.

    Retorna os metadados reconhecidos e o corpo do documento.
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    closing = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing is None:
        return {}, text

    meta: dict[str, str] = {}
    for line in lines[1:closing]:
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() in _FRONT_MATTER_KEYS:
            meta[key.strip().lower()] = value.strip()

    return meta, "\n".join(lines[closing + 1 :]).lstrip()


def load_file(path: Path, root: Path | None = None) -> Document | None:
    """Carrega um unico arquivo como Document, ou None se estiver vazio."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_front_matter(raw)
    if not body.strip():
        logger.warning("Arquivo ignorado por estar vazio: %s", path)
        return None

    source = str(path.relative_to(root)) if root else path.name
    return Document(
        source=source,
        text=body,
        title=meta.get("title") or path.stem.replace("-", " ").replace("_", " "),
        url=meta.get("url"),
        metadata={"path": str(path)},
    )


def load_directory(root: Path) -> list[Document]:
    """Carrega recursivamente todos os arquivos suportados de um diretorio."""
    if not root.exists():
        raise FileNotFoundError(f"Diretorio de conhecimento nao encontrado: {root}")

    documents: list[Document] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            document = load_file(path, root=root)
            if document is not None:
                documents.append(document)
    return documents
