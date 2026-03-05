def handler(event, context):
    lead_data = json.loads(event["body"])

    result = run_crew(
        company=lead_data["company"],
        role=lead_data["role"],
        segment=lead_data["segment"],
    )

    save_lead(lead_data, result)
    sync_to_crm(result["followups"])

    return {"statusCode": 200, "body": json.dumps(result)}