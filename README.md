# Fluig Support IA

Agente de IA que apoia a equipe técnica/N2 no suporte TOTVS Fluig. Para cada
chamado ele entrega duas coisas:

1. **Diagnóstico técnico** para o analista, com causa provável, como confirmar a
   hipótese e o que verificar no ambiente.
2. **Rascunho de resposta ao cliente**, já em linguagem de atendimento, para o
   analista revisar e enviar.

O agente combina duas fontes: a base de conhecimento indexada (documentação,
procedimentos e chamados antigos) e consultas ao vivo na API REST do Fluig do
cliente — essas consultas são **somente leitura** por padrão.

## Stack

| Camada | Escolha |
| --- | --- |
| Linguagem | Python 3.12 |
| API | FastAPI + Uvicorn |
| LLM | OpenAI (`gpt-4o`), atrás de uma interface trocável |
| Busca semântica | OpenAI embeddings + Postgres/pgvector |
| Portal | HTML/CSS/JS sem framework, servido pela própria API |
| Qualidade | pytest, ruff, mypy, GitHub Actions |

## Estrutura

```
src/fluig_support_ia/
├── config.py           Configuração via .env (pydantic-settings)
├── logging_setup.py    Logging com mascaramento de PII
├── agent/
│   ├── prompts.py      System prompt e montagem do contexto
│   ├── orchestrator.py Fluxo: RAG -> loop de ferramentas -> resposta
│   ├── parsing.py      Markdown do modelo -> campos estruturados
│   ├── redaction.py    Mascaramento de CPF/CNPJ/e-mail/segredos
│   └── schemas.py      Contratos de entrada e saída
├── llm/
│   ├── base.py         Interface LLMProvider
│   └── openai_provider.py
├── knowledge/
│   ├── loaders.py      Leitura de .md/.txt com front matter
│   ├── chunking.py     Divisão em trechos com sobreposição
│   ├── indexer.py      Indexação e busca
│   ├── store.py        InMemoryVectorStore e PgVectorStore
│   └── models.py
├── tools/
│   ├── registry.py     Registro e execução de ferramentas
│   ├── oauth1.py       Assinatura OAuth 1.0a (HMAC-SHA1)
│   ├── fluig_client.py Cliente HTTP do Fluig
│   ├── fluig_endpoints.py  Caminhos da API, centralizados
│   └── fluig_tools.py  Ferramentas de diagnóstico
├── api/
│   ├── app.py          Aplicação FastAPI
│   ├── deps.py         Wiring das dependências
│   └── routes/         chat, health, knowledge
└── web/                Portal (index.html, app.js, styles.css)
```

## Como rodar

### 1. Configurar

```bash
cp .env.example .env
# edite .env: OPENAI_API_KEY é obrigatória; as credenciais do Fluig são opcionais
```

Sem as credenciais do Fluig o agente sobe e funciona, apenas sem consultar o
ambiente do cliente.

### 2. Subir com Docker (recomendado)

```bash
docker compose up --build
```

A API e o portal ficam em <http://localhost:8000>. O Postgres com pgvector sobe
junto.

### 3. Ou rodar local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Para rodar sem Postgres, use VECTOR_STORE=in_memory no .env
uvicorn fluig_support_ia.api.app:app --reload
```

### 4. Indexar a base de conhecimento

Coloque os documentos em `data/knowledge/` como `.md` ou `.txt`. Front matter
opcional:

```markdown
---
title: Solicitação travada em uma atividade
url: https://tdn.totvs.com/...
---

Conteúdo do procedimento...
```

Depois:

```bash
python scripts/ingest.py
# ou, com a API no ar:
curl -X POST localhost:8000/api/knowledge/reindex -H 'Content-Type: application/json' -d '{}'
```

Só o `exemplo-*.md` é versionado; o resto de `data/knowledge/` está no
`.gitignore` para evitar comitar conteúdo de cliente.

## Endpoints

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/` | Portal web |
| GET | `/api/health` | Liveness |
| GET | `/api/ready` | O que está configurado, nº de trechos, ferramentas ativas |
| POST | `/api/chat` | Diagnóstico + rascunho ao cliente |
| POST | `/api/knowledge/reindex` | Reindexa `data/knowledge/` |
| POST | `/api/knowledge/search` | Busca semântica pura (depurar o RAG) |
| GET | `/api/knowledge/stats` | Total de trechos indexados |
| GET | `/docs` | OpenAPI/Swagger |

Exemplo:

```bash
curl -X POST localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Cliente diz que a solicitação 4471 travou na aprovação. O que verificar?",
    "ticket": {"ticket_id": "128394", "module": "BPM", "fluig_version": "1.8.1"}
  }'
```

## Ferramentas de diagnóstico

| Ferramenta | Uso |
| --- | --- |
| `fluig_check_connectivity` | Valida credenciais e conectividade |
| `fluig_get_user` | Usuário por login: ativo, grupos, papéis |
| `fluig_list_datasets` | Confirma se um dataset existe e está publicado |
| `fluig_run_dataset` | Executa um dataset e retorna as primeiras linhas |
| `fluig_get_process_instance` | Estado, atividade e responsável de uma solicitação |
| `fluig_list_process_definitions` | Processos publicados no ambiente |

`FLUIG_READ_ONLY=true` (padrão) bloqueia POST/PUT/PATCH/DELETE no cliente HTTP:
o agente diagnostica, não altera dados de cliente.

> **Antes de usar em produção:** os caminhos da API em
> `tools/fluig_endpoints.py` variam conforme a versão do Fluig e o que está
> licenciado no ambiente. Valide cada um contra a documentação da TOTVS (TDN) da
> sua versão e marque no arquivo o que foi confirmado.

## Segurança e privacidade

- `REDACT_PII=true` mascara CPF, CNPJ, e-mail e segredos antes de o texto ir ao
  LLM e aos logs (`agent/redaction.py`).
- O system prompt proíbe stack trace, host e credencial no rascunho ao cliente.
- **A API ainda não tem autenticação.** Antes de expor o portal fora da rede
  interna, coloque SSO/OAuth na frente — está na lista de próximos passos.

## Desenvolvimento

```bash
pytest -q              # testes
ruff check . && ruff format .
mypy
```

Os testes cobrem as partes determinísticas (chunking, redação de PII, parsing,
registro de ferramentas, OAuth1, store em memória) e o orquestrador com LLM e
ferramentas falsas — nenhum teste faz chamada de rede.

## Próximos passos sugeridos

1. Autenticação no portal (SSO da equipe) e registro de quem consultou o quê.
2. Ingestão automática dos chamados encerrados, que é a fonte mais rica de
   diagnóstico real.
3. Feedback do analista na resposta (útil / não útil) para medir qualidade.
4. Validar e marcar os endpoints em `fluig_endpoints.py` na versão do ambiente.
5. Cache de embeddings para reduzir custo em reindexações.
