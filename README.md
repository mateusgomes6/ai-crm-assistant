# AI CRM Assistant

Pipeline inteligente de vendas B2B com agentes de IA que analisam leads, desenvolvem estratégias de vendas, geram cold emails personalizados e gerenciam sequências de follow-up.

## Arquitetura

O sistema orquestra 4 agentes de IA via **CrewAI**, cada um com uma responsabilidade específica:

| Agente | Função | Temperatura |
|--------|--------|-------------|
| **Lead Analyzer** | Score, intenção de compra, pain points, stack tecnológico | 0.2 |
| **Sales Strategist** | Abordagem, canal, timing, value hooks, objeções | 0.3 |
| **Email Copywriter** | Cold email personalizado com subject lines A/B | 0.7 |
| **Followup Manager** | Sequência de 4 toques multicanal | 0.2 |

## Tech Stack

- **Python** + **CrewAI** — Orquestração multi-agente
- **Groq API** (Llama 3.3 70B) — LLM
- **PostgreSQL** + **Psycopg2** — Persistência e auditoria
- **Sentence Transformers** (all-MiniLM-L6-v2) — Embeddings para busca semântica (RAG)
- **Streamlit** — Interface web
- **AWS Lambda** + **EventBridge** + **API Gateway** — Deploy serverless
- **HubSpot / Pipedrive** — Integração CRM

## Estrutura do Projeto

```
├── app.py                  # Interface Streamlit
├── crew.py                 # Orquestração CrewAI
├── database.py             # Schema PostgreSQL, RAG e CRUD
├── lambda_handler.py       # Handler AWS Lambda
├── agents/
│   ├── lead_analyzer.py    # Agente de análise de leads
│   ├── sales_strategist.py # Agente de estratégia de vendas
│   ├── email_copywriter.py # Agente de copywriting
│   └── followup_manager.py # Agente de follow-up
└── tools/
    ├── rag_tool.py         # Busca semântica de leads históricos
    ├── crm_tool.py         # Integração HubSpot/Pipedrive
    └── enrichment_tool.py  # Enriquecimento de leads
```

## Setup

### Pré-requisitos

- Python 3.8+
- PostgreSQL

### Instalação

```bash
git clone https://github.com/seu-usuario/ai-crm-assistant.git
cd ai-crm-assistant
pip install crewai groq psycopg2-binary streamlit sentence-transformers
```

### Inicializar o Banco de Dados

```bash
python -c "from database import create_schema; create_schema()"
```

### Executar

```bash
streamlit run app.py
```

Acesse em `http://localhost:8501`.

## Fluxo de Execução

1. **Input** — Lead submetido via formulário Streamlit ou webhook API
2. **Cache** — Retorna resultado em cache se o lead foi analisado nas últimas 24h
3. **Pipeline** — Execução sequencial dos 4 agentes
4. **Persistência** — Resultados salvos no PostgreSQL com embeddings
5. **CRM Sync** — Tasks de follow-up enviadas ao HubSpot/Pipedrive (opcional)

## Deploy (AWS Lambda)

O projeto suporta 3 fontes de evento:

- **API Gateway** — `POST /analyze-lead` com payload JSON
- **EventBridge** — Processamento batch de leads pendentes
- **Invocação direta** — Chamadas internas entre serviços