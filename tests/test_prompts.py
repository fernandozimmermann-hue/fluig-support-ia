from fluig_support_ia.agent.prompts import (
    build_messages,
    format_knowledge_context,
    format_ticket_context,
)
from fluig_support_ia.agent.schemas import Message, TicketContext


def test_contexto_do_chamado_vazio_quando_nao_ha_dados():
    assert format_ticket_context(None) == ""
    assert format_ticket_context(TicketContext()) == ""


def test_contexto_do_chamado_lista_apenas_os_campos_preenchidos():
    bloco = format_ticket_context(TicketContext(ticket_id="123", module="BPM"))
    assert "Chamado: 123" in bloco
    assert "Modulo: BPM" in bloco
    assert "Cliente" not in bloco


def test_log_do_chamado_vai_em_bloco_de_codigo():
    bloco = format_ticket_context(TicketContext(error_log="java.lang.NullPointerException"))
    assert "```" in bloco
    assert "NullPointerException" in bloco


def test_contexto_sem_trecho_avisa_o_modelo():
    texto = format_knowledge_context([])
    assert "nenhum trecho relevante" in texto


def test_contexto_marca_a_fonte_de_cada_trecho():
    texto = format_knowledge_context([("a.md", "conteudo A"), ("b.md", "conteudo B")])
    assert "[fonte: a.md]" in texto
    assert "[fonte: b.md]" in texto


def test_mensagens_comecam_com_o_system_prompt():
    mensagens = build_messages("Por que travou?", [], None, [])
    assert mensagens[0]["role"] == "system"
    assert "N2" in mensagens[0]["content"]


def test_mensagens_preservam_o_historico_na_ordem():
    historico = [
        Message(role="user", content="primeira"),
        Message(role="assistant", content="resposta"),
    ]
    mensagens = build_messages("segunda", historico, None, [])
    assert [m["role"] for m in mensagens] == ["system", "user", "assistant", "user"]
    assert mensagens[1]["content"] == "primeira"


def test_ultima_mensagem_reune_chamado_contexto_e_pergunta():
    mensagens = build_messages(
        "Por que travou?",
        [],
        TicketContext(ticket_id="987"),
        [("a.md", "conteudo A")],
    )
    ultima = mensagens[-1]["content"]
    assert "Chamado: 987" in ultima
    assert "[fonte: a.md]" in ultima
    assert "Por que travou?" in ultima
