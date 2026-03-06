import json
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


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
