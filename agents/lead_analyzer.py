from crewai import Agent, LLM

llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.2)

lead_analyzer = Agent(
    role="Analista de Inteligência de Leads",
    goal=(
        "Analisar profundamente perfis de leads B2B. Identificar intenção de compra, "
        "pontos de dor, stack tecnológico, maturidade da empresa e sinais de orçamento. "
        "Usar dados históricos de leads similares para prever a probabilidade de conversão."
    ),
    backstory=(
        "Você é um analista sênior de inteligência de vendas B2B com mais de 10 anos "
        "identificando leads de alto valor em empresas SaaS. Você combina dados firmográficos, "
        "sinais comportamentais e padrões históricos alimentados por RAG para construir perfis "
        "de leads extremamente precisos. Você nunca adivinha — você raciocina a partir de evidências."
    ),
    tools=[],
    llm=llm,
    verbose=True,
    memory=False,
)


def build_analyze_task(lead_input: dict):
    from crewai import Task

    return Task(
        description=f"""
        Analise o seguinte lead e produza um relatório estruturado de inteligência.

        Dados do lead:
        - Tipo de empresa : {lead_input['company']}
        - Cargo do contato: {lead_input['role']}
        - Segmento        : {lead_input['segment']}
        - Notas extras    : {lead_input.get('notes', 'Nenhuma')}

        Etapas:
        1. Buscar leads similares na base de dados RAG (mesmo cargo + segmento).
        2. Identificar os 3 principais pontos de dor típicos para este perfil.
        3. Estimar intenção de compra (Baixa / Média / Alta) com justificativa.
        4. Atribuir um score de lead de 0 a 100 com base em: senioridade do cargo, adequação ao segmento, sinais de porte da empresa.
        5. Listar o provável stack tecnológico e os membros do comitê de compras.

        Saída em JSON:
        {{
          "lead_score": int,
          "intent": "Baixa|Média|Alta",
          "intent_reason": str,
          "pain_points": [str, str, str],
          "tech_stack_guess": [str],
          "buying_committee": [str],
          "similar_leads_found": int,
          "analyst_notes": str
        }}
        """,
        agent=lead_analyzer,
        expected_output="Objeto JSON com relatório de inteligência do lead",
    )