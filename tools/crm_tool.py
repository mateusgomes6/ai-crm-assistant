import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import requests

class CRMTaskInput(BaseModel):
    lead_email: str = Field(description="Lead's email address")
    lead_name: str = Field(description="Lead's full name")
    company: str = Field(description="Lead's company name")
    tasks: list[dict] = Field(
        description="List of tasks. Each: {title, due_in_days, channel, priority, notes}"
    )

class HubSpotClient:
    BASE = "https://api.hubapi.com"

    def __init__(self):
        self.token = os.environ["HUBSPOT_TOKEN"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_or_create_contact(self, email: str, name: str, company: str) -> str:
        """Returns HubSpot contact ID."""
        r = requests.get(
            f"{self.BASE}/crm/v3/objects/contacts/search",
            headers=self.headers,
            json={"filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}]},
        )
        data = r.json()
        if data.get("total", 0) > 0:
            return data["results"][0]["id"]

        first, *last = name.split()
        r = requests.post(
            f"{self.BASE}/crm/v3/objects/contacts",
            headers=self.headers,
            json={"properties": {
                "email": email,
                "firstname": first,
                "lastname": " ".join(last),
                "company": company,
            }},
        )
        return r.json()["id"]

    def create_task(self, contact_id: str, title: str, due_in_days: int,
                    notes: str, priority: str = "HIGH") -> str:
        """Creates a task in HubSpot and returns task ID."""
        due_ts = int((datetime.utcnow() + timedelta(days=due_in_days)).timestamp() * 1000)

        r = requests.post(
            f"{self.BASE}/crm/v3/objects/tasks",
            headers=self.headers,
            json={
                "properties": {
                    "hs_task_subject": title,
                    "hs_task_body": notes,
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": priority.upper(),
                    "hs_timestamp": due_ts,
                },
                "associations": [{
                    "to": {"id": contact_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}],
                }],
            },
        )
        return r.json().get("id", str(uuid.uuid4()))


class PipedriveClient:
    def __init__(self):
        self.token = os.environ["PIPEDRIVE_TOKEN"]
        self.base = f"https://api.pipedrive.com/v1"

    def get_or_create_person(self, email: str, name: str, company: str) -> str:
        r = requests.get(f"{self.base}/persons/search",
                         params={"term": email, "api_token": self.token})
        items = r.json().get("data", {}).get("items", [])
        if items:
            return str(items[0]["item"]["id"])

        r = requests.post(f"{self.base}/persons",
                          params={"api_token": self.token},
                          json={"name": name, "email": email})
        return str(r.json()["data"]["id"])

    def create_task(self, person_id: str, title: str, due_in_days: int,
                    notes: str, priority: str = "high") -> str:
        due_date = (datetime.utcnow() + timedelta(days=due_in_days)).strftime("%Y-%m-%d")
        r = requests.post(f"{self.base}/activities",
                          params={"api_token": self.token},
                          json={
                              "subject": title,
                              "type": "task",
                              "due_date": due_date,
                              "note": notes,
                              "person_id": person_id,
                          })
        return str(r.json()["data"]["id"])

class CRMTool(BaseTool):
    name: str = "crm_task_creator"
    description: str = (
        "Creates a contact and schedules follow-up tasks in the CRM (HubSpot or Pipedrive). "
        "Input: lead info + list of tasks with due dates and channels. "
        "Returns task IDs for each created task."
    )
    args_schema: Type[BaseModel] = CRMTaskInput

    def _run(self, lead_email: str, lead_name: str, company: str, tasks: list[dict]) -> str:
        backend = os.environ.get("CRM_BACKEND", "hubspot").lower()

        if backend == "pipedrive":
            client = PipedriveClient()
            contact_id = client.get_or_create_person(lead_email, lead_name, company)
        else:
            client = HubSpotClient()
            contact_id = client.get_or_create_contact(lead_email, lead_name, company)

        results = []
        for task in tasks:
            task_id = client.create_task(
                contact_id=contact_id,
                title=f"[{task['channel'].upper()}] {task['title']}",
                due_in_days=task["due_in_days"],
                notes=task.get("notes", ""),
                priority=task.get("priority", "high"),
            )
            results.append({
                "step": task.get("step"),
                "channel": task["channel"],
                "crm_task_id": task_id,
                "due_in_days": task["due_in_days"],
            })

        return json.dumps({
            "contact_id": contact_id,
            "crm_backend": backend,
            "tasks_created": results,
        })