from crewai import Agent, LLM

llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.2)

followup_manager = Agent(
    role="Gerente de Sequência de Follow-up",
    goal=(
        "Projetar e registrar uma sequência de follow-up multi-toque no CRM. "
        "Cada ponto de contato deve usar um canal diferente e agregar novo valor — "
        "nunca apenas 'verificando'. Sincronizar todas as tarefas/lembretes automaticamente."
    ),
    backstory=(
        "Você é um especialista em operações de vendas que sabe que 80% dos negócios fecham após "
        "o 5º ponto de contato. Você projeta sequências de follow-up que parecem um "
        "arco natural de conversa, não um disparo de spam. Cada mensagem escala valor "
        "e urgência sem ser insistente. Você sempre sincroniza com o CRM para que nada passe despercebido."
    ),
    tools=[],
    llm=llm,
    verbose=True,
    memory=False,
)

def build_followup_task(lead_input: dict):
    from crewai import Task

    return Task(
        description=f"""
        Projete uma sequência de follow-up de 4 pontos de contato para:
        - Lead    : {lead_input['role']} na {lead_input['company']} ({lead_input['segment']})
        - Objetivo: Agendar uma call de descoberta

        Regras para cada ponto de contato:
        - Canal diferente do anterior (email → LinkedIn → telefone → email)
        - Cada um referencia ou complementa o anterior (continuidade)
        - Urgência/valor crescente, nunca apenas "dando um follow-up"
        - Incluir uma dica específica de ação/mensagem para o SDR

        Em seguida, use a ferramenta CRM para registrar todas as 4 tarefas com:
        - due_date (Dia 1, 3, 7, 14 a partir de hoje)
        - canal
        - descrição da tarefa
        - prioridade (alta/média/baixa)

        Saída em JSON:
        {{
          "sequence": [
            {{
              "step": 1,
              "day": 1,
              "channel": str,
              "action": str,
              "message_hint": str,
              "priority": str,
              "crm_task_id": str  // retornado pela ferramenta CRM
            }},
            // ... etapas 2, 3, 4
          ],
          "total_touchpoints": 4,
          "estimated_reply_probability": str
        }}
        """,
        agent=followup_manager,
        expected_output="JSON com sequência de follow-up e IDs das tarefas no CRM",
    )