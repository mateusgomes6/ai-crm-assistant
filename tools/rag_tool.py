from crewai_tools import BaseTool

class RAGLeadTool(BaseTool):
    name = "search_similar_leads"
    description = "Find similar leads and past strategies that worked"

    def _run(self, lead_description: str) -> str:
        embedding = get_embedding(lead_description)  # OpenAI
        results = db.query("""
            SELECT company, role, strategy_used, outcome
            FROM leads ORDER BY embedding <=> %s LIMIT 5
        """, [embedding])
        return format_results(results)