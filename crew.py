import json
import re
from crewai import Crew, Process

from agents.lead_analyzer   import lead_analyzer,   build_analyze_task
from agents.sales_strategist import sales_strategist, build_strategy_task
from agents.email_copywriter import email_copywriter, build_email_task
from agents.followup_manager import followup_manager, build_followup_task


def _parse_task_output(task_output) -> dict:
    """Extract a dict from a CrewAI task output, trying multiple strategies."""
    if not task_output:
        return {}

    # 1. Try json_dict (populated when output_json is set)
    if hasattr(task_output, "json_dict") and isinstance(task_output.json_dict, dict):
        return task_output.json_dict

    # 2. Try pydantic model
    if hasattr(task_output, "pydantic") and task_output.pydantic:
        return task_output.pydantic.model_dump()

    # 3. Try parsing raw as JSON directly
    raw = getattr(task_output, "raw", None)
    if not raw:
        return {}

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # 4. Extract JSON object from mixed text (e.g., reasoning + JSON)
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


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
        max_rpm=10,
    )

    crew.kickoff()

    return {
        "lead_input" : lead_input,
        "analysis"   : _parse_task_output(t1.output),
        "strategy"   : _parse_task_output(t2.output),
        "email"      : _parse_task_output(t3.output),
        "followups"  : _parse_task_output(t4.output),
    }
