import os
import json
from typing import Type
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI

client = OpenAI()

def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])

class RAGInput(BaseModel):
    query: str = Field(description="Description of the lead to search similar profiles for")
    top_k: int = Field(default=5, description="Number of similar leads to return")

class RAGLeadTool(BaseTool):
    name: str = "search_similar_leads"
    description: str = (
        "Pesquisa o banco de dados histórico de leads usando similaridade semântica. "
        "Retorna leads passados semelhantes com as estratégias utilizadas e se converteram. "
        "Use isto para embasar sua análise e estratégia em dados históricos reais."
    )
    args_schema: Type[BaseModel] = RAGInput

    def _run(self, query: str, top_k: int = 5) -> str:
        embedding = get_embedding(query)

        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        id,
                        company_type,
                        contact_role,
                        segment,
                        pain_points,
                        strategy_used,
                        approach,
                        channel,
                        outcome,           -- 'won' | 'lost' | 'nurturing'
                        deal_value_usd,
                        days_to_close,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM leads
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, embedding, top_k))

                rows = cur.fetchall()

        if not rows:
            return json.dumps({"found": 0, "leads": []})

        leads = []
        for row in rows:
            leads.append({
                "company_type": row["company_type"],
                "contact_role": row["contact_role"],
                "segment": row["segment"],
                "pain_points": row["pain_points"],
                "strategy_used": row["strategy_used"],
                "approach": row["approach"],
                "channel": row["channel"],
                "outcome": row["outcome"],
                "deal_value_usd": row["deal_value_usd"],
                "days_to_close": row["days_to_close"],
                "similarity_score": round(float(row["similarity"]), 3),
            })

        won = [l for l in leads if l["outcome"] == "won"]
        win_rate = round(len(won) / len(leads) * 100) if leads else 0
        avg_deal = round(sum(l["deal_value_usd"] or 0 for l in won) / len(won)) if won else 0

        return json.dumps({
            "found": len(leads),
            "win_rate_pct": win_rate,
            "avg_deal_value_usd": avg_deal,
            "leads": leads,
        }, default=str)

class EnrichmentInput(BaseModel):
    company_domain: str = Field(description="Company domain e.g. 'finpay.io'")
    contact_email: str = Field(default="", description="Contact email if available")

class EnrichmentTool(BaseTool):
    name: str = "enrich_lead"
    description: str = (
        "Enriquece dados do lead com informações firmográficas: tamanho da empresa, "
        "estágio de funding, tech stack, sinais sociais. Usa stub Clearbit/Apollo — "
        "substitua pela chave de API real em produção."
    )
    args_schema: Type[BaseModel] = EnrichmentInput

    def _run(self, company_domain: str, contact_email: str = "") -> str:
        return json.dumps({
            "domain": company_domain,
            "employee_count_range": "51–200",
            "funding_stage": "Series A",
            "funding_total_usd": 12_000_000,
            "tech_stack": ["AWS", "Python", "Stripe", "Kubernetes"],
            "linkedin_followers": 3200,
            "founded_year": 2019,
            "hq_country": "BR",
            "note": "Stub data — configure CLEARBIT_KEY or APOLLO_KEY in .env for real enrichment",
        })