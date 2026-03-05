import os
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from openai import OpenAI

logger = logging.getLogger(__name__)
openai_client = OpenAI()

@contextmanager
def get_conn():
    """Context manager — always commits or rolls back cleanly."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

SCHEMA_SQL = """
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Main leads table ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id                UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Input fields
    email             TEXT        UNIQUE,
    name              TEXT,
    company           TEXT        NOT NULL,
    contact_role      TEXT        NOT NULL,
    segment           TEXT        NOT NULL,
    extra_notes       TEXT,

    -- Pipeline outputs (stored as JSONB for flexibility)
    analysis          JSONB,
    strategy          JSONB,
    email_draft       JSONB,
    followup_sequence JSONB,

    -- Derived / indexed fields (extracted from analysis for fast querying)
    lead_score        SMALLINT    CHECK (lead_score BETWEEN 0 AND 100),
    intent            TEXT        CHECK (intent IN ('Low', 'Medium', 'High')),
    approach          TEXT,
    primary_channel   TEXT,

    -- Outcome (updated later by sales team or CRM webhook)
    outcome           TEXT        CHECK (outcome IN ('won', 'lost', 'nurturing', 'disqualified')),
    deal_value_usd    INTEGER,
    days_to_close     INTEGER,

    -- RAG embedding (text-embedding-3-small = 1536 dims)
    embedding         vector(1536),

    -- Processing state
    status            TEXT        NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending', 'processed', 'error')),
    error_message     TEXT,
    crm_contact_id    TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_email     ON leads (email);
CREATE INDEX IF NOT EXISTS idx_leads_segment   ON leads (segment);
CREATE INDEX IF NOT EXISTS idx_leads_status    ON leads (status);
CREATE INDEX IF NOT EXISTS idx_leads_outcome   ON leads (outcome);
CREATE INDEX IF NOT EXISTS idx_leads_embedding ON leads USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ── Pipeline run audit log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id     UUID        REFERENCES leads(id) ON DELETE CASCADE,
    ran_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    duration_s  FLOAT,
    model_used  TEXT        DEFAULT 'gpt-4o',
    triggered_by TEXT,      -- 'webhook' | 'eventbridge' | 'direct'
    success     BOOLEAN     NOT NULL
);

-- ── Follow-up tasks (denormalized for quick CRM queries) ──────────────────────
CREATE TABLE IF NOT EXISTS followup_tasks (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id       UUID        REFERENCES leads(id) ON DELETE CASCADE,
    step          SMALLINT    NOT NULL,
    channel       TEXT        NOT NULL,
    due_date      DATE        NOT NULL,
    action        TEXT        NOT NULL,
    message_hint  TEXT,
    priority      TEXT        DEFAULT 'medium',
    crm_task_id   TEXT,
    completed_at  TIMESTAMPTZ
);
"""

def create_schema():
    """Run once to initialize the database. Safe to re-run (IF NOT EXISTS)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
    logger.info("Schema created/verified.")

def build_embedding_text(lead_input: dict, analysis: dict) -> str:
    """Builds the text blob that gets embedded for RAG search."""
    pain_points = analysis.get("pain_points", [])
    return (
        f"Role: {lead_input.get('contact_role', lead_input.get('role', ''))} "
        f"Segment: {lead_input.get('segment', '')} "
        f"Company type: {lead_input.get('company', '')} "
        f"Pain points: {', '.join(pain_points)} "
        f"Intent: {analysis.get('intent', '')} "
        f"Tech stack: {', '.join(analysis.get('tech_stack_guess', []))}"
    )

def get_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding

