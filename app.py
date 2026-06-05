import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Solicitações — Análise de Dados",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Senhas — lidas dos secrets ──────────────────────────────────────────────
SENHA_LIDER    = st.secrets["senhas"]["lider"]
SENHA_ANALISTA = {
    "Artur":    st.secrets["senhas"]["artur"],
    "Gabriel":  st.secrets["senhas"]["gabriel"],
    "Edson":    st.secrets["senhas"]["edson"],
}

PLANILHA_ID = st.secrets["sheets"]["id"]

# ── Conexão Tratada e Blindada Contra Erros de Chave Privada ─────────────────
def conectar_planilha():
    chave_bruta = st.secrets["gcp_service_account"]["private_key"]
    
    if "\\n" in chave_bruta:
        chave_corrigida = chave_bruta.replace("\\n", "\n")
    else:
        linhas_chave = [linha.strip() for linha in chave_bruta.split("\n") if linha.strip()]
        chave_corrigida = "\n".join(linhas_chave)

    info = {
        "type":                        st.secrets["gcp_service_account"]["type"],
        "project_id":                  st.secrets["gcp_service_account"]["project_id"],
        "private_key_id":              st.secrets["gcp_service_account"]["private_key_id"],
        "private_key":                 chave_corrigida,
        "client_email":                st.secrets["gcp_service_account"]["client_email"],
        "client_id":                   st.secrets["gcp_service_account"]["client_id"],
        "auth_uri":                    st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri":                   st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url":        st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain":             st.secrets["gcp_service_account"]["universe_domain"]
    }
    
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds = Credentials.from_service_account_info(info, scopes=escopos)
    client = gspread.authorize(creds)
    return client.open_by_key(PLANILHA_ID).worksheet("Demandas")

# ── Funções de manipulação de dados de forma segura ──────────────────────────
def carregar_demandas():
    try:
        sheet = conectar_planilha()
        linhas = sheet.get_all_values()
        
        if not linhas or len(linhas) <= 1:
            return []
            
        cabecalho_esperado = [
            "id", "nome", "setor", "tipo", "objetivo", "contexto", 
            "resultado", "frequencia", "prazo", "data", "status", "analista", "prioridade"
        ]
        
        demandas = []
        for l in linhas[1:]:
            if not any(l):
                continue
            if len(l) < len(cabecalho_esperado):
                l = l + [""] * (len(cabecalho_esperado) - len(l))
            else:
                l = l[:len(cabecalho_esperado)]
                
            dados = dict(zip(cabecalho_esperado, l))
            try:
                dados["id"] = int(dados["id"]) if dados["id"] else 0
            except:
                dados["id"] = 0
            demandas.append(dados)
        return demandas
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return []

def salvar_demandas(lista_demandas):
    try:
        sheet = conectar_planilha()
        cabecalho_esperado = [
            "id", "nome", "setor", "tipo", "objetivo", "contexto", 
            "resultado", "frequencia", "prazo", "data", "status", "analista", "prioridade"
        ]
        
        linhas_para_salvar = [cabecalho_esperado]
        for d in lista_demandas:
            linha = [str(d.get(col, "")) for col in cabecalho_esperado]
            linhas_para_salvar.append(linha)
            
        sheet.clear()
        sheet.update("A1", linhas_para_salvar)
    except Exception as e:
        st.error(f"Erro ao salvar dados na planilha: {e}")

# ── INTERFACE ORIGINAL RESTAURADA ────────────────────────────────────────────
st.title("📊 Formulário de Demandas — Análise de Dados")
st.markdown("---")

aba_solicitacao, aba_paineis = st.tabs(["📩 Nova Solicitação", "🔒 Painéis Restritos"])

