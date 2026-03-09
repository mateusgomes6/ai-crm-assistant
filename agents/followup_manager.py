from crewai import Agent, LLM
from pydantic import BaseModel, Field

llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.2, num_retries=3)

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

class FollowupStep(BaseModel):
    step: int = Field(description="Número da etapa")
    day: int = Field(description="Dia do touchpoint")
    channel: str = Field(description="Canal de contato")
    action: str = Field(description="Ação a ser realizada")
    message_hint: str = Field(description="Dica de mensagem para o SDR")
    priority: str = Field(description="Prioridade: alta, média ou baixa")
    crm_task_id: str = Field(default="", description="ID da tarefa no CRM")


class FollowupOutput(BaseModel):
    sequence: list[FollowupStep] = Field(description="Sequência de follow-up")
    total_touchpoints: int = Field(description="Total de touchpoints")
    estimated_reply_probability: str = Field(description="Probabilidade estimada de resposta")


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
        output_json=FollowupOutput,
    )