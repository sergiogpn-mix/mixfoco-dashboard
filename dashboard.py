"""
Mixfoco Dashboard — Streamlit
Candidatos · Ativos · Impacto · Regras

Local:  streamlit run dashboard.py
Deploy: mesmo serviço Railway (PORT automático)
"""
import os
import requests
import streamlit as st
from datetime import datetime

API_URL = os.getenv("MIXFOCO_API_URL", "https://railway-up-production-1df7.up.railway.app")

st.set_page_config(
    page_title="Mixfoco",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Helpers ─────────────────────────────────────────────────────────────────────

def api(method: str, path: str, **kwargs):
    try:
        r = requests.request(method, f"{API_URL}{path}", timeout=20, **kwargs)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)


def delta_badge(val):
    if val is None:
        return "—"
    color = "green" if val >= 0 else "red"
    arrow = "▲" if val >= 0 else "▼"
    return f":{color}[{arrow} {abs(val):.1f}%]"


def fmt_brl(v):
    return f"R$ {v:,.2f}" if v else "—"


def fmt_dt(iso):
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m %H:%M")
    except Exception:
        return iso[:16]


# ── Header ───────────────────────────────────────────────────────────────────────

st.markdown("## 🎯 Mixfoco")
st.caption(f"API: `{API_URL}`")

aba_candidatos, aba_ativos, aba_impacto, aba_regras = st.tabs([
    "📋 Candidatos", "⚡ Ativos", "📊 Impacto", "⚙️ Regras"
])


# ══════════════════════════════════════════════════════════════════════
# ABA 1 — CANDIDATOS
# ══════════════════════════════════════════════════════════════════════

with aba_candidatos:
    st.subheader("Candidatos ao Mixfoco")

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        period = st.selectbox("Período", ["week", "today", "month"],
                              format_func=lambda x: {"week": "Semana", "today": "Hoje", "month": "Mês"}[x])
    with col2:
        store_filter = st.text_input("Loja (vazio = todas)", placeholder="ex: DGX")
    with col3:
        roas_min = st.number_input("ROAS mín", value=5.0, step=0.5, min_value=0.0)
    with col4:
        spend_min = st.number_input("Spend mín R$", value=20.0, step=5.0, min_value=0.0)

    if st.button("🔍 Buscar candidatos", type="primary"):
        params = f"?period={period}&roas_min={roas_min}&spend_min={spend_min}&limit=50"
        if store_filter.strip():
            params += f"&store={store_filter.strip().upper()}"
        with st.spinner("Buscando na API ML..."):
            data, err = api("GET", f"/mixfoco/candidates{params}")

        if err:
            st.error(f"Erro: {err}")
        elif not data or data["total"] == 0:
            st.info("Nenhum candidato encontrado com esses critérios.")
        else:
            st.success(f"{data['total']} candidatos — {data['date_range']['from']} a {data['date_range']['to']}")
            st.session_state["candidatos"] = data["candidates"]

    candidates = st.session_state.get("candidatos", [])
    if candidates:
        for i, c in enumerate(candidates):
            with st.container(border=True):
                col_info, col_metrics, col_btn = st.columns([4, 4, 2])

                with col_info:
                    st.markdown(f"**{c['title'][:70]}{'…' if len(c['title']) > 70 else ''}**")
                    st.caption(f"🏪 {c['store_key']} · MLB: `{c['item_id']}`")
                    st.caption(f"_{c['reason']}_")

                with col_metrics:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("ROAS", f"{c['roas']}x")
                    m2.metric("CVR", f"{c['cvr']}%")
                    m3.metric("Spend", fmt_brl(c['spend']))
                    m4.metric("Score", f"{c['turbo_score']}")

                with col_btn:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("⚡ Ativar", key=f"activate_{i}_{c['item_id']}"):
                        with st.spinner("Ativando..."):
                            result, err = api("POST", "/mixfoco/activate", json={
                                "item_id":   c["item_id"],
                                "ad_id":     c.get("ad_id") or None,
                                "store_key": c["store_key"],
                                "capture_snapshot": True,
                            })
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success(f"✅ Ativado às {fmt_dt(result.get('activated_at'))}")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# ABA 2 — ATIVOS
# ══════════════════════════════════════════════════════════════════════

