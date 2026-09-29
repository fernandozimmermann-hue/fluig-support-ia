"""Divisao de documentos em trechos (chunks).

Estrategia: quebrar preferencialmente em limites naturais (paragrafo, depois
frase), com sobreposicao entre trechos vizinhos para nao cortar um procedimento
no meio. Sem dependencias externas.
"""

import re
from dataclasses import dataclass

_PARAGRAPH = re.compile(r"\n\s*\n")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")


@dataclass(slots=True)
class Chunk:
    """Um trecho de documento pronto para virar embedding."""

    text: str
    index: int


def _split_long(text: str, max_chars: int) -> list[str]:
    """Quebra um bloco grande em frases e reagrupa respeitando max_chars."""
    pieces: list[str] = []
    buffer = ""
    for sentence in _SENTENCE.split(text):
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            pieces.append(buffer)
        # Frase unica maior que o limite: corta no limite mesmo.
        while len(sentence) > max_chars:
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        buffer = sentence
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]:
    """Divide o texto em trechos de no maximo `max_chars` com sobreposicao.

    Args:
        text: conteudo do documento.
        max_chars: tamanho maximo de cada trecho.
        overlap: quantidade de caracteres do fim de um trecho repetida no inicio
            do seguinte. Deve ser menor que `max_chars`.
    """
    if max_chars <= 0:
        raise ValueError("max_chars deve ser positivo.")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap deve estar entre 0 e max_chars - 1.")

    normalized = text.strip()
    if not normalized:
        return []

    blocks: list[str] = []
    for paragraph in _PARAGRAPH.split(normalized):
        stripped = paragraph.strip()
        if not stripped:
            continue
        if len(stripped) <= max_chars:
            blocks.append(stripped)
        else:
            blocks.extend(_split_long(stripped, max_chars))

    # Reagrupa blocos pequenos para nao gerar trechos curtos demais.
    grouped: list[str] = []
    buffer = ""
    for block in blocks:
        candidate = f"{buffer}\n\n{block}" if buffer else block
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                grouped.append(buffer)
            buffer = block
    if buffer:
        grouped.append(buffer)

    if overlap == 0:
        return [Chunk(text=t, index=i) for i, t in enumerate(grouped)]

    chunks: list[Chunk] = []
    for position, block in enumerate(grouped):
        if position == 0:
            chunks.append(Chunk(text=block, index=0))
            continue
        tail = grouped[position - 1][-overlap:]
        chunks.append(Chunk(text=f"{tail}\n\n{block}".strip(), index=position))
    return chunks
