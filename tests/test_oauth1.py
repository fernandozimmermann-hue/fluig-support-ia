import hashlib
import hmac
from base64 import b64encode

from fluig_support_ia.tools.oauth1 import (
    authorization_header,
    build_signature_base,
    normalize_url,
    percent_encode,
    sign,
)


def test_percent_encode_preserva_apenas_os_caracteres_nao_reservados():
    assert percent_encode("abc-._~") == "abc-._~"
    assert percent_encode("a b") == "a%20b"
    assert percent_encode("a/b") == "a%2Fb"
    assert percent_encode("a+b=c&d") == "a%2Bb%3Dc%26d"


def test_normalize_url_remove_query_e_fragmento():
    assert normalize_url("https://f.com/api/x?a=1#frag") == "https://f.com/api/x"


def test_normalize_url_remove_porta_padrao_mas_mantem_as_outras():
    assert normalize_url("https://f.com:443/api") == "https://f.com/api"
    assert normalize_url("http://f.com:80/api") == "http://f.com/api"
    assert normalize_url("https://f.com:8443/api") == "https://f.com:8443/api"


def test_base_string_tem_tres_partes_e_metodo_em_maiusculo():
    base = build_signature_base("get", "https://f.com/api", {"oauth_nonce": "abc"})
    parts = base.split("&")
    assert parts[0] == "GET"
    assert parts[1] == percent_encode("https://f.com/api")
    assert len(parts) == 3


def test_base_string_ordena_os_parametros_alfabeticamente():
    base = build_signature_base(
        "GET",
        "https://f.com/api",
        {"oauth_nonce": "n", "oauth_consumer_key": "k"},
        query_params={"zeta": "1", "alpha": "2"},
    )
    encoded = base.split("&")[2]
    assert encoded.index(percent_encode("alpha")) < encoded.index(
        percent_encode("oauth_consumer_key")
    )
    assert encoded.index(percent_encode("oauth_nonce")) < encoded.index(percent_encode("zeta"))


def test_base_string_inclui_parametros_da_query_da_url():
    base = build_signature_base("GET", "https://f.com/api?datasetId=ds1", {"oauth_nonce": "n"})
    assert percent_encode("datasetId") in base.split("&")[2]


def test_assinatura_bate_com_hmac_sha1_calculado_a_parte():
    base = "GET&https%3A%2F%2Ff.com%2Fapi&oauth_nonce%3Dabc"
    esperado = b64encode(
        hmac.new(b"csecret&tsecret", base.encode(), hashlib.sha1).digest()
    ).decode()
    assert sign(base, "csecret", "tsecret") == esperado


def test_header_e_deterministico_com_nonce_e_timestamp_fixos():
    kwargs = {
        "method": "GET",
        "url": "https://f.com/api/public/2.0/users/getCurrent",
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "at",
        "token_secret": "ts",
        "nonce": "fixed-nonce",
        "timestamp": "1700000000",
    }
    primeiro = authorization_header(**kwargs)
    assert primeiro == authorization_header(**kwargs)
    assert primeiro.startswith("OAuth ")
    for campo in (
        'oauth_consumer_key="ck"',
        'oauth_token="at"',
        'oauth_signature_method="HMAC-SHA1"',
        'oauth_nonce="fixed-nonce"',
        'oauth_timestamp="1700000000"',
        'oauth_version="1.0"',
        "oauth_signature=",
    ):
        assert campo in primeiro


def test_nonce_aleatorio_muda_a_assinatura():
    kwargs = {
        "method": "GET",
        "url": "https://f.com/api",
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "at",
        "token_secret": "ts",
    }
    assert authorization_header(**kwargs) != authorization_header(**kwargs)
