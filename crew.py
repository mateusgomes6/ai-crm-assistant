from crewai import Agent, Task, Crew, Process

lead_analyzer = Agent(
    role="Analista de Inteligência de Leads",
    goal="Analisar o perfil do lead, detectar intenção e pontos de dor usando dados históricos",
    tools=[rag_search_tool],
    llm=ChatOpenAI(model="gpt-4o")
)

sales_strategist = Agent(
    role="Estrategista de Vendas B2B",
    goal="Definir a melhor abordagem, canal, timing e ganchos de valor para este lead",
    tools=[rag_search_tool, win_rate_tool],
)

email_copywriter = Agent(
    role="Redator de E-mails",
    goal="Escrever um e-mail hiper-personalizado que converte",
    tools=[template_tool],
)

followup_manager = Agent(
    role="Orquestrador de Follow-up",
    goal="Criar sequência de follow-up automatizada e sincronizar com CRM",
    tools=[crm_tool],
)