"""Configuracao de logging com mascaramento de dados sensiveis."""

import logging
import sys

from fluig_support_ia.agent.redaction import redact


class RedactingFormatter(logging.Formatter):
    """Formatter que mascara PII e segredos antes de escrever a linha de log."""

    def format(self, record: logging.LogRecord) -> str:
        """Formata o registro e mascara o resultado."""
        return redact(super().format(record))


def setup_logging(level: str = "INFO") -> None:
    """Configura o logger raiz. Idempotente."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Reduz o ruido das bibliotecas de rede.
    for noisy in ("httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
