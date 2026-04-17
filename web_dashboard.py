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

# IDs das Planilhas
ID_PLANILHA_ACESSO = "1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw"
ID_PLANILHA_CRIMES = "1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc"

# --- CSS PERSONALIZADO ---
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
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;
    }
    @media (max-width: 768px) {
        div[data-testid="stMainBlockContainer"] div[role="radiogroup"] { flex-direction: column; gap: 5px; }
        h1 { font-size: 38px !important; }
        h2 { font-size: 42px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# Funções de Segurança
def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_nivel" not in st.session_state:
    st.session_state.user_nivel = None
if "user_nome" not in st.session_state:
    st.session_state.user_nome = None

conn = st.connection("gsheets", type=GSheetsConnection)

# =====================================================================
# 2. CARGA DE DADOS
# =====================================================================
@st.cache_data
def carregar_dados():
    url = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_CRIMES}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [str(col).strip().upper() for col in df.columns]
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    return df

# =====================================================================
# 2.5 CARGA DE DADOS DO NOTION
# =====================================================================
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
        
        if response.status_code != 200:
            st.error(f"⚠️ Erro de comunicação com o Notion: {response.text}")
            return pd.DataFrame()
            
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
                    if relacoes:
                        linha[nome_coluna] = f"🔗 {len(relacoes)} Vinculada(s)"
                    else:
                        linha[nome_coluna] = ""
                elif tipo == "rollup":
                    rollup = dados_coluna.get("rollup", {})
                    if rollup.get("type") == "array":
                        vals = rollup.get("array", [])
