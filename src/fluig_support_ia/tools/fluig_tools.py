"""Ferramentas de diagnostico que consultam o ambiente Fluig.

Todas sao somente leitura. Cada handler devolve um `ToolResult` com um `summary`
curto (o que volta para o modelo) e o `data` bruto (o que a UI pode inspecionar).
"""

import json
import logging
from typing import Any

from fluig_support_ia.tools.fluig_client import FluigClient, FluigError
from fluig_support_ia.tools.fluig_endpoints import endpoint
from fluig_support_ia.tools.registry import Tool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

MAX_SUMMARY_CHARS = 4000


def _summarize(label: str, payload: Any) -> str:
    """Serializa o payload para o modelo, truncando o que for grande demais."""
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if len(text) > MAX_SUMMARY_CHARS:
        text = text[:MAX_SUMMARY_CHARS] + "\n... (resposta truncada)"
    return f"{label}:\n{text}"


def build_fluig_registry(client: FluigClient) -> ToolRegistry:
    """Cria o registro de ferramentas ligadas a um cliente Fluig."""
    registry = ToolRegistry()

    async def check_connectivity() -> ToolResult:
        try:
            data = await client.get(endpoint("current_user"))
        except FluigError as exc:
            return ToolResult.failure(f"Sem conexao com o Fluig: {exc}")
        return ToolResult(
            ok=True,
            summary=_summarize("Conexao com o Fluig OK. Usuario da integracao", data),
            data=data,
        )

    async def get_user(login: str) -> ToolResult:
        try:
            data = await client.get(endpoint("user_by_login", login=login))
        except FluigError as exc:
            return ToolResult.failure(f"Nao foi possivel consultar o usuario {login}: {exc}")
        if not data:
            return ToolResult(ok=True, summary=f"Usuario {login} nao encontrado.", data=None)
        return ToolResult(ok=True, summary=_summarize(f"Usuario {login}", data), data=data)

    async def list_datasets() -> ToolResult:
        try:
            data = await client.get(endpoint("datasets"))
        except FluigError as exc:
            return ToolResult.failure(f"Nao foi possivel listar os datasets: {exc}")
        return ToolResult(ok=True, summary=_summarize("Datasets do ambiente", data), data=data)

    async def run_dataset(dataset_id: str, limit: int = 10) -> ToolResult:
        try:
            data = await client.get(
                endpoint("dataset_search"),
                params={"datasetId": dataset_id, "limit": min(limit, 50)},
            )
        except FluigError as exc:
            return ToolResult.failure(f"Falha ao executar o dataset {dataset_id}: {exc}")
        return ToolResult(
            ok=True,
            summary=_summarize(f"Retorno do dataset {dataset_id}", data),
            data=data,
        )

    async def get_process_instance(request_id: str) -> ToolResult:
        try:
            data = await client.get(endpoint("process_instance", request_id=request_id))
        except FluigError as exc:
            return ToolResult.failure(f"Falha ao consultar a solicitacao {request_id}: {exc}")
        return ToolResult(
            ok=True,
            summary=_summarize(f"Solicitacao {request_id}", data),
            data=data,
        )

    async def list_process_definitions() -> ToolResult:
        try:
            data = await client.get(endpoint("process_definitions"))
        except FluigError as exc:
            return ToolResult.failure(f"Falha ao listar os processos publicados: {exc}")
        return ToolResult(
            ok=True,
            summary=_summarize("Processos publicados", data),
            data=data,
        )

    registry.register(
        Tool(
            name="fluig_check_connectivity",
            description=(
                "Verifica se a integracao consegue autenticar no Fluig do cliente. "
                "Use antes de concluir que um problema e de permissao ou de ambiente."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=check_connectivity,
        )
    )

    registry.register(
        Tool(
            name="fluig_get_user",
            description=(
                "Consulta um usuario pelo login/matricula: se esta ativo, grupos e papeis. "
                "Use em problemas de acesso, permissao ou tarefa que nao aparece."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "login": {"type": "string", "description": "Login ou matricula do usuario."}
                },
                "required": ["login"],
            },
            handler=get_user,
        )
    )

    registry.register(
        Tool(
            name="fluig_list_datasets",
            description=(
                "Lista os datasets do ambiente. Use para confirmar se um dataset "
                "citado pelo cliente existe e esta publicado."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=list_datasets,
        )
    )

    registry.register(
        Tool(
            name="fluig_run_dataset",
            description=(
                "Executa um dataset e retorna as primeiras linhas. Use para reproduzir "
                "erro de dataset customizado ou verificar se ele devolve dados."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "Identificador do dataset."},
                    "limit": {
                        "type": "integer",
                        "description": "Numero maximo de linhas (maximo 50).",
                        "default": 10,
                    },
                },
                "required": ["dataset_id"],
            },
            handler=run_dataset,
        )
    )

    registry.register(
        Tool(
            name="fluig_get_process_instance",
            description=(
                "Detalha uma solicitacao de processo BPM: estado atual, atividade e "
                "responsavel. Use em chamados de processo travado ou fluxo incorreto."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "Numero da solicitacao informado pelo cliente.",
                    }
                },
                "required": ["request_id"],
            },
            handler=get_process_instance,
        )
    )

    registry.register(
        Tool(
            name="fluig_list_process_definitions",
            description=(
                "Lista os processos publicados no ambiente. Use para confirmar versao "
                "publicada de um processo citado no chamado."
            ),
            parameters={"type": "object", "properties": {}, "required": []},
            handler=list_process_definitions,
        )
    )

    return registry
