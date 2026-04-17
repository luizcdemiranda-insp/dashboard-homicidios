import streamlit as st
import pandas as pd
import altair as alt
import hashlib
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E CSS
# =====================================================================
st.set_page_config(page_title="🛡️ Monitoramento de Homicídios", layout="wide")

ID_PLANILHA_ACESSO = "1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw"
ID_PLANILHA_CRIMES = "1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc"

st.markdown("""
    <style>
    div[role="radiogroup"] > label > div:first-child,
    div[data-testid="stCheckbox"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label,
    div[data-testid="stCheckbox"] > label {
        background-color: #1E2130; border: 1px solid #4a4f63; padding: 10px 15px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        width: 100%;
    }
    div[role="radiogroup"] > label:hover,
    div[data-testid="stCheckbox"] > label:hover { border-color: #ff4b4b; }
    div[role="radiogroup"] > label:has(input:checked),
    div[data-testid="stCheckbox"] > label:has(input:checked) {
        background-color: #ff4b4b; color: white; border-color: #ff4b4b;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        justify-content: flex-start; padding-left: 20px;
    }
    </style>
""", unsafe_allow_html=True)

def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

if "logado" not in st.session_state: st.session_state.logado = False
if "user_nivel" not in st.session_state: st.session_state.user_nivel = None
if "user_nome" not in st.session_state: st.session_state.user_nome = None

conn = st.connection("gsheets", type=GSheetsConnection)

# =====================================================================
# 2. CARGA DE DADOS (CRIMES E NOTION)
# =====================================================================
@st.cache_data
def carregar_dados():
    url = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_CRIMES}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [str(col).strip().upper() for col in df.columns]
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    return df

@st.cache_data(ttl=600)
def carregar_dados_notion():
    try:
        token = st.secrets["notion"]["token"]
        database_id = st.secrets["notion"]["database_id"]
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers)
        if response.status_code != 200: return pd.DataFrame()
        
        dados_brutos = response.json().get("results", [])
        linhas = []
        for item in dados_brutos:
            props = item.get("properties", {})
            linha = {}
            for nome_coluna, dados_coluna in props.items():
                tipo = dados_coluna.get("type")
                if tipo == "title":
                    vals = dados_coluna.get("title", [])
                    linha[nome_coluna] = vals[0].get("plain_text") if vals else ""
                elif tipo == "rich_text":
                    vals = dados_coluna.get("rich_text", [])
                    linha[nome_coluna] = "".join([v.get("plain_text", "") for v in vals])
                elif tipo == "select":
                    val = dados_coluna.get("select")
                    linha[nome_coluna] = val.get("name") if val else ""
                elif tipo == "multi_select":
                    vals = dados_coluna.get("multi_select", [])
                    linha[nome_coluna] = ", ".join([v.get("name") for v in vals])
                elif tipo == "number":
                    linha[nome_coluna] = dados_coluna.get("number")
                elif tipo == "date":
                    val = dados_coluna.get("date")
                    linha[nome_coluna] = val.get("start") if val else ""
                elif tipo == "checkbox":
                    linha[nome_coluna] = dados_coluna.get("checkbox")
                elif tipo == "relation":
                    relacoes = dados_coluna.get("relation", [])
                    linha[nome_coluna] = f"🔗 {len(relacoes)} Vinculada(s)" if relacoes else ""
                elif tipo == "rollup":
                    rollup = dados_coluna.get("rollup", {})
                    if rollup.get("type") == "array":
                        vals = rollup.get("array", [])
                        textos = []
                        for v in vals:
                            if v.get("type") == "title":
                                textos.append("".join([t.get("plain_text", "") for t in v.get("title", [])]))
                            elif v.get("type") == "rich_text":
                                textos.append("".join([t.get("plain_text", "") for t in v.get("rich_text", [])]))
                        linha[nome_coluna] = ", ".join(textos)
                    else:
                        linha[nome_coluna] = "Agregação"
                elif tipo == "files":
                    arquivos = dados_coluna.get("files", [])
                    if arquivos:
                        arq = arquivos[0]
                        if "file" in arq: linha[nome_coluna] = arq["file"].get("url", "")
                        elif "external" in arq: linha[nome_coluna] = arq["external"].get("url", "")
                        else: linha[nome_coluna] = arq.get("name", "")
                    else:
                        linha[nome_coluna] = ""
                else:
                    linha[nome_coluna] = str(dados_coluna.get(tipo, ""))
            linhas.append(linha)
        return pd.DataFrame(linhas)
    except Exception as e:
        st.error(f"Erro no sistema Notion: {e}")
        return pd.DataFrame()

