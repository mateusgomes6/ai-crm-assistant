import streamlit as st
import json
import time
from dotenv import load_dotenv

load_dotenv()

from crew import run_crew
from database import save_lead_result, get_lead_by_email

st.set_page_config(
    page_title="AI CRM Assistant",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI CRM Assistant")
st.markdown("Pipeline inteligente de vendas B2B com agentes de IA")

# ── Sidebar: Lead Input ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Dados do Lead")

    name = st.text_input("Nome", placeholder="João Silva")
    email = st.text_input("E-mail", placeholder="joao@empresa.com")
    company = st.text_input("Empresa *", placeholder="TechCorp")
    role = st.text_input("Cargo *", placeholder="CTO")
    segment = st.selectbox(
        "Segmento *",
        ["SaaS B2B", "Fintech", "E-commerce", "HealthTech", "EdTech", "MarTech", "Outro"],
    )
    notes = st.text_area("Notas extras", placeholder="Interessado em automação de vendas...")

    run_button = st.button("🚀 Analisar Lead", type="primary", use_container_width=True)

    st.divider()
    st.caption("Powered by Groq (Llama 3.3 70B) + CrewAI")

# ── Main Area ────────────────────────────────────────────────────────────────
if run_button:
    if not company or not role:
        st.error("Preencha os campos obrigatórios: Empresa e Cargo.")
    else:
        lead_input = {
            "email": email or None,
            "name": name or None,
            "company": company,
            "role": role,
            "segment": segment,
            "notes": notes or None,
        }

        # Check cache
        if email:
            cached = get_lead_by_email(email, max_age_hours=24)
            if cached:
                st.info("Lead encontrado no cache (processado nas últimas 24h). Mostrando resultado salvo.")
                st.session_state["result"] = {
                    "lead_input": lead_input,
                    "analysis": cached.get("analysis", {}),
                    "strategy": cached.get("strategy", {}),
                    "email": cached.get("email_draft", {}),
                    "followups": cached.get("followup_sequence", {}),
                    "cached": True,
                }

        if "result" not in st.session_state or not st.session_state.get("result", {}).get("cached"):
            with st.status("🤖 Agentes trabalhando...", expanded=True) as status:
                st.write("🔍 **Agente 1** — Analista de Inteligência de Leads")
                st.write("📊 **Agente 2** — Estrategista de Vendas B2B")
                st.write("✉️ **Agente 3** — Copywriter de E-mails B2B")
                st.write("📅 **Agente 4** — Gerente de Follow-up")
                st.divider()
                st.write("Processando... isso leva ~30-60 segundos.")

                start = time.time()
                try:
                    result = run_crew(lead_input)
                    duration = time.time() - start

                    # Save to database
                    try:
                        lead_id = save_lead_result(
                            lead_input=lead_input,
                            analysis=result.get("analysis", {}),
                            strategy=result.get("strategy", {}),
                            email=result.get("email", {}),
                            followups=result.get("followups", {}),
                            duration_s=duration,
                        )
                        result["lead_id"] = str(lead_id)
                    except Exception as e:
                        st.warning(f"Resultado gerado, mas erro ao salvar no banco: {e}")

                    result["duration_s"] = round(duration, 2)
                    st.session_state["result"] = result
                    status.update(label=f"Concluído em {duration:.1f}s", state="complete")

                except Exception as e:
                    status.update(label="Erro no pipeline", state="error")
                    st.error(f"Erro: {e}")
                    st.stop()

# ── Display Results ──────────────────────────────────────────────────────────
if "result" in st.session_state:
    result = st.session_state["result"]

    if result.get("lead_id"):
        st.success(f"Lead ID: `{result['lead_id']}` | Tempo: {result.get('duration_s', '?')}s")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Análise", "📊 Estratégia", "✉️ E-mail", "📅 Follow-ups", "📄 JSON Completo"
    ])

    # ── Tab 1: Analysis ──────────────────────────────────────────────────────
    with tab1:
        analysis = result.get("analysis", {})
        if isinstance(analysis, str):
            st.markdown(analysis)
        elif isinstance(analysis, dict):
            col1, col2, col3 = st.columns(3)
            with col1:
                score = analysis.get("lead_score", "?")
                st.metric("Lead Score", f"{score}/100")
            with col2:
                intent = analysis.get("intent", "?")
                st.metric("Intenção", intent)
            with col3:
                similar = analysis.get("similar_leads_found", "?")
                st.metric("Leads Similares", similar)

            st.subheader("Razão da Intenção")
            st.write(analysis.get("intent_reason", "N/A"))

            st.subheader("Pontos de Dor")
            for i, pain in enumerate(analysis.get("pain_points", []), 1):
                st.markdown(f"**{i}.** {pain}")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Stack Tecnológico")
                for tech in analysis.get("tech_stack_guess", []):
                    st.markdown(f"- {tech}")
            with col2:
                st.subheader("Comitê de Compras")
                for member in analysis.get("buying_committee", []):
                    st.markdown(f"- {member}")

            if analysis.get("analyst_notes"):
                st.subheader("Notas do Analista")
                st.info(analysis["analyst_notes"])

    # ── Tab 2: Strategy ──────────────────────────────────────────────────────
    with tab2:
        strategy = result.get("strategy", {})
        if isinstance(strategy, str):
            st.markdown(strategy)
        elif isinstance(strategy, dict):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Abordagem", strategy.get("approach", "?"))
            with col2:
                st.metric("Canal Primário", strategy.get("primary_channel", "?"))
            with col3:
                st.metric("Tom", strategy.get("tone", "?"))
            with col4:
                conf = strategy.get("strategy_confidence", "?")
                st.metric("Confiança", f"{conf}%")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Melhor Timing")
                st.write(f"**Dia:** {strategy.get('best_day', '?')}")
                st.write(f"**Horário:** {strategy.get('best_time', '?')}")
            with col2:
                st.subheader("CTA Recomendado")
                st.info(strategy.get("cta", "N/A"))

            st.subheader("Ganchos de Valor")
            for hook in strategy.get("value_hooks", []):
                if isinstance(hook, dict):
                    st.markdown(
                        f"- **Dor:** {hook.get('pain', '')} → "
                        f"**Ganho:** {hook.get('gain', '')} | "
                        f"**Métrica:** {hook.get('metric', '')}"
                    )

            st.subheader("Tratamento de Objeções")
            for obj in strategy.get("objections", []):
                if isinstance(obj, dict):
                    with st.expander(f"❓ {obj.get('objection', '')}"):
                        st.write(obj.get("handler", ""))

    # ── Tab 3: Email ─────────────────────────────────────────────────────────
    with tab3:
        email_data = result.get("email", {})
        if isinstance(email_data, str):
            st.markdown(email_data)
        elif isinstance(email_data, dict):
            st.subheader("Assunto Principal")
            st.code(email_data.get("subject", "N/A"))

            col1, col2 = st.columns(2)
            with col1:
                st.caption("Variante A")
                st.code(email_data.get("subject_variant_a", "N/A"))
            with col2:
                st.caption("Variante B")
                st.code(email_data.get("subject_variant_b", "N/A"))

            st.subheader("Corpo do E-mail")
            st.markdown(email_data.get("body", "N/A"))

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Palavras", email_data.get("word_count", "?"))
            with col2:
                st.metric("CTA", email_data.get("cta", "?"))

            hooks = email_data.get("personalization_hooks_used", [])
            if hooks:
                st.subheader("Hooks de Personalização")
                st.write(", ".join(hooks))

    # ── Tab 4: Follow-ups ────────────────────────────────────────────────────
    with tab4:
        followups = result.get("followups", {})
        if isinstance(followups, str):
            st.markdown(followups)
        elif isinstance(followups, dict):
            sequence = followups.get("sequence", [])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Touchpoints", followups.get("total_touchpoints", len(sequence)))
            with col2:
                st.metric("Probabilidade de Resposta", followups.get("estimated_reply_probability", "?"))

            for step in sequence:
                if isinstance(step, dict):
                    day = step.get("day", "?")
                    channel = step.get("channel", "?")
                    priority = step.get("priority", "média")
                    priority_color = {"alta": "🔴", "média": "🟡", "baixa": "🟢"}.get(priority, "⚪")

                    with st.expander(
                        f"Etapa {step.get('step', '?')} — Dia {day} | {channel.upper()} {priority_color}"
                    ):
                        st.write(f"**Ação:** {step.get('action', 'N/A')}")
                        st.write(f"**Dica para o SDR:** {step.get('message_hint', 'N/A')}")
                        st.write(f"**Prioridade:** {priority}")
                        if step.get("crm_task_id"):
                            st.caption(f"CRM Task ID: {step['crm_task_id']}")

    # ── Tab 5: Raw JSON ──────────────────────────────────────────────────────
    with tab5:
        st.json(result)

# ── Empty State ──────────────────────────────────────────────────────────────
elif not run_button:
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🔍 Análise de Lead")
        st.markdown("Score, intenção de compra, pontos de dor e stack tecnológico")
    with col2:
        st.markdown("### 📊 Estratégia de Vendas")
        st.markdown("Canal, abordagem, timing, ganchos de valor e objeções")
    with col3:
        st.markdown("### ✉️ E-mail + Follow-up")
        st.markdown("Cold email personalizado e sequência de 4 touchpoints")