# ABA 1: FORMULÁRIO COM SEU LAYOUT ORIGINAL
with aba_solicitacao:
    st.markdown("### 📝 Preencha os dados abaixo para abrir um chamado")
    
    with st.form("form_demanda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Seu Nome *", placeholder="Ex: João Silva")
            setor = st.selectbox("Seu Setor *", ["Comercial", "Financeiro", "Operações", "RH", "Diretoria", "Outro"])
            tipo = st.selectbox("Tipo de Demanda *", ["Novo Relatório/Dashboard", "Ajuste em Dashboard Existente", "Extração de Dados (Ad-hoc)", "Automação", "Outro"])
            frequencia = st.selectbox("Frequência de uso *", ["Uma única vez (Ad-hoc)", "Diário", "Semanal", "Mensal", "Contínuo"])
            prazo = st.date_input("Prazo desejado para entrega *", min_value=datetime.today())
            
        with col2:
            objetivo = st.text_area("Qual o objetivo principal dessa análise? * (O que você quer descobrir?)", height=68, placeholder="Explique qual decisão de negócio será tomada com esses dados.")
            contexto = st.text_area("Contexto da solicitação * (Explique o cenário ou problema atual)", height=68, placeholder="Quais bases de dados envolvem isso? Como é feito hoje?")
            resultado = st.text_area("Qual o resultado prático esperado após a entrega? *", height=68, placeholder="Ex: Reduzir tempo de análise manual, aumentar conversão, etc.")
            
        st.markdown("<small>* Campos obrigatórios</small>", unsafe_allow_html=True)
        enviar = st.form_submit_button("🚀 Enviar Solicitação para a Engenharia de Dados", type="primary")
        
        if enviar:
            if nome and objetivo and contexto and resultado:
                demandas_atuais = carregar_demandas()
                novo_id = max([d["id"] for d in demandas_atuais], default=0) + 1
                
                nova_demanda = {
                    "id": novo_id,
                    "nome": nome,
                    "setor": setor,
                    "tipo": tipo,
                    "objetivo": objetivo,
                    "contexto": contexto,
                    "resultado": resultado,
                    "frequencia": frequencia,
                    "prazo": prazo.strftime("%Y-%m-%d"),
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "Aberta",
                    "analista": "Não designado",
                    "prioridade": "Não definida"
                }
                
                demandas_atuais.append(nova_demanda)
                salvar_demandas(demandas_atuais)
                st.success(f"🎉 Solicitação enviada com sucesso! ID da Demanda: {novo_id}")
            else:
                st.warning("⚠️ Por favor, preencha todos os campos obrigatórios.")

# ABA 2: PAINÉIS RESTRITOS (LÍDER E ANALISTAS)
with aba_paineis:
    perfil = st.radio("Selecione seu perfil:", ["Analista", "Líder do Setor"], horizontal=True)
    demandas = carregar_demandas()
    
    if perfil == "Analista":
        analista_sel = st.selectbox("Selecione seu nome:", list(SENHA_ANALISTA.keys()))
        senha_an = st.text_input("Senha do Analista:", type="password", key="senha_analista")
        
        if senha_an == SENHA_ANALISTA[analista_sel]:
            st.success(f"Olá, {analista_sel}! Veja suas demandas abaixo:")
            filtradas = [d for d in demandas if d.get("analista") == analista_sel]
            
            if not filtradas:
                st.info("Você não tem demandas atribuídas no momento.")
            else:
                for d in filtradas:
                    with st.container(border=True):
                        col_txt, col_st = st.columns([3, 1])
                        with col_txt:
                            st.markdown(f"### Demanda #{d['id']} — {d['tipo']}")
                            st.markdown(f"**Solicitante:** {d['nome']} ({d['setor']})")
                            st.markdown(f"**Status:** `{d['status']}` | **Prioridade:** `{d['prioridade']}`")
                            st.markdown(f"**Objetivo:**")
                            st.info(d["objetivo"])
                        with col_st:
                            novo_status = st.selectbox("Atualizar Status:", ["Aberta", "Em execução", "Concluída"], index=["Aberta", "Em execução", "Concluída"].index(d["status"]) if d["status"] in ["Aberta", "Em execução", "Concluída"] else 0, key=f"status_{d['id']}")
                            if st.button("Salvar", key=f"btn_an_{d['id']}"):
                                for dem in demandas:
                                    if dem["id"] == d["id"]:
                                        dem["status"] = novo_status
                                salvar_demandas(demandas)
                                st.success("Atualizado!")
                                st.rerun()
                                
    elif perfil == "Líder do Setor":
        senha_lid = st.text_input("Senha do Líder:", type="password", key="senha_lider")
        if senha_lid == SENHA_LIDER:
            st.success("Painel de Gestão Liberado!")
            
            if not demandas:
                st.info("Nenhuma demanda registrada no sistema.")
            else:
                for d in demandas:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"### #{d['id']} - {d['tipo']} (De: {d['nome']})")
                            st.markdown(f"**Objetivo:**")
                            st.info(d["objetivo"])
                            st.markdown(f"**Designado para:** `{d['analista']}` | **Prioridade:** `{d['prioridade']}` | **Status:** `{d['status']}`")
                        with c2:
                            novo_an = st.selectbox("Designar Analista:", ["Não designado"] + list(SENHA_ANALISTA.keys()), index=(["Não designado"] + list(SENHA_ANALISTA.keys())).index(d["analista"]) if d["analista"] in (["Não designado"] + list(SENHA_ANALISTA.keys())) else 0, key=f"lead_an_{d['id']}")
                            nova_prio = st.selectbox("Definir Prioridade:", ["Não definida", "Baixa", "Média", "Alta"], index=["Não definida", "Baixa", "Média", "Alta"].index(d["prioridade"]) if d["prioridade"] in ["Não definida", "Baixa", "Média", "Alta"] else 0, key=f"lead_prio_{d['id']}")
                            
                            if st.button("Atribuir", key=f"btn_lead_{d['id']}"):
                                for dem in demandas:
                                    if dem["id"] == d["id"]:
                                        dem["analista"] = novo_an
                                        dem["prioridade"] = nova_prio
                                salvar_demandas(demandas)
                                st.success("Atribuído!")
                                st.rerun()
