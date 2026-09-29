"""Caminhos da API REST do Fluig usados pelas ferramentas.

ATENCAO: os caminhos abaixo variam conforme a versao do Fluig e o que esta
licenciado no ambiente. Eles estao centralizados aqui, e nao espalhados pelo
codigo, justamente para serem conferidos contra a documentacao da TOTVS (TDN) da
versao do seu ambiente antes de ir para producao.

Como validar um caminho rapidamente:
    curl -H "Authorization: OAuth ..." "$FLUIG_BASE_URL/<caminho>"

Marque como confirmado (# ok: 1.7.x) o que voce validar.
"""

from typing import Final

ENDPOINTS: Final[dict[str, str]] = {
    # Usuario autenticado; serve como teste de conectividade e credenciais.
    "current_user": "/api/public/2.0/users/getCurrent",
    # Consulta de usuario por login/matricula.
    "user_by_login": "/api/public/2.0/users/getByLogin/{login}",
    # Lista de datasets disponiveis no ambiente.
    "datasets": "/api/public/ecm/dataset/datasets",
    # Execucao de um dataset (diagnostico de dataset customizado).
    "dataset_search": "/api/public/ecm/dataset/search",
    # Solicitacao (instancia) de processo BPM.
    "process_instance": "/api/public/2.0/requests/{request_id}",
    # Definicoes de processo publicadas.
    "process_definitions": "/process-management/api/v2/processes",
    # Metadados de um documento do ECM.
    "document": "/api/public/2.0/documents/{document_id}",
}


def endpoint(name: str, **path_params: str) -> str:
    """Resolve um caminho pelo nome, substituindo os parametros do template."""
    try:
        template = ENDPOINTS[name]
    except KeyError as exc:
        raise KeyError(f"Endpoint desconhecido: {name}") from exc
    return template.format(**path_params)