with aba_ativos:
    st.subheader("Itens com Mixfoco ativo")

    col_r, col_s = st.columns([6, 2])
    with col_r:
        store_ativos = st.text_input("Filtrar por loja", placeholder="ex: MIXCONECTA", key="store_ativos")
    with col_s:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        refresh_ativos = st.button("🔄 Atualizar", key="refresh_ativos")

    if refresh_ativos or "historico" not in st.session_state:
        params = "?active_only=true&limit=100"
        if store_ativos.strip():
            params += f"&store={store_ativos.strip().upper()}"
        data, err = api("GET", f"/mixfoco/history{params}")
        if not err:
            st.session_state["historico"] = data.get("records", [])

    records = st.session_state.get("historico", [])
    ativos  = [r for r in records if not r.get("deactivated_at")]

    if not ativos:
        st.info("Nenhum item ativo no momento.")
    else:
        st.markdown(f"**{len(ativos)} item(s) ativo(s)**")
        for r in ativos:
            with st.container(border=True):
                col_i, col_t, col_btn = st.columns([5, 3, 2])
                with col_i:
                    st.markdown(f"`{r['item_id']}` · 🏪 {r['store_key']}")
                    st.caption(f"Ativado em {fmt_dt(r.get('activated_at'))}")
                with col_t:
                    snap = r.get("snapshot_before") or {}
                    if snap:
                        s1, s2, s3 = st.columns(3)
                        s1.metric("ROAS before", f"{snap.get('roas', 0)}x")
                        s2.metric("CVR before",  f"{snap.get('cvr', 0)}%")
                        s3.metric("Conv. before", snap.get("conversions", 0))
                with col_btn:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("🛑 Desativar", key=f"deact_{r['item_id']}"):
                        with st.spinner("Desativando..."):
                            result, err = api("POST", "/mixfoco/deactivate", json={
                                "item_id":   r["item_id"],
                                "ad_id":     r.get("ad_id") or None,
                                "store_key": r["store_key"],
                                "capture_snapshot": True,
                            })
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success("✅ Desativado — veja o impacto na aba Impacto")
                            st.session_state.pop("historico", None)
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════
# ABA 3 — IMPACTO
# ══════════════════════════════════════════════════════════════════════

