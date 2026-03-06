import json
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from database import get_embedding, search_similar_leads

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
        rows = search_similar_leads(embedding, top_k=top_k)

        if not rows:
            return json.dumps({"found": 0, "leads": []})

        leads = []
        for row in rows:
            leads.append({
                "company": row.get("company"),
                "contact_role": row.get("contact_role"),
                "segment": row.get("segment"),
                "pain_points": row.get("pain_points"),
                "strategy_used": row.get("strategy_used"),
                "approach": row.get("approach"),
                "channel": row.get("channel"),
                "outcome": row.get("outcome"),
                "deal_value_usd": row.get("deal_value_usd"),
                "days_to_close": row.get("days_to_close"),
                "similarity_score": round(float(row.get("similarity", 0)), 3),
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