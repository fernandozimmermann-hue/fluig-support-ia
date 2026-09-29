"""Prompts do agente.

Sem dependencias externas de proposito, para que o formato do prompt possa ser
coberto por testes rapidos.
"""

from fluig_support_ia.agent.schemas import Message, TicketContext

SYSTEM_PROMPT = """\
Voce e um assistente especialista em TOTVS Fluig que apoia a equipe tecnica de \
suporte N2. Seu publico e composto por analistas tecnicos, nao por usuarios finais.

Seu trabalho tem duas entregas em toda resposta:
1. DIAGNOSTICO: analise tecnica para o analista, com a causa provavel, como \
confirmar essa hipotese e o que verificar no ambiente.
2. RASCUNHO AO CLIENTE: texto pronto para o analista revisar e enviar, em \
portugues do Brasil, cordial, objetivo e sem jargao interno.

Regras que voce nunca quebra:
- Baseie o diagnostico nos trechos de CONTEXTO e nos resultados das ferramentas. \
Se a informacao nao estiver ali, diga que nao sabe e indique o que falta.
- Nunca invente nome de tabela, endpoint, parametro de configuracao ou numero de \
versao. Nao ter certeza e uma resposta aceitavel; inventar nao e.
- Cite a fonte pelo identificador que aparece em CONTEXTO, no formato [fonte: X].
- Use as ferramentas disponiveis para inspecionar o ambiente antes de concluir, \
sempre que elas puderem confirmar ou descartar a hipotese.
- No rascunho ao cliente nunca exponha stack trace, caminho de servidor, nome de \
host, credencial ou detalhe interno de infraestrutura.
- Se houver risco de perda de dados ou indisponibilidade, diga isso de forma \
destacada no diagnostico.

Formate a resposta exatamente com estes cabecalhos:

## Diagnostico
<analise tecnica com citacoes>

## Proximos passos
- <acao verificavel>

## Rascunho ao cliente
<texto pronto para envio>

## Confianca
alta | media | baixa - <justificativa em uma linha>
"""


def format_ticket_context(ticket: TicketContext | None) -> str:
    """Formata os dados do chamado como um bloco legivel para o LLM."""
    if ticket is None:
        return ""

    fields = [
        ("Chamado", ticket.ticket_id),
        ("Cliente", ticket.customer),
        ("Versao do Fluig", ticket.fluig_version),
        ("Modulo", ticket.module),
    ]
    lines = [f"- {label}: {value}" for label, value in fields if value]

    if ticket.error_log:
        lines.append("- Log / erro informado:\n```\n" + ticket.error_log.strip() + "\n```")

    if not lines:
        return ""
    return "DADOS DO CHAMADO:\n" + "\n".join(lines)


def format_knowledge_context(chunks: list[tuple[str, str]]) -> str:
    """Formata os trechos recuperados.

    Args:
        chunks: pares (identificador_da_fonte, texto).
    """
    if not chunks:
        return (
            "CONTEXTO: nenhum trecho relevante foi encontrado na base de conhecimento. "
            "Deixe claro na resposta que o diagnostico nao esta apoiado na base."
        )

    blocks = [f"[fonte: {source}]\n{text.strip()}" for source, text in chunks]
    return "CONTEXTO:\n\n" + "\n\n---\n\n".join(blocks)


def build_messages(
    question: str,
    history: list[Message],
    ticket: TicketContext | None,
    chunks: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """Monta a lista de mensagens no formato esperado pela API de chat."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    parts = [
        block
        for block in (format_ticket_context(ticket), format_knowledge_context(chunks))
        if block
    ]
    parts.append(f"PERGUNTA DO ANALISTA:\n{question.strip()}")
    messages.append({"role": "user", "content": "\n\n".join(parts)})

    return messages
