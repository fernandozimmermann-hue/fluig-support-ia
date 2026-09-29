"""Mascaramento de PII e segredos.

Chamados de suporte costumam trazer CPF, CNPJ, e-mail e as vezes senhas ou
tokens colados de um log. Esta camada mascara esses valores antes de eles irem
para o LLM ou para os arquivos de log.

Usa apenas a biblioteca padrao de proposito: e testavel sem nenhuma dependencia.
"""

import re
from typing import Final

MASK: Final[str] = "[REDACTED]"

_CPF: Final = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
_CNPJ: Final = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
_EMAIL: Final = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

# senha=..., "password": "...", token: ..., apikey=..., Authorization: Bearer ...
_SECRET: Final = re.compile(
    r"""(?ix)
    (?P<quote>["']?)   # aspas que abrem a chave em JSON: "password"
    \b(?P<label>senha|password|passwd|pwd|secret|token|api[_-]?key|authorization|bearer)\b
    ["']?              # aspas que fecham a chave
    \s*[:=]?\s*
    (?:(?:bearer|basic|oauth|token)\s+)?   # esquema, que nao e o segredo
    ["']?              # aspas que abrem o valor
    (?P<value>[^\s"',;}{]{4,})
    ["']?
    """
)


def redact(text: str) -> str:
    """Retorna o texto com CPF, CNPJ, e-mail e segredos mascarados."""
    if not text:
        return text

    def _mask_secret(match: re.Match[str]) -> str:
        quote = match.group("quote")
        return f"{quote}{match.group('label')}{quote}={MASK}"

    text = _SECRET.sub(_mask_secret, text)
    # CNPJ antes de CPF: o padrao de CNPJ e mais longo e mais especifico.
    text = _CNPJ.sub(MASK, text)
    text = _CPF.sub(MASK, text)
    return _EMAIL.sub(MASK, text)


def redact_if(text: str, enabled: bool) -> str:
    """Aplica `redact` somente quando `enabled` for verdadeiro."""
    return redact(text) if enabled else text
