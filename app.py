import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Solicitações — Análise de Dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Arquivo local para salvar as demandas ───────────────────────────────────
ARQUIVO = "demandas.json"

# ── Funções de persistência ─────────────────────────────────────────────────
def carregar_demandas():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_demandas(demandas):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(demandas, f, ensure_ascii=False, indent=2, default=str)

# ── CSS personalizado ────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Importa fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Esconde o menu do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Cabeçalho customizado */
    .header-bar {
        background: linear-gradient(135deg, #1a3a5c 0%, #185FA5 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    .header-bar h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 600;
        color: white;
    }
    .header-bar p {
        margin: 0.3rem 0 0;
        font-size: 0.9rem;
        opacity: 0.85;
        color: white;
    }

    /* Cards de seção */
    .section-card {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .section-title {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #6b7a8d;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #f0f2f5;
    }

    /* Avisos informativos */
    .info-box {
        background: #EBF5FB;
        border-left: 4px solid #185FA5;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        font-size: 0.88rem;
        color: #1a3a5c;
        margin-bottom: 0.8rem;
    }
    .warning-box {
        background: #FEF9EC;
        border-left: 4px solid #F4A62A;
        border-radius: 6px;
        padding: 0.75rem 1rem;
        font-size: 0.88rem;
        color: #7a5000;
        margin-bottom: 0.8rem;
    }

    /* Badges de status */
    .badge-aberta   { background:#FEF3E2; color:#854F0B; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }
    .badge-execucao { background:#E6F1FB; color:#185FA5; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }
    .badge-concluida{ background:#EAF3DE; color:#3B6D11; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }

    /* Inputs */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {
        border-radius: 8px !important;
        border: 1px solid #d0d7de !important;
    }

    /* Botão principal */
    .stButton > button[kind="primary"] {
        background: #185FA5 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.6rem 2rem !important;
    }

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #e8ecf0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #185FA5 !important;
        color: white !important;
    }

    /* Tabela de demandas */
    .demanda-row {
        background: white;
        border: 1px solid #e8ecf0;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        cursor: pointer;
        transition: border-color 0.15s;
    }
    .demanda-row:hover {
        border-color: #185FA5;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CABEÇALHO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="header-bar">
    <h1>📊 Setor de Análise de Dados</h1>
    <p>Sistema de solicitações e gerenciamento de demandas</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ABAS PRINCIPAIS
# ══════════════════════════════════════════════════════════════════════════════
aba_form, aba_admin = st.tabs(["📝  Formulário de Solicitação", "⚙️  Painel do Administrador"])


# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — FORMULÁRIO DO SOLICITANTE
# ══════════════════════════════════════════════════════════════════════════════
with aba_form:

    st.markdown("### Nova solicitação")
    st.markdown("Preencha todos os campos para registrar sua demanda.")
    st.markdown("")

    # ── Identificação ────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="section-title">👤 Identificação</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome completo *",
                placeholder="Nome e sobrenome",
                help="Informe seu nome e pelo menos um sobrenome."
            )

        with col2:
            setor = st.selectbox(
                "Setor / Departamento *",
                options=[
                    "", "Comercial", "Educação", "Faturamento",
                    "Financeiro", "Logística", "Marketing",
                    "Televendas", "Direção", "Outro"
                ]
            )

    st.markdown("---")

    # ── Tipo de Solicitação ──────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="section-title">📋 Tipo de solicitação</div>', unsafe_allow_html=True)

        TIPOS = [
            "Relatório",
            "Dashboard",
            "Extração de dados",
            "Indicadores / KPIs",
            "Automação de processo",
            "Correção / Ajuste de relatório",
            "Estudo / Análise específica",
        ]

        tipo = st.radio(
            "Selecione o tipo *",
            options=TIPOS,
            horizontal=True,
            label_visibility="collapsed",
        )

    st.markdown("---")

    # ── Detalhes ─────────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="section-title">📝 Detalhes da solicitação</div>', unsafe_allow_html=True)

        objetivo = st.text_area(
            "Objetivo da solicitação *",
            placeholder="Descreva de forma clara o que precisa ser desenvolvido ou analisado...",
            height=110,
        )

        contexto = st.text_area(
            "Contexto do negócio *",
            placeholder="Explique o motivo da solicitação e qual decisão ou processo será impactado...",
            height=110,
        )

    st.markdown("---")

    # ── Entrega ──────────────────────────────────────────────────────────────
    with st.container():
        st.markdown('<div class="section-title">📦 Entrega</div>', unsafe_allow_html=True)

        col3, col4 = st.columns(2)

        with col3:
            resultado = st.selectbox(
                "Resultado esperado *",
                options=["", "Excel", "Dashboard", "PDF", "Outro"]
            )

        with col4:
            frequencia = st.selectbox(
                "Frequência de entrega *",
                options=[
                    "", "Solicitação única", "Diária", "Semanal",
                    "Quinzenal", "Mensal", "Sob demanda"
                ]
            )

    st.markdown("")

    # ── Informativos ─────────────────────────────────────────────────────────
    st.markdown("""
    <div class="info-box">
        📎 <strong>Anexos:</strong> Caso tenha algum arquivo relevante, envie para
        <strong>analise.dados@empresa.com.br</strong> com o assunto: <em>Anexo – [seu nome]</em>.
    </div>
    <div class="warning-box">
        🕐 <strong>Prazo de entrega:</strong> a ser definido após análise da demanda pela equipe.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # ── Botão de envio ───────────────────────────────────────────────────────
    col_btn, col_vazio = st.columns([1, 3])
    with col_btn:
        enviar = st.button("📤  Enviar solicitação", type="primary", use_container_width=True)

    if enviar:
        # Validações
        erros = []
        if not nome.strip():
            erros.append("Nome completo é obrigatório.")
        elif len(nome.strip().split()) < 2:
            erros.append("Informe nome e sobrenome.")
        if not setor:
            erros.append("Selecione o setor/departamento.")
        if not objetivo.strip():
            erros.append("Descreva o objetivo da solicitação.")
        if not contexto.strip():
            erros.append("Descreva o contexto do negócio.")
        if not resultado:
            erros.append("Selecione o resultado esperado.")
        if not frequencia:
            erros.append("Selecione a frequência de entrega.")

        if erros:
            for e in erros:
                st.error(f"⚠️ {e}")
        else:
            # Salva a demanda
            demandas = carregar_demandas()
            nova = {
                "id": int(datetime.now().timestamp() * 1000),
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "nome": nome.strip(),
                "setor": setor,
                "tipo": tipo,
                "objetivo": objetivo.strip(),
                "contexto": contexto.strip(),
                "resultado": resultado,
                "frequencia": frequencia,
                "status": "Aberta",
                "analista": "",
                "prazo": "",
            }
            demandas.insert(0, nova)
            salvar_demandas(demandas)
            st.success("✅ Solicitação enviada com sucesso! Em breve a equipe entrará em contato.")
            st.balloons()


# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — PAINEL DO ADMINISTRADOR
# ══════════════════════════════════════════════════════════════════════════════
with aba_admin:

    demandas = carregar_demandas()

    st.markdown("### Painel do administrador")

    if not demandas:
        st.info("📭 Nenhuma demanda registrada ainda. Quando alguém enviar uma solicitação, ela aparecerá aqui.")
    else:
        # ── Métricas rápidas ─────────────────────────────────────────────────
        total    = len(demandas)
        abertas  = sum(1 for d in demandas if d["status"] == "Aberta")
        execucao = sum(1 for d in demandas if d["status"] == "Em execução")
        concl    = sum(1 for d in demandas if d["status"] == "Concluída")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", total)
        m2.metric("🟡 Abertas", abertas)
        m3.metric("🔵 Em execução", execucao)
        m4.metric("🟢 Concluídas", concl)

        st.markdown("---")

        # ── Filtro por status ────────────────────────────────────────────────
        filtro = st.selectbox(
            "Filtrar por status",
            ["Todas", "Aberta", "Em execução", "Concluída"],
            label_visibility="visible",
        )

        lista_filtrada = demandas if filtro == "Todas" else [d for d in demandas if d["status"] == filtro]

        st.markdown(f"**{len(lista_filtrada)} demanda(s) exibida(s)**")
        st.markdown("")

        # ── Lista de demandas ────────────────────────────────────────────────
        for i, d in enumerate(lista_filtrada):

            badge_map = {
                "Aberta":       "badge-aberta",
                "Em execução":  "badge-execucao",
                "Concluída":    "badge-concluida",
            }
            badge = badge_map.get(d["status"], "badge-aberta")

            with st.expander(
                f"📄  {d['nome']}  ·  {d['tipo']}  ·  {d['data']}",
                expanded=False,
            ):
                col_info, col_form = st.columns([1, 1])

                # Coluna esquerda: informações da solicitação
                with col_info:
                    st.markdown("**Detalhes da solicitação**")
                    st.markdown(f"**Solicitante:** {d['nome']}")
                    st.markdown(f"**Setor:** {d['setor']}")
                    st.markdown(f"**Tipo:** {d['tipo']}")
                    st.markdown(f"**Resultado esperado:** {d['resultado']}  ·  **Frequência:** {d['frequencia']}")
                    st.markdown(f"**Data de envio:** {d['data']}")

                    st.markdown("**Objetivo:**")
                    st.info(d["objetivo"])

                    st.markdown("**Contexto do negócio:**")
                    st.info(d["contexto"])

                # Coluna direita: ações do admin
                with col_form:
                    st.markdown("**Gerenciar demanda**")

                    novo_status = st.selectbox(
                        "Status",
                        ["Aberta", "Em execução", "Concluída"],
                        index=["Aberta", "Em execução", "Concluída"].index(d["status"]),
                        key=f"status_{d['id']}",
                    )

                    novo_analista = st.selectbox(
                        "Vincular analista",
                        ["", "Ana Lima", "Carlos Melo", "Priya Singh"],
                        index=["", "Ana Lima", "Carlos Melo", "Priya Singh"].index(d.get("analista", "") or ""),
                        key=f"analista_{d['id']}",
                    )

                    novo_prazo = st.date_input(
                        "Prazo de entrega",
                        value=datetime.strptime(d["prazo"], "%Y-%m-%d").date() if d.get("prazo") else None,
                        key=f"prazo_{d['id']}",
                        format="DD/MM/YYYY",
                    )

                    if st.button("💾  Salvar alterações", key=f"salvar_{d['id']}", type="primary"):
                        # Atualiza no arquivo JSON
                        todas = carregar_demandas()
                        for dem in todas:
                            if dem["id"] == d["id"]:
                                dem["status"]   = novo_status
                                dem["analista"] = novo_analista
                                dem["prazo"]    = str(novo_prazo) if novo_prazo else ""
                                break
                        salvar_demandas(todas)
                        st.success("✅ Demanda atualizada!")
                        st.rerun()

        # ── Exportar para Excel ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**Exportar dados**")

        df = pd.DataFrame(demandas)
        col_cols = ["data","nome","setor","tipo","objetivo","contexto","resultado","frequencia","status","analista","prazo"]
        df = df[[c for c in col_cols if c in df.columns]]
        df.columns = ["Data","Nome","Setor","Tipo","Objetivo","Contexto","Resultado","Frequência","Status","Analista","Prazo"]

        excel_bytes = df.to_excel.__module__  # só pra verificar se pandas tem openpyxl
        csv_data = df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="⬇️  Baixar como CSV (Excel)",
            data=csv_data,
            file_name=f"demandas_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