with aba_impacto:
    st.subheader("Impacto do Mixfoco")

    col_id, col_btn_imp = st.columns([4, 2])
    with col_id:
        item_id_imp = st.text_input("Item ID", placeholder="ex: MLB1234567890")
    with col_btn_imp:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        refresh_after = st.checkbox("Capturar snapshot now (after)", value=False)
        buscar_imp    = st.button("📊 Ver impacto", type="primary")

    if buscar_imp and item_id_imp.strip():
        suffix = "?refresh_after=true" if refresh_after else ""
        with st.spinner("Buscando métricas..."):
            data, err = api("GET", f"/mixfoco/impact/{item_id_imp.strip()}{suffix}")
        if err:
            st.error(f"Erro: {err}")
        elif data:
            st.session_state["impact_data"] = data

    imp = st.session_state.get("impact_data")
    if imp:
        status_color = "🟢" if imp.get("status") == "ativo" else "🔴"
        st.markdown(f"**{status_color} {imp['item_id']}** · {imp.get('store_key')} · "
                    f"Ativado: {fmt_dt(imp.get('activated_at'))} · "
                    f"Desativado: {fmt_dt(imp.get('deactivated_at'))}")

        delta = imp.get("impact_delta")
        if not delta:
            st.info(imp.get("note", "Snapshot after ainda não disponível."))
        else:
            st.markdown("### Variação de métricas")
            cols = st.columns(4)
            metrics = [
                ("Impressões",  "impressions"),
                ("Cliques",     "clicks"),
                ("Conversões",  "conversions"),
                ("ROAS",        "roas"),
                ("CVR",         "cvr"),
                ("CTR",         "ctr"),
                ("Receita",     "revenue"),
                ("Spend",       "spend"),
            ]
            for idx, (label, key) in enumerate(metrics):
                with cols[idx % 4]:
                    before = delta.get(f"{key}_before", 0)
                    after  = delta.get(f"{key}_after", 0)
                    pct    = delta.get(f"{key}_delta_pct")
                    st.metric(
                        label=label,
                        value=f"{after:,.2f}" if isinstance(after, float) else str(after),
                        delta=f"{pct:+.1f}%" if pct is not None else None,
                        help=f"Antes: {before}",
                    )

        with st.expander("Ver snapshots completos"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Before**")
                st.json(imp.get("snapshot_before") or {})
            with c2:
                st.markdown("**After**")
                st.json(imp.get("snapshot_after") or {})


# ══════════════════════════════════════════════════════════════════════
# ABA 4 — REGRAS
# ══════════════════════════════════════════════════════════════════════

with aba_regras:
    st.subheader("Regras de automação")

    # Listar regras existentes
    rules_data, err = api("GET", "/mixfoco/rules")
    rules = rules_data.get("rules", []) if rules_data else []

    if not rules:
        st.info("Nenhuma regra criada ainda.")
    else:
        for rule in rules:
            status_icon = "🟢" if rule.get("enabled") else "⚫"
            auto_icon   = "🤖" if rule.get("auto") else "👁️"
            with st.container(border=True):
                col_r, col_act = st.columns([6, 2])
                with col_r:
                    st.markdown(f"{status_icon} **{rule['name']}** {auto_icon}")
                    c = rule.get("criteria", {})
                    st.caption(
                        f"ROAS {c.get('roas_min')}–{c.get('roas_max')}x · "
                        f"Conv ≥{c.get('conversions_min')} · "
                        f"Spend ≥R${c.get('spend_min')} · "
                        f"Período: {rule.get('period')} · "
                        f"Cooldown: {rule.get('cooldown_hours')}h"
                    )
                    if rule.get("last_run"):
                        st.caption(f"Último run: {fmt_dt(rule['last_run'])} · Aplicados: {rule.get('last_applied', 0)}")
                    lojas = rule.get("stores") or ["todas"]
                    st.caption(f"Lojas: {', '.join(lojas)}")
                with col_act:
                    dry = st.checkbox("Dry run", value=True, key=f"dry_{rule['id']}")
                    if st.button("▶ Rodar", key=f"run_{rule['id']}"):
                        with st.spinner("Avaliando..."):
                            result, err = api("POST", f"/mixfoco/rules/{rule['id']}/run",
                                              params={"dry_run": str(dry).lower()})
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success(
                                f"✅ {result['total_matches']} matches · "
                                f"{len(result.get('applied', []))} ativados · "
                                f"{result['total_cooldown']} em cooldown"
                            )
                    if st.button("🗑️ Remover", key=f"del_{rule['id']}"):
                        _, err = api("DELETE", f"/mixfoco/rules/{rule['id']}")
                        if not err:
                            st.rerun()

    st.divider()
    st.markdown("### Nova regra")
    with st.form("nova_regra"):
        col_n, col_p, col_s = st.columns([3, 2, 2])
        with col_n:
            nome = st.text_input("Nome", value="Regra Mixfoco")
        with col_p:
            periodo = st.selectbox("Período", ["week", "today", "month"],
                                   format_func=lambda x: {"week": "Semana", "today": "Hoje", "month": "Mês"}[x])
        with col_s:
            lojas_input = st.text_input("Lojas (vazio = todas)", placeholder="DGX,MIXCONECTA")

        col1, col2, col3, col4 = st.columns(4)
        with col1: r_min = st.number_input("ROAS mín", value=5.0, step=0.5)
        with col2: r_max = st.number_input("ROAS máx", value=12.0, step=0.5)
        with col3: conv  = st.number_input("Conversões mín", value=1, step=1, min_value=0)
        with col4: spend = st.number_input("Spend mín R$", value=20.0, step=5.0)

        col_auto, col_cool = st.columns(2)
        with col_auto:
            auto     = st.toggle("Ativar automaticamente (auto=true)", value=False)
        with col_cool:
            cooldown = st.number_input("Cooldown (horas)", value=168, step=24, min_value=0)

        submitted = st.form_submit_button("✅ Criar regra", type="primary")
        if submitted:
            lojas_list = [l.strip().upper() for l in lojas_input.split(",") if l.strip()]
            payload = {
                "name":            nome,
                "enabled":         True,
                "auto":            auto,
                "stores":          lojas_list,
                "period":          periodo,
                "roas_min":        r_min,
                "roas_max":        r_max,
                "conversions_min": int(conv),
                "spend_min":       spend,
                "cooldown_hours":  int(cooldown),
            }
            result, err = api("POST", "/mixfoco/rules", json=payload)
            if err:
                st.error(f"Erro: {err}")
            else:
                st.success(f"✅ Regra `{result['rule']['id']}` criada!")
                st.rerun()

    st.divider()
    if st.button("🤖 Rodar TODAS as regras habilitadas"):
        dry_all = st.checkbox("Dry run global", value=True, key="dry_all")
        with st.spinner("Executando regras..."):
            result, err = api("POST", "/mixfoco/rules/run",
                              params={"dry_run": str(dry_all).lower()})
        if err:
            st.error(f"Erro: {err}")
        else:
            st.success(
                f"✅ {result['rules_run']} regras · {result['total_applied']} ativações"
            )
            for r in result.get("results", []):
                st.caption(
                    f"• **{r['rule_name']}**: {r['total_matches']} matches · "
                    f"{len(r.get('applied', []))} ativados · "
                    f"{r['total_cooldown']} cooldown"
                )
