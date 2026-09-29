"""Cliente HTTP da API REST do Fluig."""

import logging
from typing import Any

import httpx

from fluig_support_ia.tools.oauth1 import authorization_header

logger = logging.getLogger(__name__)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class FluigError(RuntimeError):
    """Erro ao falar com a API do Fluig."""


class FluigClient:
    """Wrapper fino sobre a API REST do Fluig, com OAuth1 e modo somente leitura.

    O modo somente leitura (`read_only=True`, o padrao) e uma trava deliberada: o
    agente diagnostica ambientes de cliente e nao deve conseguir alterar dados.
    """

    def __init__(
        self,
        base_url: str,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        token_secret: str,
        timeout: float = 30.0,
        read_only: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("FLUIG_BASE_URL nao configurada.")

        self._base_url = base_url.rstrip("/")
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._access_token = access_token
        self._token_secret = token_secret
        self._read_only = read_only
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        """Fecha o cliente HTTP subjacente."""
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        """Executa uma chamada assinada e devolve o JSON da resposta."""
        method = method.upper()
        if self._read_only and method in _WRITE_METHODS:
            raise FluigError(f"Chamada {method} bloqueada: o cliente esta em modo somente leitura.")

        url = f"{self._base_url}/{path.lstrip('/')}"
        string_params = {k: str(v) for k, v in (params or {}).items() if v is not None}

        header = authorization_header(
            method=method,
            url=url,
            consumer_key=self._consumer_key,
            consumer_secret=self._consumer_secret,
            access_token=self._access_token,
            token_secret=self._token_secret,
            query_params=string_params,
        )

        try:
            response = await self._client.request(
                method,
                url,
                params=string_params or None,
                json=json_body,
                headers={"Authorization": header, "Accept": "application/json"},
            )
        except httpx.RequestError as exc:
            raise FluigError(f"Falha de rede ao chamar o Fluig: {exc}") from exc

        if response.status_code >= 400:
            raise FluigError(
                f"Fluig respondeu {response.status_code} em {method} {path}: {response.text[:500]}"
            )

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise FluigError(f"Resposta do Fluig nao e JSON valido em {path}") from exc

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Atalho para uma chamada GET."""
        return await self.request("GET", path, params=params)
