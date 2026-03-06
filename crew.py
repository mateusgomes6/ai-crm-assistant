import json
from crewai import Crew, Process

from agents.lead_analyzer   import lead_analyzer,   build_analyze_task
from agents.sales_strategist import sales_strategist, build_strategy_task
from agents.email_copywriter import email_copywriter, build_email_task
from agents.followup_manager import followup_manager, build_followup_task


def run_crew(lead_input: dict) -> dict:
    t1 = build_analyze_task(lead_input)
    t2 = build_strategy_task(lead_input)
    t3 = build_email_task(lead_input)
    t4 = build_followup_task(lead_input)

    crew = Crew(
        agents=[lead_analyzer, sales_strategist, email_copywriter, followup_manager],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential,
        verbose=True,
        memory=False,
    )

    raw_result = crew.kickoff()

    try:
        analysis  = json.loads(t1.output.raw)
        strategy  = json.loads(t2.output.raw)
        email     = json.loads(t3.output.raw)
        followups = json.loads(t4.output.raw)
    except (json.JSONDecodeError, AttributeError):
        analysis  = t1.output.raw if t1.output else {}
        strategy  = t2.output.raw if t2.output else {}
        email     = t3.output.raw if t3.output else {}
        followups = t4.output.raw if t4.output else {}

    return {
        "lead_input" : lead_input,
        "analysis"   : analysis,
        "strategy"   : strategy,
        "email"      : email,
        "followups"  : followups,
    }
