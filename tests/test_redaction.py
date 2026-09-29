from fluig_support_ia.agent.redaction import MASK, redact, redact_if


def test_mascara_cpf_com_e_sem_formatacao():
    assert redact("cliente 123.456.789-09 abriu") == f"cliente {MASK} abriu"
    assert redact("cliente 12345678909 abriu") == f"cliente {MASK} abriu"


def test_mascara_cnpj():
    assert redact("CNPJ 12.345.678/0001-95") == f"CNPJ {MASK}"


def test_mascara_email():
    assert redact("contato joao.silva@empresa.com.br") == f"contato {MASK}"


def test_mascara_senha_preservando_o_rotulo():
    assert redact("senha=Abc12345") == f"senha={MASK}"


def test_mascara_segredo_em_json():
    resultado = redact('{"password": "segredo123"}')
    assert "segredo123" not in resultado
    assert "password" in resultado
    assert MASK in resultado


def test_mascara_token_de_authorization():
    resultado = redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9")
    assert "eyJhbGciOiJIUzI1NiJ9" not in resultado
    assert MASK in resultado


def test_nao_altera_texto_sem_dado_sensivel():
    texto = "A solicitacao 4471 travou na atividade de aprovacao."
    assert redact(texto) == texto


def test_texto_vazio():
    assert redact("") == ""


def test_redact_if_desligado_nao_altera():
    assert redact_if("senha=abc123", enabled=False) == "senha=abc123"