# =====================================================================
# 3. INTERFACE DE ACESSO
# =====================================================================
def tela_acesso():
    col_esq, col_meio, col_dir = st.columns([1, 4, 1])
    with col_meio:
        st.markdown("<h1 style='text-align: center;'>🛡️ ACESSO AO SISTEMA</h1>", unsafe_allow_html=True)
        aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Solicitar Cadastro"])
        
        with aba_login:
            mat_login = st.text_input("Matrícula", key="login_mat_input")
            senha_login = st.text_input("Senha", type="password", key="login_pass_input")
            
            if st.button("Acessar Painel"):
                try:
                    url_users = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/gviz/tq?tqx=out:csv&sheet=USUARIOS"
                    df_users = pd.read_csv(url_users)
                    df_users.columns = [str(col).strip().upper() for col in df_users.columns]
                    df_users['MATRICULA'] = df_users['MATRICULA'].astype(str).str.strip()
                    mat_login_limpa = str(mat_login).strip()
                    senha_hash = gerar_hash(senha_login)
                    
                    user_match = df_users[(df_users['MATRICULA'] == mat_login_limpa) & (df_users['SENHA'] == senha_hash)]
                    if not user_match.empty:
                        status = str(user_match.iloc[0]['STATUS']).strip().upper()
                        if status == 'APROVADO':
                            st.session_state.logado = True
                            st.session_state.user_nivel = user_match.iloc[0]['NIVEL']
                            st.session_state.user_nome = user_match.iloc[0]['NOME']
                            st.rerun()
                        else:
                            st.warning(f"Acesso Pendente. Status atual: {status}")
                    else:
                        st.error("Matrícula ou Senha incorretos.")
                except Exception as e:
                    st.error("Erro na base de usuários. Verifique o acesso da planilha.")

        with aba_cadastro:
            st.markdown("### 📝 Solicitação de Acesso")
            n_cad = st.text_input("Nome Completo", key="cad_nome_input")
            m_cad = st.text_input("Matrícula", key="cad_mat_input")
            s_cad = st.text_input("Defina uma Senha", type="password", key="cad_pass_input")
            
            if st.button("Enviar Solicitação"):
                if n_cad and m_cad and s_cad:
                    try:
                        senha_hash = gerar_hash(s_cad)
                        email_remetente = st.secrets["email"]["remetente"]
                        email_senha = st.secrets["email"]["senha"]
                        email_destino = "luizcdemiranda.insp@gmail.com"

                        corpo = f"""NOVA SOLICITAÇÃO DE ACESSO - DASHBOARD
                        Nome: {n_cad}
                        Matrícula: {m_cad}
                        Senha Escolhida: {s_cad}
                        Hash SHA256: {senha_hash}"""

                        msg = MIMEMultipart()
                        msg['From'] = email_remetente
                        msg['To'] = email_destino
                        msg['Subject'] = f"🔔 Solicitação de Cadastro: {n_cad}"
                        msg.attach(MIMEText(corpo, 'plain'))

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(email_remetente, email_senha)
                        server.send_message(msg)
                        server.quit()
                        st.success("✅ Solicitação enviada!")
                    except Exception as e:
                        st.error(f"Erro ao processar solicitação: {e}")
                else:
                    st.warning("Preencha todos os campos.")

# =====================================================================
# 4. FUNÇÃO REUTILIZÁVEL DO DASHBOARD E RENDERIZADORES
# =====================================================================
def render_kpi(titulo, valor, cor):
    html = f"""
    <div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid {cor}; text-align: center;">
        <h3 style="color: #b0b4c4; font-size: 16px;">{titulo}</h3>
        <h1 style="color: white; font-size: 48px;">{valor}</h1>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_card(titulo, valor, cor):
    html = f"""
    <div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid {cor}; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;">
        <h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">{titulo}</h4>
        <h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{valor}</h2>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def gerar_dashboard(df_filtrado):
    # Dica: Se for colar, certifique-se de que cada uma destas 3 variáveis fique em uma única linha!
    COL_DIA = next((c for c in df_filtrado.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
    COL_CIRCUNSCRICAO = next((c for c in df_filtrado.columns if "CIRCUNSCRI" in str(c)), None)
    COL_VITIMAS = next((c for c in df_filtrado.columns if "VÍTIMAS" in str(c) or "VITIMAS" in str(c)), None)

    total_procedimentos = len(df_filtrado)
