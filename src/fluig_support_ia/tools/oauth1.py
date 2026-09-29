"""Assinatura OAuth 1.0a (HMAC-SHA1), que e o padrao da API REST do Fluig.

Implementado com a biblioteca padrao para evitar uma dependencia extra e para que
a geracao da assinatura possa ser verificada por testes deterministicos.

Referencia: RFC 5849, secao 3.
"""

import hashlib
import hmac
import secrets
import time
from base64 import b64encode
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit


def percent_encode(value: str) -> str:
    """Codificacao percentual exigida pelo OAuth (RFC 5849, secao 3.6)."""
    return quote(str(value), safe="-._~")


def normalize_url(url: str) -> str:
    """Remove query string, fragmento e porta padrao da URL base da assinatura."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"
    return urlunsplit((scheme, host, parts.path, "", ""))


def build_signature_base(
    method: str,
    url: str,
    oauth_params: dict[str, str],
    query_params: dict[str, str] | None = None,
) -> str:
    """Monta a string base da assinatura."""
    collected: list[tuple[str, str]] = list(oauth_params.items())
    collected.extend(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    if query_params:
        collected.extend((key, str(value)) for key, value in query_params.items())

    encoded = sorted((percent_encode(k), percent_encode(v)) for k, v in collected)
    param_string = "&".join(f"{k}={v}" for k, v in encoded)

    return "&".join(
        [
            method.upper(),
            percent_encode(normalize_url(url)),
            percent_encode(param_string),
        ]
    )


def sign(base_string: str, consumer_secret: str, token_secret: str) -> str:
    """Calcula a assinatura HMAC-SHA1 em base64."""
    key = f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}".encode()
    digest = hmac.new(key, base_string.encode(), hashlib.sha1).digest()
    return b64encode(digest).decode()


def authorization_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    token_secret: str,
    query_params: dict[str, str] | None = None,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> str:
    """Gera o valor completo do header `Authorization: OAuth ...`.

    `nonce` e `timestamp` sao parametros para permitir testes deterministicos; em
    producao deixe-os como None.
    """
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_token": access_token,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_version": "1.0",
    }

    base = build_signature_base(method, url, oauth_params, query_params)
    oauth_params["oauth_signature"] = sign(base, consumer_secret, token_secret)

    pairs = ", ".join(
        f'{percent_encode(k)}="{percent_encode(v)}"' for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {pairs}"
