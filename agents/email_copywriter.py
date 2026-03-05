from crewai import Agent
from tools.rag_tool import RAGLeadTool
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

email_copywriter = Agent(
    role="Copywriter de E-mails B2B",
    goal=(
        "Escrever e-mails outbound hiperpersonalizados que pareçam humanos, não automatizados. "
        "Cada e-mail deve: abrir com um insight relevante sobre o prospect, "
        "entregar um gancho de valor claro e terminar com um CTA sem fricção. "
        "Sem jargões. Sem enrolação. Menos de 150 palavras para cold email."
    ),
    backstory=(
        "Você é um copywriter de conversão que já escreveu sequências outbound com taxa de resposta acima de 40%. "
        "Você entende que CTOs odeiam receber vendas — eles querem ser compreendidos. "
        "Você nunca começa um e-mail com 'Espero que este e-mail te encontre bem'. "
        "Você escreve como um colega perspicaz, não como um vendedor."
    ),
    tools=[RAGLeadTool()],
    llm=llm,
    verbose=True,
    memory=True,
)

def build_email_task(lead_input: dict):
    from crewai import Task

    return Task(
        description=f"""
        Escreva um e-mail cold outbound para:
        - Destinatário: {lead_input['role']} em uma empresa de {lead_input['segment']}
        - Produto     : {lead_input['company']}
        - Tom da estratégia: use o tom que o Estrategista de Vendas definiu

        Regras:
        - Assunto: menos de 8 palavras, curiosidade ou especificidade — sem clickbait
        - Linha de abertura: referencie algo VERDADEIRO sobre o cargo/segmento (sem personalização falsa)
        - Corpo: NO MÁXIMO UM gancho de valor, estruturado como dor → solução → prova/métrica
        - CTA: peça UMA coisa específica (call de 15 min, responder com uma pergunta, etc.)
        - Total do corpo: 100–150 palavras
        - PROIBIDO: "Espero que este e-mail te encontre bem", "pergunta rápida", "só dando um follow-up",
                     "sinergia", "alavancar", "game-changer", "revolucionário"

        Escreva também 2 variantes A/B de assunto.

        Saída em JSON:
        {{
          "subject": str,
          "subject_variant_a": str,
          "subject_variant_b": str,
          "body": str,
          "word_count": int,
          "personalization_hooks_used": [str],
          "cta": str
        }}
        """,
        agent=email_copywriter,
        expected_output="JSON com assunto do e-mail, corpo e variantes A/B",
    )