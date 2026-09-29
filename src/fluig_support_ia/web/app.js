"use strict";

const $ = (id) => document.getElementById(id);

const els = {
  form: $("form"),
  submit: $("submit"),
  status: $("status"),
  empty: $("empty"),
  error: $("error"),
  result: $("result"),
  diagnosis: $("diagnosis"),
  draft: $("draft"),
  nextSteps: $("next-steps"),
  stepsBlock: $("steps-block"),
  confidence: $("confidence"),
  model: $("model"),
  toolCalls: $("tool-calls"),
  toolsCount: $("tools-count"),
  toolsBlock: $("tools-block"),
  citations: $("citations"),
  citationsCount: $("citations-count"),
  citationsBlock: $("citations-block"),
};

/** Consulta /api/ready e reflete o estado do ambiente no cabecalho. */
async function loadStatus() {
  try {
    const response = await fetch("/api/ready");
    const data = await response.json();

    const problems = [];
    if (!data.openai_configured) problems.push("OpenAI nao configurada");
    if (!data.fluig_configured) problems.push("Fluig nao configurado");
    if (data.knowledge && data.knowledge.ok === false) problems.push("base de conhecimento fora");

    const chunks = (data.knowledge && data.knowledge.chunks) || 0;
    if (problems.length === 0) {
      els.status.textContent = `ambiente ok \u00b7 ${chunks} trechos \u00b7 ${data.tools.length} ferramentas`;
      els.status.dataset.state = "ok";
    } else {
      els.status.textContent = problems.join(" \u00b7 ");
      els.status.dataset.state = "warn";
    }
  } catch {
    els.status.textContent = "API indisponivel";
    els.status.dataset.state = "err";
  }
}

/** Monta o corpo da requisicao a partir do formulario. */
function buildPayload(formData) {
  const ticketFields = ["ticket_id", "customer", "fluig_version", "module", "error_log"];
  const ticket = {};
  let hasTicket = false;

  for (const field of ticketFields) {
    const value = (formData.get(field) || "").trim();
    if (value) {
      ticket[field] = value;
      hasTicket = true;
    }
  }

  return {
    question: (formData.get("question") || "").trim(),
    use_tools: formData.get("use_tools") === "on",
    ticket: hasTicket ? ticket : null,
    history: [],
  };
}

function renderNextSteps(steps) {
  els.nextSteps.replaceChildren();
  els.stepsBlock.hidden = steps.length === 0;
  for (const step of steps) {
    const li = document.createElement("li");
    li.textContent = step;
    els.nextSteps.appendChild(li);
  }
}

function renderToolCalls(calls) {
  els.toolCalls.replaceChildren();
  els.toolsCount.textContent = String(calls.length);
  els.toolsBlock.hidden = calls.length === 0;

  for (const call of calls) {
    const wrapper = document.createElement("div");
    wrapper.className = "toolcall";

    const head = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = call.name;
    const flag = document.createElement("span");
    flag.className = call.ok ? "tool-ok" : "tool-fail";
    flag.textContent = call.ok ? " \u2713" : " \u2717 falhou";
    head.append(name, flag);

    const args = document.createElement("div");
    args.className = "muted";
    args.textContent = JSON.stringify(call.arguments);

    const output = document.createElement("pre");
    output.textContent = call.summary;

    wrapper.append(head, args, output);
    els.toolCalls.appendChild(wrapper);
  }
}

function renderCitations(citations) {
  els.citations.replaceChildren();
  els.citationsCount.textContent = String(citations.length);
  els.citationsBlock.hidden = citations.length === 0;

  for (const citation of citations) {
    const wrapper = document.createElement("div");
    wrapper.className = "citation";

    const head = document.createElement("div");
    head.className = "citation-head";

    const label = citation.title || citation.source;
    if (citation.url) {
      const link = document.createElement("a");
      link.href = citation.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = label;
      head.appendChild(link);
    } else {
      const strong = document.createElement("strong");
      strong.textContent = label;
      head.appendChild(strong);
    }

    const score = document.createElement("span");
    score.className = "muted";
    score.textContent = `${citation.source} \u00b7 score ${citation.score}`;
    head.appendChild(score);

    const excerpt = document.createElement("p");
    excerpt.className = "excerpt";
    excerpt.textContent = citation.excerpt;

    wrapper.append(head, excerpt);
    els.citations.appendChild(wrapper);
  }
}

function renderResult(data) {
  els.diagnosis.textContent = data.diagnosis || "(vazio)";
  els.draft.textContent = data.draft_reply || "(o modelo nao gerou rascunho)";
  els.confidence.textContent = `confianca ${data.confidence}`;
  els.confidence.dataset.level = data.confidence;
  els.model.textContent = data.model ? `modelo ${data.model}` : "";

  renderNextSteps(data.next_steps || []);
  renderToolCalls(data.tool_calls || []);
  renderCitations(data.citations || []);

  els.empty.hidden = true;
  els.error.hidden = true;
  els.result.hidden = false;
}

function showError(message) {
  els.error.textContent = message;
  els.error.hidden = false;
  els.result.hidden = true;
  els.empty.hidden = true;
}

els.form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = buildPayload(new FormData(els.form));
  if (!payload.question) {
    showError("Descreva a pergunta ou o problema antes de analisar.");
    return;
  }

  els.submit.disabled = true;
  els.submit.textContent = "Analisando...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = (data && data.detail) || response.statusText;
      showError(`Erro ${response.status}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`);
      return;
    }
    renderResult(data);
  } catch (err) {
    showError(`Falha de rede: ${err.message}`);
  } finally {
    els.submit.disabled = false;
    els.submit.textContent = "Analisar";
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest(".copy");
  if (!button) return;

  const target = button.dataset.copy === "draft" ? els.draft : els.diagnosis;
  try {
    await navigator.clipboard.writeText(target.textContent);
    const original = button.textContent;
    button.textContent = "Copiado";
    setTimeout(() => {
      button.textContent = original;
    }, 1400);
  } catch {
    showError("Nao foi possivel copiar (o navegador exige HTTPS ou permissao).");
  }
});

loadStatus();