def save_lead_result(
    lead_input: dict,
    analysis: dict,
    strategy: dict,
    email: dict,
    followups: dict,
    duration_s: float = 0.0,
    triggered_by: str = "webhook",
) -> uuid.UUID:
    emb_text  = build_embedding_text(lead_input, analysis)
    embedding = get_embedding(emb_text)

    lead_id   = uuid.uuid4()
    email_val = lead_input.get("email")

    lead_score = analysis.get("lead_score") if isinstance(analysis, dict) else None
    intent     = analysis.get("intent")     if isinstance(analysis, dict) else None
    approach   = strategy.get("approach")   if isinstance(strategy, dict) else None
    channel    = strategy.get("primary_channel") if isinstance(strategy, dict) else None

    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO leads (
                    id, email, name, company, contact_role, segment, extra_notes,
                    analysis, strategy, email_draft, followup_sequence,
                    lead_score, intent, approach, primary_channel,
                    embedding, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, 'processed'
                )
                ON CONFLICT (email) DO UPDATE SET
                    analysis          = EXCLUDED.analysis,
                    strategy          = EXCLUDED.strategy,
                    email_draft       = EXCLUDED.email_draft,
                    followup_sequence = EXCLUDED.followup_sequence,
                    lead_score        = EXCLUDED.lead_score,
                    intent            = EXCLUDED.intent,
                    approach          = EXCLUDED.approach,
                    primary_channel   = EXCLUDED.primary_channel,
                    embedding         = EXCLUDED.embedding,
                    status            = 'processed',
                    updated_at        = now()
                RETURNING id
            """, (
                lead_id,
                email_val,
                lead_input.get("name"),
                lead_input.get("company"),
                lead_input.get("role"),
                lead_input.get("segment"),
                lead_input.get("notes"),
                json.dumps(analysis),
                json.dumps(strategy),
                json.dumps(email),
                json.dumps(followups),
                lead_score,
                intent,
                approach,
                channel,
                embedding,
            ))
            returned = cur.fetchone()
            actual_id = returned[0] if returned else lead_id

            cur.execute("""
                INSERT INTO pipeline_runs (lead_id, duration_s, triggered_by, success)
                VALUES (%s, %s, %s, true)
            """, (actual_id, duration_s, triggered_by))

            sequence = followups.get("sequence", []) if isinstance(followups, dict) else []
            if sequence:
                rows = []
                for step in sequence:
                    due_date = (
                        datetime.now(timezone.utc) + timedelta(days=int(step.get("day", 1)))
                    ).date()
                    rows.append((
                        actual_id,
                        step.get("step", 1),
                        step.get("channel", "email"),
                        due_date,
                        step.get("action", ""),
                        step.get("message_hint", ""),
                        step.get("priority", "medium"),
                        step.get("crm_task_id"),
                    ))
                execute_values(cur, """
                    INSERT INTO followup_tasks
                        (lead_id, step, channel, due_date, action, message_hint, priority, crm_task_id)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                """, rows)

    return actual_id

def get_lead_by_email(email: str, max_age_hours: int = 24) -> dict | None:
    """Returns the latest processed result for an email, if recent enough."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, company, contact_role, segment,
                       analysis, strategy, email_draft, followup_sequence,
                       lead_score, intent, status, updated_at
                FROM leads
                WHERE email = %s AND status = 'processed' AND updated_at > %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (email, cutoff))
            row = cur.fetchone()
    return dict(row) if row else None


def get_pending_leads(older_than_hours: int = 2, limit: int = 10) -> list[dict]:
    """Returns leads stuck in 'pending' state — used by EventBridge retry."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, email, name, company, contact_role AS role,
                       segment, extra_notes AS notes
                FROM leads
                WHERE status = 'pending' AND created_at < %s
                ORDER BY created_at ASC
                LIMIT %s
            """, (cutoff, limit))
            return [dict(r) for r in cur.fetchall()]


def mark_lead_processed(lead_id: uuid.UUID):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leads SET status = 'processed', updated_at = now() WHERE id = %s",
                (str(lead_id),),
            )


def update_outcome(email: str, outcome: str, deal_value_usd: int = None, days_to_close: int = None):
    """
    Called by CRM webhook when a deal is marked won/lost.
    Updates the lead record — feeds future RAG quality.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE leads
                SET outcome = %s, deal_value_usd = %s, days_to_close = %s, updated_at = now()
                WHERE email = %s
            """, (outcome, deal_value_usd, days_to_close, email))

def search_similar_leads(embedding: list[float], top_k: int = 5) -> list[dict]:
    """Semantic search — called internally by RAGLeadTool."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    company, contact_role, segment,
                    analysis->'pain_points'  AS pain_points,
                    strategy->'approach'     AS strategy_used,
                    approach, primary_channel AS channel,
                    outcome, deal_value_usd, days_to_close,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM leads
                WHERE embedding IS NOT NULL AND status = 'processed'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (embedding, embedding, top_k))
            return [dict(r) for r in cur.fetchall()]

if __name__ == "__main__":
    create_schema()
    print("✅ Schema initialized successfully.")