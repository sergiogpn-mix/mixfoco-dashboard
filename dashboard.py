"""
Mixfoco Dashboard — Streamlit
Candidatos · Ativos · Impacto · Regras · Lojas
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

aba_candidatos, aba_ativos, aba_impacto, aba_regras, aba_lojas, aba_vendas, aba_sac = st.tabs([
    "📋 Candidatos", "⚡ Ativos", "📊 Impacto", "⚙️ Regras", "🏪 Lojas", "💰 Vendas", "🎧 SAC"
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


# ══════════════════════════════════════════════════════════════════════
# ABA 5 — LOJAS
# ══════════════════════════════════════════════════════════════════════

with aba_lojas:
    st.subheader("Comparativo por Loja")

    col_per, col_btn_loja = st.columns([3, 1])
    with col_per:
        period_loja = st.selectbox(
            "Período",
            ["week", "today", "month"],
            format_func=lambda x: {"week": "Semana", "today": "Hoje", "month": "Mês"}[x],
            key="period_loja",
        )
    with col_btn_loja:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        carregar_lojas = st.button("🔄 Carregar", type="primary", key="carregar_lojas")

    if carregar_lojas or "lojas_summary" not in st.session_state:
        with st.spinner("Buscando dados de todas as lojas..."):
            data, err = api("GET", f"/mixfoco/stores/summary?period={period_loja}")
        if err:
            st.error(f"Erro: {err}")
        elif data:
            st.session_state["lojas_summary"] = data

    summary = st.session_state.get("lojas_summary")
    if summary:
        stores = summary.get("stores", [])
        if not stores:
            st.info("Nenhuma loja com dados no período.")
        else:
            # ── KPIs totais ──────────────────────────────────────────
            total_spend   = sum(s["spend"] for s in stores)
            total_revenue = sum(s["revenue"] for s in stores)
            total_conv    = sum(s["conversions"] for s in stores)
            total_cand    = sum(s["candidates"] for s in stores)

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Gasto total", fmt_brl(total_spend))
            k2.metric("Receita total", fmt_brl(total_revenue))
            k3.metric("Conversões", total_conv)
            k4.metric("Candidatos Mixfoco", total_cand)

            st.divider()

            # ── Cards por loja ────────────────────────────────────────
            st.markdown("### Detalhes por loja")
            for s in stores:
                with st.container(border=True):
                    st.markdown(f"#### 🏪 {s['name']} `{s['store_key']}`")
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("Gasto",        fmt_brl(s["spend"]))
                    c2.metric("Receita",       fmt_brl(s["revenue"]))
                    c3.metric("ROAS médio",    f"{s['avg_roas']}x")
                    c4.metric("Conversões",    s["conversions"])
                    c5.metric("Candidatos",    s["candidates"])
                    c6.metric("Anúncios",      s["num_ads"])

            st.divider()

            # ── Gráfico comparativo ───────────────────────────────────
            st.markdown("### Gráfico comparativo")
            chart_metric = st.selectbox(
                "Métrica",
                ["revenue", "spend", "avg_roas", "conversions", "candidates"],
                format_func=lambda x: {
                    "revenue":     "Receita (R$)",
                    "spend":       "Gasto (R$)",
                    "avg_roas":    "ROAS médio",
                    "conversions": "Conversões",
                    "candidates":  "Candidatos Mixfoco",
                }[x],
                key="chart_metric",
            )

            chart_data = {s["store_key"]: s[chart_metric] for s in stores}
            st.bar_chart(chart_data, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════
# ABA 6 — VENDAS
# ══════════════════════════════════════════════════════════════════════

with aba_vendas:
    import pandas as pd
    from datetime import date as _date

    st.subheader("Vendas & Faturamento")

    # ── Filtros ──────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([2, 2, 2, 2, 1])
    with col_f1:
        data_ini = st.date_input("Data Início", value=_date.today(), key="v_date_from")
    with col_f2:
        data_fim = st.date_input("Data Fim", value=_date.today(), key="v_date_to")
    with col_f3:
        loja_v = st.text_input("Loja (vazio = todas)", placeholder="ex: MIXCONECTA", key="v_store")
    with col_f4:
        status_v = st.selectbox("Status", ["Todos", "Aprovados", "Cancelados"], key="v_status")
    with col_f5:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        buscar_v = st.button("🔍 Buscar", type="primary", key="buscar_vendas")

    if buscar_v:
        with st.spinner("Buscando pedidos ML..."):
            params = f"?date_from={data_ini}&date_to={data_fim}"
            if loja_v.strip():
                params += f"&store={loja_v.strip().upper()}"
            data, err = api("GET", f"/mixfoco/vendas/summary{params}")
        if err:
            st.error(f"Erro: {err}")
        elif data:
            for e in data.get("errors", []):
                st.warning(f"⚠️ {e}")
            st.session_state["vendas_data"] = data

    vdata = st.session_state.get("vendas_data")
    if vdata:
        s = vdata.get("summary", {})
        fat   = s.get("faturamento_ml", 0)
        tarif = s.get("tarifa_ml", 0)
        custo = s.get("custo_total", 0)
        impos = s.get("imposto_total", 0)
        frete_c = s.get("frete_comprador", 0)
        frete_v = s.get("frete_vendedor", 0)
        marg  = s.get("margem_total", 0)

        # ── KPIs linha 1 ─────────────────────────────────────────────
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Vendas Aprovadas",  s.get("vendas_aprovadas", 0),
                  help=f"{s.get('unidades_aprovadas',0)} unidades")
        k2.metric("Faturamento ML",    fmt_brl(fat))
        k3.metric("Canceladas",        s.get("vendas_canceladas", 0),
                  help=fmt_brl(s.get("faturamento_cancelado", 0)))
        k4.metric("Custo & Imposto",   fmt_brl(custo + impos))
        k5.metric("Tarifa de Venda",   fmt_brl(tarif))
        k6.metric("Margem Contrib.",   fmt_brl(marg),
                  delta=f"{s.get('margem_pct',0):.1f}%")

        # ── KPIs linha 2 ─────────────────────────────────────────────
        k7, k8, k9, k10, k11, k12 = st.columns(6)
        mod = s.get("por_modalidade", {})
        k7.metric("Full",     fmt_brl(mod.get("Full", 0)))
        k8.metric("Premium",  fmt_brl(mod.get("Premium", 0)))
        k9.metric("Clássico", fmt_brl(mod.get("Clássico", 0)))
        k10.metric("Ticket Médio",   fmt_brl(s.get("ticket_medio", 0)))
        k11.metric("Ticket Margem",  fmt_brl(s.get("ticket_margem", 0)))
        k12.metric("MC %",           f"{s.get('margem_pct',0):.1f}%")

        # ── Nivelar Custo por SKU ─────────────────────────────────────
        with st.expander("⚙️ Nivelar Custo & Imposto por SKU"):
            custos_data, _ = api("GET", "/mixfoco/custos")
            custos_map     = (custos_data or {}).get("custos", {})

            orders_all = vdata.get("orders", [])
            skus_uniq  = sorted({o["sku"] for o in orders_all if o["sku"]})

            if skus_uniq:
                custo_rows = []
                for sku in skus_uniq:
                    cfg = custos_map.get(sku, {})
                    custo_rows.append({
                        "SKU":          sku,
                        "Custo (R$)":   cfg.get("custo", 0.0),
                        "Imposto (%)":  cfg.get("imposto_pct", 0.0),
                    })
                df_custos = pd.DataFrame(custo_rows)
                edited = st.data_editor(df_custos, use_container_width=True,
                                        num_rows="fixed", key="editor_custos")
                if st.button("💾 Salvar custos", key="salvar_custos"):
                    payload = {
                        row["SKU"]: {"custo": row["Custo (R$)"], "imposto_pct": row["Imposto (%)"]}
                        for _, row in edited.iterrows() if row["SKU"]
                    }
                    result, err = api("POST", "/mixfoco/custos", json=payload)
                    if err:
                        st.error(f"Erro: {err}")
                    else:
                        st.success(f"✅ {result['total_skus']} SKUs salvos — refaça a busca para atualizar a tabela")

        # ── Tabela de pedidos ─────────────────────────────────────────
        st.divider()
        orders = vdata.get("orders", [])
        status_map = {"Todos": None, "Aprovados": "paid", "Cancelados": "cancelled"}
        status_sel = status_map[status_v]
        filtered = [o for o in orders if not status_sel or o["status"] == status_sel]

        search_v = st.text_input("🔍 Buscar por título ou SKU", key="v_search")
        if search_v.strip():
            q = search_v.strip().lower()
            filtered = [o for o in filtered if q in o["title"].lower() or q in o["sku"].lower()]

        st.caption(f"{len(filtered)} de {len(orders)} registros · {vdata.get('date_from')} → {vdata.get('date_to')}")

        if filtered:
            rows = []
            for o in filtered:
                fat_o   = o["faturamento_ml"]
                cst     = float(o.get("custo", 0))
                imp_pct = float(o.get("imposto_pct", 0))
                imp     = round(fat_o * imp_pct / 100, 2)
                tar     = o["tarifa_venda"]
                fc      = o["frete_comp"]
                fv      = o["frete_vend"]
                marg    = round(fat_o - cst - imp - tar - fv, 2)
                mc_pct  = round(marg / fat_o * 100, 2) if fat_o else 0.0
                rows.append({
                    "Anúncio":               o["title"],
                    "SKU":                   o["sku"] or "",
                    "Data":                  o["date_created"],
                    "Frete":                 o.get("modalidade", ""),
                    "Valor Unit.":           o["unit_price"],
                    "Qtd.":                  int(o["quantity"]),
                    "Faturamento ML":        fat_o,
                    "Custo (-)":             cst,
                    "Imposto (%)":           imp_pct,
                    "Tarifa de Venda (-)":   tar,
                    "Frete Comprador (-)":   fc,
                    "Frete Vendedor (-)":    fv,
                    "Margem de Contrib. (-)": marg,
                    "MC %":                  mc_pct,
                    "_sku":                  o["sku"],
                })

            df = pd.DataFrame(rows)

            READ_ONLY = ["Anúncio", "SKU", "Data", "Frete", "Valor Unit.", "Qtd.",
                         "Faturamento ML", "Tarifa de Venda (-)",
                         "Frete Comprador (-)", "Frete Vendedor (-)",
                         "Margem de Contrib. (-)", "MC %", "_sku"]

            edited = st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=READ_ONLY,
                column_config={
                    "Anúncio":               st.column_config.TextColumn(width="large"),
                    "SKU":                   st.column_config.TextColumn(width="small"),
                    "Data":                  st.column_config.TextColumn(width="small"),
                    "Frete":                 st.column_config.TextColumn(width="small"),
                    "Valor Unit.":           st.column_config.NumberColumn(format="%.2f"),
                    "Qtd.":                  st.column_config.NumberColumn(width="small"),
                    "Faturamento ML":        st.column_config.NumberColumn(format="%.2f"),
                    "Custo (-)":             st.column_config.NumberColumn(format="%.2f", min_value=0.0),
                    "Imposto (%)":           st.column_config.NumberColumn(format="%.2f", min_value=0.0, max_value=100.0),
                    "Tarifa de Venda (-)":   st.column_config.NumberColumn(format="%.2f"),
                    "Frete Comprador (-)":   st.column_config.NumberColumn(format="%.2f"),
                    "Frete Vendedor (-)":    st.column_config.NumberColumn(format="%.2f"),
                    "Margem de Contrib. (-)": st.column_config.NumberColumn(format="%.2f"),
                    "MC %":                  st.column_config.NumberColumn(format="%.1f"),
                    "_sku":                  None,
                },
                key="tabela_vendas",
            )

            col_save, col_csv = st.columns([3, 7])
            with col_save:
                if st.button("💾 Salvar custos & recalcular", key="salvar_tabela"):
                    payload = {}
                    for _, row in edited.iterrows():
                        sku = row.get("_sku", "")
                        if sku:
                            payload[sku] = {
                                "custo":       float(row["Custo (-)"]),
                                "imposto_pct": float(row["Imposto (%)"]),
                            }
                    if payload:
                        result, err = api("POST", "/mixfoco/custos", json=payload)
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success(f"✅ {result['total_skus']} SKUs salvos — refaça a busca para atualizar")
            with col_csv:
                export_df = edited.drop(columns=["_sku"], errors="ignore")
                csv = export_df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Exportar CSV", csv,
                                   file_name=f"vendas_{data_ini}_{data_fim}.csv",
                                   mime="text/csv")


# ══════════════════════════════════════════════════════════════════════
# ABA 7 — SAC (Atendimento)
# ══════════════════════════════════════════════════════════════════════

with aba_sac:
    import pandas as pd
    from datetime import date as _date

    st.subheader("SAC — Atendimento ao Cliente")

    sub_painel, sub_tickets, sub_kb = st.tabs(["📊 Painel", "🎫 Tickets", "📚 Base de Conhecimento"])

    # ── PAINEL ───────────────────────────────────────────────────────
    with sub_painel:
        col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
        with col_d1:
            sac_de = st.date_input("De", value=_date.today().replace(day=1), key="sac_de")
        with col_d2:
            sac_ate = st.date_input("Até", value=_date.today(), key="sac_ate")
        with col_d3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            carregar_painel = st.button("🔄 Carregar", key="carregar_sac_painel")

        if carregar_painel or "sac_dashboard" not in st.session_state:
            with st.spinner("Buscando KPIs do SAC..."):
                data, err = api("GET", f"/mixfoco/sac/dashboard?de={sac_de}&ate={sac_ate}")
            if err:
                st.error(f"Erro: {err}")
            elif data:
                st.session_state["sac_dashboard"] = data

        dash = st.session_state.get("sac_dashboard")
        if dash:
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Volume", dash.get("volume", dash.get("total", "—")))
            k2.metric("TMA", dash.get("tma", "—"))
            k3.metric("TMR", dash.get("tmr", "—"))
            sla_v = dash.get("sla")
            k4.metric("SLA", f"{sla_v}%" if sla_v is not None else "—")
            k5.metric("Satisfação", dash.get("satisfacao", dash.get("csat", "—")))
            k6.metric("Abertos", dash.get("abertos", dash.get("open", "—")))

            ranking = dash.get("ranking") or dash.get("ranking_operadores")
            if ranking:
                st.markdown("### Ranking de operadores")
                st.dataframe(pd.DataFrame(ranking), use_container_width=True, hide_index=True)

            with st.expander("Ver dados completos (JSON)"):
                st.json(dash)
        else:
            st.info("Clique em Carregar para ver os KPIs do período.")

    # ── TICKETS ──────────────────────────────────────────────────────
    with sub_tickets:
        col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([2, 2, 2, 2, 1])
        with col_t1:
            status_t = st.selectbox(
                "Status",
                ["Todos", "aberto", "em_andamento", "aguardando", "resolvido", "fechado"],
                key="sac_status",
            )
        with col_t2:
            canal_t = st.text_input("Canal", placeholder="ex: ML, whatsapp", key="sac_canal")
        with col_t3:
            urgencia_t = st.selectbox("Urgência", ["Todas", "baixa", "media", "alta", "critica"], key="sac_urgencia")
        with col_t4:
            busca_t = st.text_input("Buscar", placeholder="pedido, cliente...", key="sac_busca")
        with col_t5:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            buscar_tickets = st.button("🔍", key="buscar_sac_tickets")

        if buscar_tickets or "sac_tickets" not in st.session_state:
            params = "?limit=50"
            if status_t != "Todos":
                params += f"&status={status_t}"
            if canal_t.strip():
                params += f"&canal={canal_t.strip()}"
            if urgencia_t != "Todas":
                params += f"&urgencia={urgencia_t}"
            if busca_t.strip():
                params += f"&q={busca_t.strip()}"
            with st.spinner("Buscando tickets..."):
                data, err = api("GET", f"/mixfoco/sac/tickets{params}")
            if err:
                st.error(f"Erro: {err}")
            elif data is not None:
                st.session_state["sac_tickets"] = data.get("tickets", data if isinstance(data, list) else [])

        tickets = st.session_state.get("sac_tickets", [])
        if not tickets:
            st.info("Nenhum ticket encontrado.")
        else:
            st.markdown(f"**{len(tickets)} ticket(s)**")
            for t in tickets:
                tid = t.get("id") or t.get("ticket_id")
                with st.container(border=True):
                    col_i, col_s, col_b = st.columns([5, 2, 2])
                    with col_i:
                        st.markdown(f"**#{tid}** · {t.get('cliente', t.get('comprador', '—'))}")
                        st.caption(f"{t.get('canal', '—')} · {t.get('assunto', t.get('titulo', '—'))}")
                    with col_s:
                        st.caption(f"Status: {t.get('status', '—')}")
                        st.caption(f"Urgência: {t.get('urgencia', '—')}")
                    with col_b:
                        st.markdown("&nbsp;", unsafe_allow_html=True)
                        if st.button("👁️ Abrir", key=f"abrir_{tid}"):
                            st.session_state["sac_ticket_aberto"] = tid
                            st.rerun()

        ticket_aberto = st.session_state.get("sac_ticket_aberto")
        if ticket_aberto:
            st.divider()
            with st.spinner("Carregando ticket..."):
                detalhe, err = api("GET", f"/mixfoco/sac/tickets/{ticket_aberto}")
            if err:
                st.error(f"Erro: {err}")
            else:
                st.markdown(f"### 🎫 Ticket #{ticket_aberto}")
                col_msgs, col_ia = st.columns([3, 2])

                with col_msgs:
                    mensagens = detalhe.get("mensagens", detalhe.get("mensagens_ticket", []))
                    for m in mensagens:
                        autor = m.get("autor", m.get("de", "—"))
                        st.markdown(f"**{autor}** _{fmt_dt(m.get('data', m.get('created_at')))}_")
                        st.write(m.get("texto", m.get("mensagem", "")))
                        st.divider()

                    nova_msg = st.text_area("Responder", key=f"nova_msg_{ticket_aberto}")
                    if st.button("📤 Enviar resposta", key=f"enviar_{ticket_aberto}"):
                        result, err = api(
                            "POST",
                            f"/mixfoco/sac/tickets/{ticket_aberto}/mensagem",
                            json={"texto": nova_msg},
                        )
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success("✅ Resposta enviada!")
                            st.rerun()

                with col_ia:
                    st.markdown("#### 🤖 Assistente IA")
                    if st.button("💡 Sugerir resposta", key=f"sugerir_{ticket_aberto}"):
                        with st.spinner("Gerando sugestão..."):
                            sug, err = api("POST", "/mixfoco/sac/ia/sugerir", json={"ticket_id": ticket_aberto})
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.session_state[f"sugestao_{ticket_aberto}"] = sug.get(
                                "sugestao", sug.get("resposta", sug)
                            )

                    sugestao = st.session_state.get(f"sugestao_{ticket_aberto}")
                    if sugestao:
                        st.text_area(
                            "Sugestão da IA", value=str(sugestao),
                            key=f"sugestao_texto_{ticket_aberto}", height=150,
                        )
                        if st.button("↩️ Usar sugestão", key=f"usar_sugestao_{ticket_aberto}"):
                            st.session_state[f"nova_msg_{ticket_aberto}"] = str(sugestao)
                            st.rerun()

                    col_ia1, col_ia2 = st.columns(2)
                    with col_ia1:
                        if st.button("🏷️ Classificar", key=f"classificar_{ticket_aberto}"):
                            with st.spinner("Classificando..."):
                                cls, err = api("POST", "/mixfoco/sac/ia/classificar", json={"ticket_id": ticket_aberto})
                            if err:
                                st.error(f"Erro: {err}")
                            else:
                                st.json(cls)
                        if st.button("📋 Resumir", key=f"resumir_{ticket_aberto}"):
                            with st.spinner("Resumindo..."):
                                res, err = api("POST", "/mixfoco/sac/ia/resumir", json={"ticket_id": ticket_aberto})
                            if err:
                                st.error(f"Erro: {err}")
                            else:
                                st.json(res)
                    with col_ia2:
                        if st.button("⚠️ Urgência", key=f"urgencia_{ticket_aberto}"):
                            with st.spinner("Avaliando urgência..."):
                                urg, err = api("POST", "/mixfoco/sac/ia/urgencia", json={"ticket_id": ticket_aberto})
                            if err:
                                st.error(f"Erro: {err}")
                            else:
                                st.json(urg)

                col_a1, col_a2, col_a3, col_a4 = st.columns([2, 3, 2, 2])
                with col_a1:
                    if st.button("🙋 Assumir ticket", key=f"assumir_{ticket_aberto}"):
                        _, err = api("POST", f"/mixfoco/sac/tickets/{ticket_aberto}/assumir")
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success("Ticket assumido!")
                            st.rerun()
                with col_a2:
                    novo_status = st.selectbox(
                        "Mudar status",
                        ["aberto", "em_andamento", "aguardando", "resolvido", "fechado"],
                        key=f"status_sel_{ticket_aberto}",
                    )
                with col_a3:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("✅ Atualizar", key=f"atualizar_status_{ticket_aberto}"):
                        _, err = api(
                            "POST", f"/mixfoco/sac/tickets/{ticket_aberto}/status",
                            json={"status": novo_status},
                        )
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.success("Status atualizado!")
                            st.rerun()
                with col_a4:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("⬅️ Fechar visão", key=f"fechar_view_{ticket_aberto}"):
                        st.session_state.pop("sac_ticket_aberto", None)
                        st.rerun()

    # ── BASE DE CONHECIMENTO ───────────────────────────────────────────
    with sub_kb:
        st.markdown("### Base de Conhecimento")
        st.caption("Respostas padrão e informações que a IA usa para sugerir respostas no SAC.")

        col_k1, col_k2, col_k3 = st.columns([3, 2, 1])
        with col_k1:
            kb_busca = st.text_input("Buscar", placeholder="palavra-chave", key="kb_busca")
        with col_k2:
            kb_categoria = st.text_input("Categoria", placeholder="ex: devolução, garantia", key="kb_categoria")
        with col_k3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            kb_recarregar = st.button("🔄", key="kb_recarregar")

        if kb_recarregar or "kb_entries" not in st.session_state:
            params = []
            if kb_busca.strip():
                params.append(f"q={kb_busca.strip()}")
            if kb_categoria.strip():
                params.append(f"categoria={kb_categoria.strip()}")
            qs = "?" + "&".join(params) if params else ""
            with st.spinner("Buscando base de conhecimento..."):
                data, err = api("GET", f"/mixfoco/sac/kb{qs}")
            if err:
                st.error(f"Erro: {err}")
            elif data is not None:
                st.session_state["kb_entries"] = data.get(
                    "entries", data.get("items", data if isinstance(data, list) else [])
                )

        entries = st.session_state.get("kb_entries", [])
        st.markdown(f"**{len(entries)} entrada(s)**")

        for e in entries:
            eid = e.get("id") or e.get("entry_id")
            with st.container(border=True):
                col_e1, col_e2 = st.columns([5, 1])
                with col_e1:
                    st.markdown(f"**{e.get('titulo', e.get('pergunta', '—'))}**")
                    st.caption(f"Categoria: {e.get('categoria', '—')} · Marketplace: {e.get('marketplace', 'todos')}")
                    st.write(e.get("resposta", e.get("conteudo", "")))
                with col_e2:
                    if st.button("✏️ Editar", key=f"editar_kb_{eid}"):
                        st.session_state["kb_editando"] = eid
                        st.rerun()
                    if st.button("🗑️ Remover", key=f"del_kb_{eid}"):
                        _, err = api("DELETE", f"/mixfoco/sac/kb/{eid}")
                        if err:
                            st.error(f"Erro: {err}")
                        else:
                            st.session_state.pop("kb_entries", None)
                            st.rerun()

        st.divider()
        editando_id = st.session_state.get("kb_editando")
        entry_edit = None
        if editando_id:
            entry_edit = next(
                (e for e in entries if str(e.get("id") or e.get("entry_id")) == str(editando_id)), None
            )

        st.markdown("### ✏️ Editar entrada" if entry_edit else "### ➕ Nova entrada")
        with st.form("form_kb", clear_on_submit=not entry_edit):
            titulo = st.text_input(
                "Título/Pergunta",
                value=entry_edit.get("titulo", entry_edit.get("pergunta", "")) if entry_edit else "",
            )
            categoria = st.text_input("Categoria", value=entry_edit.get("categoria", "") if entry_edit else "")
            marketplace = st.text_input(
                "Marketplace (vazio = todos)", value=entry_edit.get("marketplace", "") if entry_edit else ""
            )
            resposta = st.text_area(
                "Resposta/Conteúdo",
                value=entry_edit.get("resposta", entry_edit.get("conteudo", "")) if entry_edit else "",
                height=120,
            )
            ativo = st.toggle("Ativo", value=entry_edit.get("ativo", True) if entry_edit else True)

            col_sub, col_cancel = st.columns([1, 1])
            with col_sub:
                submitted_kb = st.form_submit_button("💾 Salvar", type="primary")
            with col_cancel:
                cancelar_kb = st.form_submit_button("✖ Cancelar") if entry_edit else False

            if submitted_kb:
                payload = {
                    "titulo": titulo,
                    "categoria": categoria,
                    "marketplace": marketplace or None,
                    "resposta": resposta,
                    "ativo": ativo,
                }
                if entry_edit:
                    result, err = api("PUT", f"/mixfoco/sac/kb/{editando_id}", json=payload)
                else:
                    result, err = api("POST", "/mixfoco/sac/kb", json=payload)
                if err:
                    st.error(f"Erro: {err}")
                else:
                    st.success("✅ Entrada salva!")
                    st.session_state.pop("kb_entries", None)
                    st.session_state.pop("kb_editando", None)
                    st.rerun()

            if cancelar_kb:
                st.session_state.pop("kb_editando", None)
                st.rerun()
