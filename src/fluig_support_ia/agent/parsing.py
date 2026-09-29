"""Converte o texto em markdown produzido pelo LLM na estrutura ChatResponse.

Se o modelo nao seguir o formato pedido, o texto inteiro vira o diagnostico em
vez de a requisicao falhar: perder formatacao e aceitavel, perder a resposta nao.
"""

import re
from typing import Literal

_HEADING = re.compile(r"^##\s*(.+?)\s*$", re.MULTILINE)

_CONFIDENCE_VALUES = ("alta", "media", "baixa")


def _normalize(heading: str) -> str:
    table = str.maketrans("áàâãéêíóôõúüç", "aaaaeeiooouuc")
    return heading.strip().lower().translate(table)


def split_sections(text: str) -> dict[str, str]:
    """Divide o markdown em um dicionario {titulo_normalizado: conteudo}."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[_normalize(match.group(1))] = text[start:end].strip()
    return sections


def parse_next_steps(block: str) -> list[str]:
    """Extrai os itens de uma lista markdown, ignorando linhas vazias."""
    steps = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", line)
        if line:
            steps.append(line)
    return steps


def parse_confidence(block: str) -> Literal["alta", "media", "baixa"]:
    """Le o nivel de confianca declarado pelo modelo; o padrao e 'media'."""
    normalized = _normalize(block)
    for value in _CONFIDENCE_VALUES:
        if re.search(rf"\b{value}\b", normalized):
            return value  # type: ignore[return-value]
    return "media"


def parse_agent_output(text: str) -> dict[str, object]:
    """Retorna os campos de ChatResponse extraidos do texto do modelo."""
    sections = split_sections(text)

    diagnosis = sections.get("diagnostico", "").strip()
    draft = sections.get("rascunho ao cliente", "").strip()

    if not diagnosis and not draft:
        # Modelo ignorou o formato: preserva tudo no diagnostico.
        return {
            "diagnosis": text.strip(),
            "draft_reply": "",
            "next_steps": [],
            "confidence": "baixa",
        }

    return {
        "diagnosis": diagnosis or text.strip(),
        "draft_reply": draft,
        "next_steps": parse_next_steps(sections.get("proximos passos", "")),
        "confidence": parse_confidence(sections.get("confianca", "")),
    }
