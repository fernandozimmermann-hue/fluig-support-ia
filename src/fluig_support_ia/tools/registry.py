"""Registro de ferramentas do agente.

Mantido sem dependencias externas para que o contrato possa ser testado sozinho.
"""

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

ToolHandler = Callable[..., Awaitable["ToolResult"]]


@dataclass(slots=True)
class ToolResult:
    """Resultado da execucao de uma ferramenta."""

    ok: bool
    summary: str
    data: Any = None

    @classmethod
    def failure(cls, summary: str) -> "ToolResult":
        """Atalho para um resultado de erro."""
        return cls(ok=False, summary=summary, data=None)


@dataclass(slots=True)
class Tool:
    """Uma ferramenta exposta ao modelo."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    read_only: bool = True

    def to_openai_schema(self) -> dict[str, Any]:
        """Converte para o formato de `tools` da API da OpenAI."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Coleciona ferramentas e executa as chamadas pedidas pelo modelo."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Adiciona uma ferramenta; nomes duplicados sao rejeitados."""
        if tool.name in self._tools:
            raise ValueError(f"Ferramenta duplicada: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Busca uma ferramenta pelo nome."""
        return self._tools.get(name)

    @property
    def names(self) -> list[str]:
        """Nomes das ferramentas registradas, em ordem de registro."""
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        """Schemas de todas as ferramentas, para enviar ao modelo."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Executa uma ferramenta, isolando erros como ToolResult de falha."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult.failure(f"Ferramenta desconhecida: {name}")

        accepted = _accepted_parameters(tool.handler)
        if accepted is not None:
            unexpected = set(arguments) - accepted
            if unexpected:
                return ToolResult.failure(
                    f"Parametros nao suportados por {name}: {sorted(unexpected)}"
                )

        try:
            return await tool.handler(**arguments)
        except TypeError as exc:
            return ToolResult.failure(f"Argumentos invalidos para {name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - erro de ferramenta volta ao modelo
            return ToolResult.failure(f"Falha ao executar {name}: {type(exc).__name__}: {exc}")


def _accepted_parameters(handler: ToolHandler) -> set[str] | None:
    """Nomes de parametros aceitos, ou None se o handler aceita **kwargs."""
    signature = inspect.signature(handler)
    names: set[str] = set()
    for parameter in signature.parameters.values():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            return None
        if parameter.kind is not inspect.Parameter.VAR_POSITIONAL:
            names.add(parameter.name)
    return names
