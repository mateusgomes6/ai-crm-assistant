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
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { max-width: 800px; padding-top: 2rem; }
    .report-card {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #e94560;
    }
    .report-card h3 { margin-top: 0; color: #e94560; }
    .metric-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .metric-box {
        background: #16213e;
        border-radius: 8px;
        padding: 1rem;
        flex: 1;
        text-align: center;
    }
    .metric-box .label { font-size: 0.8rem; color: #aaa; }
    .metric-box .value { font-size: 1.5rem; font-weight: bold; color: #fff; }
    .email-preview {
        background: #0f3460;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        font-family: Georgia, serif;
        line-height: 1.6;
    }
    .step-card {
        background: #16213e;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        border-left: 3px solid #0f3460;
    }
    .step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-alta { background: #e94560; color: white; }
    .badge-media { background: #f5a623; color: black; }
    .badge-baixa { background: #2ecc71; color: white; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🎯 AI CRM Assistant")
st.caption("Pipeline inteligente de vendas B2B com agentes de IA")

# ── State management ─────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "form"

def safe_get(data, key, default="N/A"):
    if isinstance(data, dict):
        return data.get(key, default)
    return default

# ── PAGE: Input Form ─────────────────────────────────────────────────────────
if st.session_state["page"] == "form":
    st.markdown("---")
    st.markdown("### Preencha os dados do lead")

    with st.form("lead_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome do contato", placeholder="João Silva")
            company = st.text_input("Empresa *", placeholder="TechCorp")
            segment = st.selectbox(
                "Segmento *",
                ["SaaS B2B", "Fintech", "E-commerce", "HealthTech", "EdTech", "MarTech", "Outro"],
            )
        with col2:
            email = st.text_input("E-mail", placeholder="joao@empresa.com")
            role = st.text_input("Cargo *", placeholder="CTO")
            notes = st.text_area("Notas extras", placeholder="Interessado em automacao de vendas...", height=80)

        submitted = st.form_submit_button("🚀 Analisar Lead", type="primary", use_container_width=True)

    if submitted:
        if not company or not role:
            st.error("Preencha os campos obrigatorios: **Empresa** e **Cargo**.")
        else:
            lead_input = {
                "email": email or None,
                "name": name or None,
                "company": company,
                "role": role,
                "segment": segment,
                "notes": notes or None,
            }

            with st.status("🤖 Agentes de IA trabalhando...", expanded=True) as status:
                st.write("🔍 Analisando perfil do lead...")
                start = time.time()

                try:
                    result = run_crew(lead_input)
                    duration = time.time() - start

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
                    except Exception:
                        pass

                    result["duration_s"] = round(duration, 2)
                    st.session_state["result"] = result
                    st.session_state["lead_input"] = lead_input
                    st.session_state["page"] = "report"
                    status.update(label=f"Concluido em {duration:.1f}s", state="complete")
                    st.rerun()

                except Exception as e:
                    status.update(label="Erro no pipeline", state="error")
                    st.error(f"Erro: {e}")

    if st.session_state["page"] == "form":
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🔍 Analise**")
            st.caption("Score, intencao de compra e pontos de dor")
        with col2:
            st.markdown("**📊 Estrategia**")
            st.caption("Canal, abordagem e ganchos de valor")
        with col3:
            st.markdown("**✉️ E-mail + Follow-up**")
            st.caption("Cold email e sequencia de touchpoints")

# ── PAGE: Report ─────────────────────────────────────────────────────────────
elif st.session_state["page"] == "report":
    result = st.session_state.get("result", {})
    lead = st.session_state.get("lead_input", {})
    analysis = result.get("analysis", {})
    strategy = result.get("strategy", {})
    email_data = result.get("email", {})
    followups = result.get("followups", {})

    # Back button
    if st.button("← Novo Lead"):
        st.session_state["page"] = "form"
        if "result" in st.session_state:
            del st.session_state["result"]
        st.rerun()

    # ── Report Header ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### Relatorio: {safe_get(lead, 'name', safe_get(lead, 'role'))} — {safe_get(lead, 'company')}")
    st.caption(f"{safe_get(lead, 'role')} | {safe_get(lead, 'segment')} | Processado em {result.get('duration_s', '?')}s")

    # ── Section 1: Analysis ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🔍 Analise do Lead")

    if isinstance(analysis, str):
        st.write(analysis)
    elif isinstance(analysis, dict):
        col1, col2, col3 = st.columns(3)
        with col1:
            score = safe_get(analysis, "lead_score", 0)
            st.metric("Lead Score", f"{score}/100")
        with col2:
            st.metric("Intencao de Compra", safe_get(analysis, "intent", "?"))
        with col3:
            st.metric("Leads Similares", safe_get(analysis, "similar_leads_found", 0))

        reason = safe_get(analysis, "intent_reason")
        if reason and reason != "N/A":
            st.info(f"**Justificativa:** {reason}")

        pain_points = analysis.get("pain_points", []) if isinstance(analysis, dict) else []
        if pain_points:
            st.markdown("#### Principais Pontos de Dor")
            for i, pain in enumerate(pain_points, 1):
                st.markdown(f"{i}. {pain}")

        col1, col2 = st.columns(2)
        tech = analysis.get("tech_stack_guess", []) if isinstance(analysis, dict) else []
        committee = analysis.get("buying_committee", []) if isinstance(analysis, dict) else []
        with col1:
            if tech:
                st.markdown("#### Stack Tecnologico Provavel")
                for t in tech:
                    st.markdown(f"- {t}")
        with col2:
            if committee:
                st.markdown("#### Comite de Compras")
                for m in committee:
                    st.markdown(f"- {m}")

        notes = safe_get(analysis, "analyst_notes")
        if notes and notes != "N/A":
            st.markdown("#### Notas do Analista")
            st.write(notes)

    # ── Section 2: Strategy ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Estrategia de Vendas")

    if isinstance(strategy, str):
        st.write(strategy)
    elif isinstance(strategy, dict):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Abordagem", safe_get(strategy, "approach", "?"))
        with col2:
            st.metric("Canal", safe_get(strategy, "primary_channel", "?"))
        with col3:
            st.metric("Tom", safe_get(strategy, "tone", "?"))
        with col4:
            st.metric("Confianca", f"{safe_get(strategy, 'strategy_confidence', '?')}%")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Melhor dia:** {safe_get(strategy, 'best_day')}")
            st.markdown(f"**Melhor horario:** {safe_get(strategy, 'best_time')}")
        with col2:
            cta = safe_get(strategy, "cta")
            if cta and cta != "N/A":
                st.success(f"**CTA recomendado:** {cta}")

        hooks = strategy.get("value_hooks", []) if isinstance(strategy, dict) else []
        if hooks:
            st.markdown("#### Ganchos de Valor")
            for i, hook in enumerate(hooks, 1):
                if isinstance(hook, dict):
                    st.markdown(
                        f"**{i}.** 🎯 *{hook.get('pain', '')}*\n\n"
                        f"   → **Ganho:** {hook.get('gain', '')}  \n"
                        f"   → **Metrica:** {hook.get('metric', '')}"
                    )
                    st.markdown("")

        objections = strategy.get("objections", []) if isinstance(strategy, dict) else []
        if objections:
            st.markdown("#### Objecoes e Respostas")
            for obj in objections:
                if isinstance(obj, dict):
                    with st.expander(f"❓ {obj.get('objection', '')}"):
                        st.write(f"**Resposta:** {obj.get('handler', '')}")

    # ── Section 3: Email ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## ✉️ E-mail Outbound")

    if isinstance(email_data, str):
        st.write(email_data)
    elif isinstance(email_data, dict):
        subject = safe_get(email_data, "subject", "Sem assunto")
        body = safe_get(email_data, "body", "")
        var_a = safe_get(email_data, "subject_variant_a")
        var_b = safe_get(email_data, "subject_variant_b")

        st.markdown(f"**Assunto:** {subject}")
        if var_a and var_a != "N/A":
            st.caption(f"Variante A: {var_a}")
        if var_b and var_b != "N/A":
            st.caption(f"Variante B: {var_b}")

        st.markdown("#### Preview do E-mail")
        st.markdown(
            f'<div class="email-preview">{body}</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            wc = safe_get(email_data, "word_count", "?")
            st.caption(f"📝 {wc} palavras")
        with col2:
            cta = safe_get(email_data, "cta", "")
            if cta:
                st.caption(f"🎯 CTA: {cta}")

        hooks_used = email_data.get("personalization_hooks_used", []) if isinstance(email_data, dict) else []
        if hooks_used:
            st.caption(f"🔗 Hooks usados: {', '.join(hooks_used)}")

    # ── Section 4: Follow-ups ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📅 Sequencia de Follow-up")

    if isinstance(followups, str):
        st.write(followups)
    elif isinstance(followups, dict):
        sequence = followups.get("sequence", [])
        total = followups.get("total_touchpoints", len(sequence))
        prob = safe_get(followups, "estimated_reply_probability", "?")
        st.caption(f"{total} touchpoints | Probabilidade de resposta estimada: **{prob}**")

        for step in sequence:
            if not isinstance(step, dict):
                continue
            day = step.get("day", "?")
            channel = step.get("channel", "?")
            priority = step.get("priority", "media")
            action = step.get("action", "")
            hint = step.get("message_hint", "")
            step_num = step.get("step", "?")

            priority_badge = {
                "alta": "badge-alta",
                "media": "badge-media",
                "média": "badge-media",
                "baixa": "badge-baixa",
            }.get(priority, "badge-media")

            st.markdown(f"""
<div class="step-card">
    <div class="step-header">
        <strong>Etapa {step_num} — Dia {day}</strong>
        <span>
            <span class="badge {priority_badge}">{priority}</span>
            &nbsp; 📡 {channel}
        </span>
    </div>
    <div><strong>Acao:</strong> {action}</div>
    <div style="color: #aaa; margin-top: 4px;"><strong>Dica SDR:</strong> {hint}</div>
</div>
""", unsafe_allow_html=True)

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption("Powered by Groq (Llama 3.3 70B) + CrewAI + Streamlit")
