from crewai import Agent, LLM

llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.3)

sales_strategist = Agent(
    role="Estrategista de Vendas B2B",
    goal=(
        "Usando o relatório de análise do lead, definir a estratégia de vendas ideal: "
        "melhor canal, estilo de abordagem, timing, ganchos de proposta de valor e tratamento de objeções. "
        "Priorizar estratégias que historicamente fecharam negócios para perfis similares."
    ),
    backstory=(
        "Você é um estrategista de vendas B2B de alta performance que já fechou negócios de 7 dígitos em "
        "empresas SaaS. Você sabe que um CTO de uma fintech pensa completamente diferente de "
        "um VP de Vendas de um e-commerce. Você personaliza cada estratégia para a psicologia do comprador, "
        "seus incentivos, seus medos e o que sucesso significa para eles."
    ),
    tools=[],
    llm=llm,
    verbose=True,
    memory=False,
)

def build_strategy_task(lead_input: dict):
    from crewai import Task

    return Task(
        description=f"""
        Com base na análise de lead já realizada para:
        - Cargo   : {lead_input['role']}
        - Segmento: {lead_input['segment']}
        - Empresa : {lead_input['company']}

        Construa uma estratégia de vendas completa. Use a ferramenta RAG para verificar quais abordagens
        funcionaram melhor para negócios fechados com perfis similares.

        Defina:
        1. TIPO DE ABORDAGEM: consultiva / product-led / orientada a ROI / demo técnica / briefing executivo
        2. CANAL PRIMÁRIO: cold email / LinkedIn / indicação / telefone / pago / evento
        3. MELHOR TIMING: dia da semana, horário do dia e justificativa
        4. TOM: formal / casual / técnico / storytelling
        5. TOP 3 GANCHOS DE VALOR: dor específica → ganho específico
        6. TOP 2 OBJEÇÕES + tratamentos
        7. CALL TO ACTION: exatamente o que pedir na primeira mensagem

        Saída em JSON:
        {{
          "approach": str,
          "primary_channel": str,
          "secondary_channel": str,
          "best_day": str,
          "best_time": str,
          "tone": str,
          "value_hooks": [
            {{"pain": str, "gain": str, "metric": str}},
            {{"pain": str, "gain": str, "metric": str}},
            {{"pain": str, "gain": str, "metric": str}}
          ],
          "objections": [
            {{"objection": str, "handler": str}},
            {{"objection": str, "handler": str}}
          ],
          "cta": str,
          "strategy_confidence": int  // 0–100
        }}
        """,
        agent=sales_strategist,
        expected_output="Objeto JSON com estratégia de vendas completa",
    )