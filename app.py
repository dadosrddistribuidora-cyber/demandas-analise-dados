import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import time
 
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import WorksheetNotFound
 
st.set_page_config(
    page_title="Solicitações — Análise de Dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
 
# ── Senhas ──────────────────────────────────────────────────────────────────
# As senhas agora vêm do Streamlit Secrets.
# No Streamlit Cloud, confira em: App > Settings > Secrets.
SENHAS = dict(st.secrets.get("senhas", {}))
 
SENHA_LIDER = SENHAS.get("lider", "lider123")
SENHA_ANALISTA = {
    "Artur": SENHAS.get("artur", "artur10"),
    "Gabriel": SENHAS.get("gabriel", "gabriel20"),
    "Edson": SENHAS.get("edson", "edson30"),
    "Carol": SENHAS.get("carol", "Carol26"),
}
 
# ── Google Sheets ────────────────────────────────────────────────────────────
NOME_ABA = "Demandas"
COLUNAS = [
    "id", "data", "nome", "setor", "tipo", "objetivo", "contexto",
    "resultado", "frequencia", "status", "analista", "prazo",
    "classificacao_lider", "comentario_lider",
]
 
# Fuso horário local da RD/RN/PB.
FUSO_BRASIL = ZoneInfo("America/Fortaleza")
 
def agora_brasil():
    """Retorna a data/hora atual no fuso de RN/PB, independente do servidor do Streamlit."""
    return datetime.now(FUSO_BRASIL)
 
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
 
@st.cache_resource(ttl=3600)
def _obter_aba_cacheada():
    """
    Cria a conexão completa com o Sheets e cacheia o objeto aba por 1 hora.
    Após 1 hora o Streamlit descarta o cache e reconecta automaticamente,
    evitando sessão expirada sem fazer novas requisições a cada operação.
    """
    service_account_info = dict(st.secrets["gcp_service_account"])
    service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
    credenciais = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open_by_key(st.secrets["sheets"]["id"])
 
    try:
        aba = planilha.worksheet(NOME_ABA)
    except WorksheetNotFound:
        aba = planilha.add_worksheet(title=NOME_ABA, rows=1000, cols=len(COLUNAS))
 
    # Garante cabeçalho correto na primeira vez
    cabecalho_atual = aba.row_values(1)
    if cabecalho_atual != COLUNAS:
        aba.update([COLUNAS], "A1")
 
    return aba
 
def conectar_aba_demandas():
    """Retorna a aba cacheada, com retry automático em caso de erro 429 (quota excedida)."""
    for tentativa in range(1, 4):  # até 3 tentativas
        try:
            return _obter_aba_cacheada()
        except Exception as erro:
            erro_str = str(erro)
            _obter_aba_cacheada.clear()  # força reconexão limpa na próxima tentativa
 
            if "429" in erro_str and tentativa < 3:
                # Cota excedida: aguarda e tenta novamente silenciosamente
                time.sleep(5 * tentativa)  # 5s, depois 10s
                continue
 
            # Erro diferente de 429, ou esgotou as tentativas
            st.error("Não foi possível conectar ao Google Sheets.")
            st.info(
                "Confira se o Google Sheets foi compartilhado com o e-mail da service account "
                "e se o ID da planilha está correto no Secrets."
            )
            st.exception(erro)
            st.stop()
 
def migrar_json_para_sheets_se_existir(aba):
    """Migra demandas antigas do arquivo local demandas.json, se ele existir e a planilha estiver vazia."""
    try:
        if aba.get_all_records():
            return
 
        if not os.path.exists("demandas.json"):
            return
 
        with open("demandas.json", "r", encoding="utf-8") as arquivo:
            demandas_antigas = json.load(arquivo)
 
        if not demandas_antigas:
            return
 
        linhas = []
        for demanda in demandas_antigas:
            linhas.append([demanda.get(coluna, "") for coluna in COLUNAS])
 
        aba.clear()
        aba.update([COLUNAS] + linhas, "A1")
        st.toast("Demandas antigas migradas do demandas.json para o Google Sheets.")
 
    except Exception as e:
        # A migração é apenas uma segurança extra. Se falhar, o app continua funcionando.
        st.warning(f"Aviso na migração do demandas.json: {e}")
 
def carregar_demandas():
    """Lê todas as demandas da aba Demandas."""
    aba = conectar_aba_demandas()
 
    # Migra do JSON legado apenas uma vez por sessão
    if not st.session_state.get("_migracao_feita"):
        migrar_json_para_sheets_se_existir(aba)
        st.session_state["_migracao_feita"] = True
 
    registros = aba.get_all_records()
 
    demandas = []
    for registro in registros:
        if not registro.get("id"):
            continue
 
        demanda = {coluna: registro.get(coluna, "") for coluna in COLUNAS}
 
        try:
            demanda["id"] = int(float(demanda["id"]))
        except Exception:
            pass
 
        if not demanda.get("status"):
            demanda["status"] = "Aberta"
        if demanda.get("prazo"):
            demanda["prazo"] = str(demanda["prazo"])
        if not demanda.get("classificacao_lider"):
            demanda["classificacao_lider"] = "Aberto"
 
        demandas.append(demanda)
 
    # Mantém as mais recentes primeiro, como já acontecia no JSON.
    demandas.sort(key=lambda d: int(d.get("id", 0)), reverse=True)
    return demandas
 
def salvar_demandas(demandas):
    """Regrava a planilha com a lista atualizada de demandas."""
 
    # Segurança: nunca apaga o Sheets se a lista estiver vazia.
    # Isso evita perda de dados caso carregar_demandas() tenha falhado silenciosamente.
    if not demandas:
        st.error("⛔ Operação cancelada: tentativa de salvar lista vazia. Nenhum dado foi alterado.")
        st.stop()
 
    aba = conectar_aba_demandas()
 
    # Lê quantas linhas existem atualmente no Sheets antes de apagar.
    linhas_atuais = aba.get_all_records()
 
    # Segunda segurança: se o Sheets tem dados mas a lista nova tem menos da metade,
    # algo deu errado na leitura. Cancela para não apagar registros existentes.
    if linhas_atuais and len(demandas) < len(linhas_atuais) / 2:
        st.error(
            f"⛔ Operação cancelada: o Sheets tem {len(linhas_atuais)} registros, "
            f"mas a lista a salvar tem apenas {len(demandas)}. "
            "Recarregue a página e tente novamente."
        )
        st.stop()
 
    linhas = []
    for demanda in demandas:
        linhas.append([demanda.get(coluna, "") for coluna in COLUNAS])
 
    aba.clear()
    aba.update([COLUNAS] + linhas, "A1")
 
# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
 
.header-bar {
    background: linear-gradient(135deg, #1a3a5c 0%, #185FA5 100%);
    padding: 1.2rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; color: white;
}
.header-bar h1 { margin: 0; font-size: 1.5rem; font-weight: 600; color: white; }
.header-bar p  { margin: 0.2rem 0 0; font-size: 0.85rem; opacity: 0.85; color: white; }
 
.info-box {
    background: #EBF5FB; border-left: 4px solid #185FA5; border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem; font-size: 0.88rem; color: #1a3a5c; margin-bottom: 0.8rem;
}
.warning-box {
    background: #FEF9EC; border-left: 4px solid #F4A62A; border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem; font-size: 0.88rem; color: #7a5000; margin-bottom: 0.8rem;
}
 
.metric-card {
    background: white; border: 1px solid #e8ecf0; border-radius: 10px;
    padding: 1rem 1.2rem; text-align: center;
}
.metric-card .num  { font-size: 2rem; font-weight: 600; color: #185FA5; }
.metric-card .lbl  { font-size: 0.8rem; color: #6b7a8d; margin-top: 2px; }
 
.analista-card {
    background: white; border: 1px solid #e8ecf0; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
}
.analista-card h4 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #1a3a5c; }
 
.badge-aberta    { background:#FEF3E2; color:#854F0B; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-execucao  { background:#E6F1FB; color:#185FA5; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-concluida { background:#EAF3DE; color:#3B6D11; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-duplicado   { background:#F3E8FF; color:#6B21A8; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-improcedente { background:#FFE4E4; color:#991B1B; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:500; }
 
.lock-card {
    max-width: 380px; margin: 3rem auto; background: white;
    border: 1px solid #e8ecf0; border-radius: 16px; padding: 2.5rem 2rem; text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.07);
}
.lock-card h2 { font-size: 1.2rem; color: #1a3a5c; margin-bottom: 0.4rem; }
.lock-card p  { font-size: 0.85rem; color: #6b7a8d; margin-bottom: 1.5rem; }
 
.stButton > button[kind="primary"] {
    background: #185FA5 !important; border: none !important;
    border-radius: 8px !important; font-weight: 500 !important;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 2px solid #e8ecf0; }
.stTabs [aria-selected="true"] { background: #185FA5 !important; color: white !important; border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)
 
# ── Inicializa session state ─────────────────────────────────────────────────
if "logado_como" not in st.session_state:
    st.session_state.logado_como = None  # None | "lider" | nome_analista
if "form_enviado" not in st.session_state:
    st.session_state.form_enviado = False
if "expander_aberto_lider" not in st.session_state:
    st.session_state.expander_aberto_lider = None
 
# ══════════════════════════════════════════════════════════════════════════════
# CABEÇALHO
# ══════════════════════════════════════════════════════════════════════════════
col_h, col_logout = st.columns([5, 1])
with col_h:
    st.markdown("""
    <div class="header-bar">
        <h1>📊 Setor de Análise de Dados</h1>
        <p>Sistema de solicitações e gerenciamento de demandas</p>
    </div>
    """, unsafe_allow_html=True)
with col_logout:
    if st.session_state.logado_como:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 Sair", use_container_width=True):
            st.session_state.logado_como = None
            st.rerun()
 
# ══════════════════════════════════════════════════════════════════════════════
# ABAS PRINCIPAIS
# ══════════════════════════════════════════════════════════════════════════════
aba_form, aba_lider, aba_analista = st.tabs([
    "📝  Formulário de Solicitação",
    "👑  Painel do Líder",
    "👤  Painel do Analista",
])
 
# ══════════════════════════════════════════════════════════════════════════════
# ABA 1 — FORMULÁRIO DO SOLICITANTE
# ══════════════════════════════════════════════════════════════════════════════
with aba_form:
 
    # Se acabou de enviar com sucesso, mostra confirmação e botão para nova solicitação
    if st.session_state.form_enviado:
        st.success("✅ Sua solicitação foi enviada com sucesso!")
        st.balloons()
        st.markdown("A equipe de Análise de Dados receberá sua demanda e entrará em contato pelo WhatsApp com o prazo de entrega.")
        if st.button("📝 Fazer nova solicitação", type="primary"):
            st.session_state.form_enviado = False
            st.rerun()
        st.stop()
 
    st.markdown("### Nova solicitação")
    st.markdown("Preencha todos os campos para registrar sua demanda.")
    st.markdown("")
 
    with st.container():
        st.markdown("**👤 Identificação**")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome completo *", placeholder="Nome e sobrenome", key="f_nome")
        with col2:
            setor = st.selectbox("Setor / Departamento *", options=[
                "", "Comercial", "Educação", "Gerencia Administrativa", "Faturamento", "Financeiro",
                "Logística", "Marketing", "Televendas", "Direção", "Industria", "Outro"
            ], key="f_setor")
 
    st.markdown("---")
    st.markdown("**📋 Tipo de solicitação**")
    tipo = st.radio("", options=[
        "Relatório", "Dashboard", "Extração de dados", "Indicadores / KPIs",
        "Automação de processo", "Correção / Ajuste de relatório", "Estudo / Análise específica",
    ], horizontal=True, label_visibility="collapsed", key="f_tipo")
 
    st.markdown("---")
    st.markdown("**📝 Detalhes**")
    objetivo = st.text_area("Objetivo da solicitação *",
        placeholder="Descreva de forma clara o que precisa ser desenvolvido ou analisado...", height=100, key="f_objetivo")
    contexto = st.text_area("Contexto do negócio *",
        placeholder="Explique o motivo da solicitação e qual decisão ou processo será impactado...", height=100, key="f_contexto")
 
    st.markdown("---")
    st.markdown("**📦 Entrega**")
    col3, col4 = st.columns(2)
    with col3:
        resultado = st.selectbox("Resultado esperado *", options=["", "Excel", "Dashboard", "PDF", "Outro"], key="f_resultado")
    with col4:
        frequencia = st.selectbox("Frequência de entrega *", options=[
            "", "Solicitação única", "Diária", "Semanal", "Quinzenal", "Mensal", "Sob demanda"
        ], key="f_frequencia")
 
    st.markdown("")
    st.markdown("""
    <div class="info-box">📎 <strong>Anexos:</strong> Caso tenha algum anexo ou referência que contribua a execução da sua solicitação, por favor, enviar por WhatsApp para (84) 996241616 (Número de Caroline). </em>.</div>
    <div class="warning-box">🕐 <strong>Prazo de entrega:</strong> a ser definido após análise da demanda pela equipe. O retorno com o prazo será enviado por WhatsApp. </div>
    """, unsafe_allow_html=True)
 
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        enviar = st.button("📤  Enviar solicitação", type="primary", use_container_width=True)
 
    if enviar:
        erros = []
        if not nome.strip(): erros.append("Nome completo é obrigatório.")
        elif len(nome.strip().split()) < 2: erros.append("Informe nome e sobrenome.")
        if not setor: erros.append("Selecione o setor/departamento.")
        if not objetivo.strip(): erros.append("Descreva o objetivo.")
        if not contexto.strip(): erros.append("Descreva o contexto.")
        if not resultado: erros.append("Selecione o resultado esperado.")
        if not frequencia: erros.append("Selecione a frequência.")
 
        if erros:
            for e in erros: st.error(f"⚠️ {e}")
        else:
            demandas = carregar_demandas()
            agora = agora_brasil()
            nova = {
                "id": int(agora.timestamp() * 1000),
                "data": agora.strftime("%d/%m/%Y %H:%M"),
                "nome": nome.strip(), "setor": setor, "tipo": tipo,
                "objetivo": objetivo.strip(), "contexto": contexto.strip(),
                "resultado": resultado, "frequencia": frequencia,
                "status": "Aberta", "analista": "", "prazo": "",
                "classificacao_lider": "Aberto", "comentario_lider": "",
            }
            demandas.insert(0, nova)
            salvar_demandas(demandas)
            st.session_state.form_enviado = True
            st.rerun()
 
# ══════════════════════════════════════════════════════════════════════════════
# ABA 2 — PAINEL DO LÍDER
# ══════════════════════════════════════════════════════════════════════════════
with aba_lider:
 
    # Login do líder
    if st.session_state.logado_como != "lider":
        st.markdown("""
        <div class="lock-card">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">👑</div>
            <h2>Painel do Analista Líder</h2>
            <p>Acesso restrito. Digite a senha para continuar.</p>
        </div>
        """, unsafe_allow_html=True)
        col_lk, _ = st.columns([1, 2])
        with col_lk:
            senha_lider = st.text_input("Senha do líder", type="password", key="inp_lider")
            if st.button("🔐 Entrar", type="primary", use_container_width=True, key="btn_lider"):
                if senha_lider == SENHA_LIDER:
                    st.session_state.logado_como = "lider"
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
    else:
        # ── LÍDER LOGADO ────────────────────────────────────────────────────
        demandas = carregar_demandas()
        analistas = list(SENHA_ANALISTA.keys())
 
        st.markdown("### 👑 Painel do Analista Líder")
 
        # Métricas gerais
        total    = len(demandas)
        abertas  = sum(1 for d in demandas if d["status"] == "Aberta")
        execucao = sum(1 for d in demandas if d["status"] == "Em execução")
        concl    = sum(1 for d in demandas if d["status"] == "Concluída")
 
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="num">{total}</div><div class="lbl">Total de demandas</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#854F0B">{abertas}</div><div class="lbl">🟡 Abertas</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#185FA5">{execucao}</div><div class="lbl">🔵 Em execução</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#3B6D11">{concl}</div><div class="lbl">🟢 Concluídas</div></div>', unsafe_allow_html=True)
 
        st.markdown("---")
        st.markdown("#### 📋 Gerenciar demandas")
 
        filtro_status   = st.selectbox("Filtrar por status (Aplica-se apenas às Atribuídas)", ["Todas", "Aberta", "Em execução", "Concluída"], key="filt_lider")
        filtro_analista = st.selectbox("Filtrar por analista (Aplica-se apenas às Atribuídas)", ["Todos"] + analistas, key="filt_an_lider")
 
        # Separação das listas baseada na atribuição do analista
        # Separação das listas com a nova regra de arquivamento
        demandas_arquivadas = [d for d in demandas if d.get("classificacao_lider") in ["Duplicado", "Improcedente"]]
        demandas_novas = [d for d in demandas if not d.get("analista") and d.get("classificacao_lider") == "Aberto"]
        demandas_atribuidas = [d for d in demandas if d.get("analista") and d.get("classificacao_lider") == "Aberto"]
        
        # Aplica os filtros apenas na lista de atribuídas
        if filtro_status != "Todas":
            demandas_atribuidas = [d for d in demandas_atribuidas if d["status"] == filtro_status]
        if filtro_analista != "Todos":
            demandas_atribuidas = [d for d in demandas_atribuidas if d.get("analista") == filtro_analista]
 
        # ── SEÇÃO 1: DEMANDAS NOVAS ──────────────────────────────────────────
        st.markdown(f"### 📥 Novas Demandas (Aguardando Atribuição) — **{len(demandas_novas)}**")
 
        if not demandas_novas:
            st.info("Não há nenhuma nova demanda aguardando atribuição no momento.")
        else:
            for d in demandas_novas:
                esta_aberto = st.session_state.expander_aberto_lider == d["id"]
                icone_status = '🟡 Aguardando Analista'
                titulo = f"🆕 📄 {d['nome']} · {d['tipo']} · {d['data']} · {icone_status}"
 
                with st.expander(titulo, expanded=esta_aberto):
                    if not esta_aberto:
                        st.session_state.expander_aberto_lider = d["id"]
 
                    col_info, col_acao = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**Solicitante:** {d['nome']}")
                        st.markdown(f"**Setor:** {d['setor']} · **Tipo:** {d['tipo']}")
                        st.markdown(f"**Resultado:** {d['resultado']} · **Frequência:** {d['frequencia']}")
                        st.markdown(f"**Enviado em:** {d['data']}")
                        st.markdown("**Objetivo:**")
                        st.info(d["objetivo"])
                        st.markdown("**Contexto:**")
                        st.info(d["contexto"])
 
                    with col_acao:
                        st.markdown("**⚙️ Atribuição do líder**")

                        # Classificação da demanda
                        opcoes_class = ["Aberto", "Duplicado", "Improcedente"]
                        idx_class = opcoes_class.index(d.get("classificacao_lider", "Aberto")) if d.get("classificacao_lider", "Aberto") in opcoes_class else 0
                        nova_classificacao = st.selectbox(
                            "📌 Classificação da demanda",
                            opcoes_class,
                            index=idx_class,
                            key=f"class_nova_{d['id']}",
                        )

                        # Comentário do líder
                        novo_comentario = st.text_area(
                            "💬 Comentário para o analista",
                            value=d.get("comentario_lider", ""),
                            placeholder="Ex: Verificar se já existe relatório similar. Prioridade alta. Use a base XYZ...",
                            height=90,
                            key=f"coment_nova_{d['id']}",
                        )

                        novo_analista = st.selectbox(
                            "Vincular analista responsável",
                            [""] + analistas,
                            key=f"an_nova_{d['id']}",
                        )
                        novo_prazo = st.date_input(
                            "Prazo de entrega",
                            value=None,
                            key=f"prazo_nova_{d['id']}",
                            format="DD/MM/YYYY",
                        )

                        if st.button("💾 Salvar atribuição", key=f"salvar_nova_{d['id']}", type="primary"):
                            # Se o líder decidiu arquivar (Duplicado ou Improcedente)
                            if nova_classificacao in ["Duplicado", "Improcedente"]:
                                todas = carregar_demandas()
                                for dem in todas:
                                    if dem["id"] == d["id"]:
                                        dem["classificacao_lider"] = nova_classificacao
                                        dem["comentario_lider"] = novo_comentario.strip()
                                        # Forçamos o status para Concluída/Arquivada para controle interno
                                        dem["status"] = "Concluída" 
                                        break
                                salvar_demandas(todas)
                                st.session_state.expander_aberto_lider = None
                                st.success(f"✅ Demanda arquivada como '{nova_classificacao}'!")
                                st.rerun()
                            
                            # Se continuou Aberto, mas não escolheu analista, aí sim dá erro
                            elif not novo_analista:
                                st.error("⚠️ Selecione um analista antes de salvar ou mude a classificação para arquivar.")
                            
                            # Se está tudo certo para mandar para um analista
                            else:
                                todas = carregar_demandas()
                                for dem in todas:
                                    if dem["id"] == d["id"]:
                                        dem["analista"] = novo_analista
                                        dem["prazo"]    = str(novo_prazo) if novo_prazo else ""
                                        dem["status"]   = "Aberta"
                                        dem["classificacao_lider"] = nova_classificacao
                                        dem["comentario_lider"] = novo_comentario.strip()
                                        break
                                salvar_demandas(todas)
                                st.session_state.expander_aberto_lider = None
                                st.success("✅ Demanda atribuída com sucesso!")
                                st.rerun()

        st.markdown("---")

        # ── SEÇÃO 2: DEMANDAS JÁ ATRIBUÍDAS ──────────────────────────────────
        st.markdown(f"### 🤝 Demandas Já Atribuídas — **{len(demandas_atribuidas)} exibida(s)**")
 
        if not demandas_atribuidas:
            st.info("Nenhuma demanda atribuída corresponde aos filtros selecionados.")
        else:
            for d in demandas_atribuidas:
                icone_status = '🟡 '+d['status'] if d['status']=='Aberta' else '🔵 '+d['status'] if d['status']=='Em execução' else '🟢 '+d['status']
                analista_atual = d.get("analista", "—")
                titulo = f"📋 📄 {d['nome']} · {d['tipo']} · Responsável: {analista_atual} · {icone_status}"
 
                with st.expander(titulo):
                    col_info, col_acao = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**Solicitante:** {d['nome']}")
                        st.markdown(f"**Setor:** {d['setor']} · **Tipo:** {d['tipo']}")
                        st.markdown(f"**Resultado:** {d['resultado']} · **Frequência:** {d['frequencia']}")
                        st.markdown(f"**Enviado em:** {d['data']}")
                        st.markdown("**Objetivo:**")
                        st.info(d["objetivo"])
                        st.markdown("**Contexto:**")
                        st.info(d["contexto"])
 
                    with col_acao:
                        prazo_fmt = ""
                        if d.get("prazo"):
                            try:
                                prazo_fmt = datetime.strptime(d["prazo"], "%Y-%m-%d").strftime("%d/%m/%Y")
                            except:
                                prazo_fmt = d["prazo"]

                        st.markdown(f"**Analista Responsável:** `{analista_atual}`")
                        st.markdown(f"**Prazo Pactuado:** {prazo_fmt if prazo_fmt else 'Não definido'}")
                        st.markdown(f"**Status Atual:** {icone_status}")

                        # Classificação e comentário editáveis mesmo nas atribuídas
                        opcoes_class2 = ["Aberto", "Duplicado", "Improcedente"]
                        idx_class2 = opcoes_class2.index(d.get("classificacao_lider", "Aberto")) if d.get("classificacao_lider", "Aberto") in opcoes_class2 else 0
                        nova_class2 = st.selectbox(
                            "📌 Classificação",
                            opcoes_class2,
                            index=idx_class2,
                            key=f"class_atr_{d['id']}",
                        )
                        novo_coment2 = st.text_area(
                            "💬 Comentário para o analista",
                            value=d.get("comentario_lider", ""),
                            placeholder="Observações, orientações ou contexto adicional...",
                            height=80,
                            key=f"coment_atr_{d['id']}",
                        )
                        if st.button("💾 Salvar comentário", key=f"salvar_coment_{d['id']}", type="primary"):
                            todas = carregar_demandas()
                            for dem in todas:
                                if dem["id"] == d["id"]:
                                    dem["classificacao_lider"] = nova_class2
                                    dem["comentario_lider"] = novo_coment2.strip()
                                    break
                            salvar_demandas(todas)
                            st.success("✅ Comentário salvo!")
                            st.rerun()
        st.markdown("---")

        # ── SEÇÃO 3: DEMANDAS ARQUIVADAS ─────────────────────────────────────
        st.markdown(f"### 📦 Demandas Arquivadas (Duplicadas / Improcedentes) — **{len(demandas_arquivadas)}**")

        if not demandas_arquivadas:
            st.info("Nenhuma demanda foi arquivada como duplicada ou improcedente.")
        else:
            for d in demandas_arquivadas:
                classe = d.get("classificacao_lider", "Duplicado")
                badge_cor = "badge-duplicado" if classe == "Duplicado" else "badge-improcedente"
                titulo = f"📁 {d['nome']} · {d['tipo']} · [ {classe.upper()} ]"

                with st.expander(titulo):
                    col_info, col_acao = st.columns([1, 1])
                    with col_info:
                        st.markdown(f"**Solicitante:** {d['nome']}")
                        st.markdown(f"**Setor:** {d['setor']} · **Tipo:** {d['tipo']}")
                        st.markdown(f"**Enviado em:** {d['data']}")
                        st.markdown("**Objetivo:**")
                        st.info(d["objetivo"])
                    
                    with col_acao:
                        st.markdown(f"**Motivo do arquivamento ({classe}):**")
                        if d.get("comentario_lider"):
                            st.warning(d["comentario_lider"])
                        else:
                            st.info("*Nenhum comentário inserido pelo líder.*")
                        
                        # Opção para desarquivar se o líder mudar de ideia
                        if st.button("🔄 Reabrir e voltar para novas", key=f"Desarquivar_{d['id']}"):
                            todas = carregar_demandas()
                            for dem in todas:
                                if dem["id"] == d["id"]:
                                    dem["classificacao_lider"] = "Aberto"
                                    dem["analista"] = ""
                                    dem["status"] = "Aberta"
                                    break
                            salvar_demandas(todas)
                            st.success("Demandas reaberta com sucesso!")
                            st.rerun()
        # ── Exportar ─────────────────────────────────────────────────────────
        if demandas:
            st.markdown("---")
            df = pd.DataFrame(demandas)
            cols = ["data","nome","setor","tipo","objetivo","contexto","resultado","frequencia","status","analista","prazo","classificacao_lider","comentario_lider"]
            df = df[[c for c in cols if c in df.columns]]
            df.columns = ["Data","Nome","Setor","Tipo","Objetivo","Contexto","Resultado","Frequência","Status","Analista","Prazo","Classificação Líder","Comentário Líder"]
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ Exportar CSV", data=csv,
                file_name=f"demandas_{agora_brasil().strftime('%Y%m%d')}.csv", mime="text/csv")
 
        # ── Resumo por analista ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📊 Resumo por analista")
 
        for analista in analistas:
            dem_analista = [d for d in demandas if d.get("analista") == analista]
            ab  = sum(1 for d in dem_analista if d["status"] == "Aberta")
            ex  = sum(1 for d in dem_analista if d["status"] == "Em execução")
            co  = sum(1 for d in dem_analista if d["status"] == "Concluída")
            tot = len(dem_analista)
 
            st.markdown(f"""
            <div class="analista-card">
                <h4>👤 {analista} &nbsp;·&nbsp; <span style="color:#6b7a8d;font-weight:400;font-size:0.85rem">{tot} demanda(s) atribuída(s)</span></h4>
                <span class="badge-aberta">🟡 Abertas: {ab}</span>&nbsp;
                <span class="badge-execucao">🔵 Em execução: {ex}</span>&nbsp;
                <span class="badge-concluida">🟢 Concluídas: {co}</span>
            </div>
            """, unsafe_allow_html=True)
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ABA 3 — PAINEL DO ANALISTA
# ══════════════════════════════════════════════════════════════════════════════
with aba_analista:
 
    analistas = list(SENHA_ANALISTA.keys())
 
    # Se não está logado como analista
    logado_analista = st.session_state.logado_como if st.session_state.logado_como in analistas else None
 
    if not logado_analista:
        st.markdown("""
        <div class="lock-card">
            <div style="font-size:2.5rem;margin-bottom:0.5rem">👤</div>
            <h2>Painel do Analista</h2>
            <p>Selecione seu nome e digite sua senha para acessar suas demandas.</p>
        </div>
        """, unsafe_allow_html=True)
        col_ak, _ = st.columns([1, 2])
        with col_ak:
            sel_analista = st.selectbox("Selecione seu nome", [""] + analistas, key="sel_analista_login")
            senha_an = st.text_input("Sua senha", type="password", key="inp_analista")
            if st.button("🔐 Entrar", type="primary", use_container_width=True, key="btn_analista"):
                if sel_analista and senha_an == SENHA_ANALISTA.get(sel_analista, ""):
                    st.session_state.logado_como = sel_analista
                    st.rerun()
                else:
                    st.error("Nome ou senha incorretos.")
    else:
        # ── ANALISTA LOGADO ──────────────────────────────────────────────────
        demandas = carregar_demandas()
        minhas   = [d for d in demandas if d.get("analista") == logado_analista]
 
        st.markdown(f"### 👤 Olá, {logado_analista}!")
        st.markdown(f"Você tem **{len(minhas)} demanda(s)** atribuída(s).")
 
        # Mini métricas
        ab = sum(1 for d in minhas if d["status"] == "Aberta")
        ex = sum(1 for d in minhas if d["status"] == "Em execução")
        co = sum(1 for d in minhas if d["status"] == "Concluída")
 
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#854F0B">{ab}</div><div class="lbl">🟡 Abertas</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#185FA5">{ex}</div><div class="lbl">🔵 Em execução</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="num" style="color:#3B6D11">{co}</div><div class="lbl">🟢 Concluídas</div></div>', unsafe_allow_html=True)
 
        st.markdown("---")
 
        filtro_an = st.selectbox("Filtrar por status", ["Todas", "Aberta", "Em execução", "Concluída"], key="filt_analista")
        lista_an  = minhas if filtro_an == "Todas" else [d for d in minhas if d["status"] == filtro_an]
 
        if not lista_an:
            st.info("Nenhuma demanda encontrada." if minhas else "Você ainda não tem demandas atribuídas. Aguarde o líder atribuir uma demanda para você.")
 
        for d in lista_an:
            prazo_fmt = ""
            if d.get("prazo"):
                try:
                    prazo_fmt = datetime.strptime(d["prazo"], "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    prazo_fmt = d["prazo"]
 
            with st.expander(f"📄  {d['nome']}  ·  {d['tipo']}  ·  {d['status']}" + (f"  ·  ⏰ {prazo_fmt}" if prazo_fmt else "")):
                col_det, col_st = st.columns([2, 1])
 
                with col_det:
                    st.markdown(f"**Solicitante:** {d['nome']}")
                    st.markdown(f"**Setor:** {d['setor']}  ·  **Tipo:** {d['tipo']}")
                    st.markdown(f"**Resultado esperado:** {d['resultado']}  ·  **Frequência:** {d['frequencia']}")
                    if prazo_fmt:
                        st.markdown(f"**⏰ Prazo:** {prazo_fmt}")
                    st.markdown(f"**Enviado em:** {d['data']}")
                    st.markdown("**Objetivo:**")
                    st.info(d["objetivo"])
                    st.markdown("**Contexto:**")
                    st.info(d["contexto"])

                    # Comentário do líder visível para o analista
                    if d.get("comentario_lider"):
                        st.markdown("**💬 Orientação do Líder:**")
                        st.warning(d["comentario_lider"])
                    classificacao = d.get("classificacao_lider", "Aberto")
                    if classificacao in ["Duplicado", "Improcedente"]:
                        st.error(f"⚠️ Esta demanda foi classificada como **{classificacao}** pelo líder.")
 
                with col_st:
                    st.markdown("**Atualizar status**")
                    novo_status_an = st.selectbox(
                        "Status da demanda",
                        ["Aberta", "Em execução", "Concluída"],
                        index=["Aberta", "Em execução", "Concluída"].index(d["status"]),
                        key=f"an_st_{d['id']}",
                    )
                    if st.button("💾 Atualizar status", key=f"an_salvar_{d['id']}", type="primary"):
                        todas = carregar_demandas()
                        for dem in todas:
                            if dem["id"] == d["id"]:
                                dem["status"] = novo_status_an
                                break
                        salvar_demandas(todas)
                        st.success("✅ Status atualizado!")
                        st.rerun()
