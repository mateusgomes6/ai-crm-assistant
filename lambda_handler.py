import json
import os
import logging
import traceback
from datetime import datetime, timezone

from crew import run_crew
from database import save_lead_result, get_lead_by_email, mark_lead_processed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REQUIRED_FIELDS = {"company", "role", "segment"}
MAX_BODY_BYTES   = 64_000   # 64 KB guard

def handler(event: dict, context) -> dict:
    """Unified handler: detects event source and routes accordingly.

    Supported sources:
      1. API Gateway (HTTP webhook from CRM or frontend)
      2. EventBridge (scheduled batch re-run)
      3. Direct Lambda invocation (testing / internal calls)
    """
    logger.info("Event received: %s", json.dumps(event)[:500])

    try:
        source = detect_source(event)

        if source == "api_gateway":
            return handle_api_gateway(event)

        if source == "eventbridge":
            return handle_eventbridge(event)

        return handle_direct(event)

    except Exception as exc:
        logger.error("Unhandled exception: %s", traceback.format_exc())
        return error_response(500, f"Internal error: {str(exc)}")

def handle_api_gateway(event: dict) -> dict:
    """Handles POST /analyze-lead from API Gateway."""

    raw_body = event.get("body", "{}")
    if event.get("isBase64Encoded"):
        import base64
        raw_body = base64.b64decode(raw_body).decode()

    if len(raw_body.encode()) > MAX_BODY_BYTES:
        return error_response(413, "Request body too large")

    try:
        lead_input = json.loads(raw_body)
    except json.JSONDecodeError:
        return error_response(400, "Invalid JSON body")

    missing = REQUIRED_FIELDS - set(lead_input.keys())
    if missing:
        return error_response(400, f"Missing required fields: {sorted(missing)}")

    email = lead_input.get("email")
    if email:
        existing = get_lead_by_email(email, max_age_hours=24)
        if existing:
            logger.info("Lead %s already processed. Returning cached result.", email)
            return success_response(existing, cached=True)

    result = run_pipeline(lead_input)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*"),
        },
        "body": json.dumps(result, ensure_ascii=False, default=str),
    }


def handle_eventbridge(event: dict) -> dict:
    logger.info("EventBridge trigger: %s", event.get("detail-type"))

    from database import get_pending_leads

    pending = get_pending_leads(older_than_hours=2, limit=10)
    logger.info("Found %d pending leads to process", len(pending))

    results = []
    for lead in pending:
        try:
            result = run_pipeline(lead)
            results.append({"email": lead.get("email"), "status": "ok"})
        except Exception as exc:
            logger.error("Failed for %s: %s", lead.get("email"), exc)
            results.append({"email": lead.get("email"), "status": "error", "error": str(exc)})

    return {"statusCode": 200, "body": json.dumps({"processed": results})}


def handle_direct(event: dict) -> dict:
    """Direct Lambda invocation (testing or internal service call)."""
    missing = REQUIRED_FIELDS - set(event.keys())
    if missing:
        return error_response(400, f"Missing fields: {sorted(missing)}")
    result = run_pipeline(event)
    return {"statusCode": 200, "body": json.dumps(result, default=str)}

def run_pipeline(lead_input: dict) -> dict:
    """Calls CrewAI pipeline, persists result, returns structured output."""

    started_at = datetime.now(timezone.utc)
    logger.info("Starting pipeline for: %s / %s / %s",
                lead_input.get("company"), lead_input.get("role"), lead_input.get("segment"))

    result = run_crew(lead_input)

    finished_at = datetime.now(timezone.utc)
    duration_s  = (finished_at - started_at).total_seconds()

    lead_id = save_lead_result(
        lead_input=lead_input,
        analysis=result.get("analysis", {}),
        strategy=result.get("strategy", {}),
        email=result.get("email", {}),
        followups=result.get("followups", {}),
        duration_s=duration_s,
    )

    logger.info("Pipeline done. lead_id=%s duration=%.1fs", lead_id, duration_s)

    return {
        "lead_id"     : str(lead_id),
        "duration_s"  : round(duration_s, 2),
        "finished_at" : finished_at.isoformat(),
        **result,
    }

def detect_source(event: dict) -> str:
    if "httpMethod" in event or "requestContext" in event:
        return "api_gateway"
    if event.get("source") == "aws.events" or "detail-type" in event:
        return "eventbridge"
    return "direct"


def success_response(data: dict, cached: bool = False) -> dict:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({**data, "cached": cached}, default=str),
    }


def error_response(status: int, message: str) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }