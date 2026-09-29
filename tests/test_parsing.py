from fluig_support_ia.agent.parsing import parse_agent_output, parse_confidence, split_sections

RESPOSTA = """\
## Diagnostico
O responsavel da atividade esta inativo [fonte: exemplo.md].

## Proximos passos
- Verificar o usuario no Identity
1. Reativar ou substituir o responsavel

## Rascunho ao cliente
Ola, identificamos a causa e vamos ajustar o responsavel da atividade.

## Confianca
Alta - confirmado pela consulta ao ambiente.
"""


def test_divide_as_secoes_por_titulo():
    sections = split_sections(RESPOSTA)
    assert set(sections) == {"diagnostico", "proximos passos", "rascunho ao cliente", "confianca"}


def test_extrai_diagnostico_e_rascunho():
    parsed = parse_agent_output(RESPOSTA)
    assert "responsavel da atividade esta inativo" in parsed["diagnosis"]
    assert parsed["draft_reply"].startswith("Ola, identificamos")


def test_extrai_passos_removendo_marcadores():
    parsed = parse_agent_output(RESPOSTA)
    assert parsed["next_steps"] == [
        "Verificar o usuario no Identity",
        "Reativar ou substituir o responsavel",
    ]


def test_extrai_confianca_ignorando_acento_e_caixa():
    parsed = parse_agent_output(RESPOSTA)
    assert parsed["confidence"] == "alta"
    assert parse_confidence("Média - faltou validar o log") == "media"
    assert parse_confidence("BAIXA") == "baixa"


def test_confianca_desconhecida_cai_para_media():
    assert parse_confidence("sem opiniao") == "media"


def test_texto_sem_formato_preserva_tudo_no_diagnostico():
    parsed = parse_agent_output("Nao consegui identificar a causa.")
    assert parsed["diagnosis"] == "Nao consegui identificar a causa."
    assert parsed["draft_reply"] == ""
    assert parsed["confidence"] == "baixa"


def test_apenas_rascunho_ainda_e_aproveitado():
    parsed = parse_agent_output("## Rascunho ao cliente\nSegue a orientacao.")
    assert parsed["draft_reply"] == "Segue a orientacao."
