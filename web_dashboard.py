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
from folium.plugins import Draw, MarkerCluster
import re

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E CSS
# =====================================================================
st.set_page_config(page_title="🛡️ Monitoramento", layout="wide")

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
    </style>
""", unsafe_allow_html=True)

def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

if "logado" not in st.session_state: st.session_state.logado = False
if "user_nivel" not in st.session_state: st.session_state.user_nivel = None
if "user_nome" not in st.session_state: st.session_state.user_nome = None

conn = st.connection("gsheets", type=GSheetsConnection)

def render_kpi(titulo, valor, cor):
    s_div = "background-color:#1E2130; padding:25px; border-radius:12px; "
    s_div += f"border-top:5px solid {cor}; text-align:center;"
    html = f"<div style='{s_div}'><h3 style='color:#b0b4c4;'>{titulo}</h3>"
    html += f"<h1 style='color:white; font-size:48px;'>{valor}</h1></div>"
    st.markdown(html, unsafe_allow_html=True)

def render_card(titulo, valor, cor):
    s_div = "background-color:#1E2130; padding:20px; border-radius:10px; "
    s_div += f"border-top:5px solid {cor}; text-align:center; height:100%;"
    html = f"<div style='{s_div}'><h4 style='color:#b0b4c4;'>{titulo}</h4>"
    html += f"<h2 style='color:white; font-size:54px;'>{valor}</h2></div>"
    st.markdown(html, unsafe_allow_html=True)

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
        db_id = st.secrets["notion"]["database_id"]
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        headers = {
            "Authorization": f"Bearer {token}", 
            "Notion-Version": "2022-06-28", 
            "Content-Type": "application/json"
        }
        res = requests.post(url, headers=headers)
        if res.status_code != 200: return pd.DataFrame()
        bruto = res.json().get("results", [])
        linhas = []
        for item in bruto:
            props = item.get("properties", {})
            ln = {}
            for col, dados in props.items():
                t = dados.get("type")
                if t == "title":
                    v = dados.get("title", [])
                    ln[col] = v[0].get("plain_text") if v else ""
                elif t == "rich_text":
                    v = dados.get("rich_text", [])
                    ln[col] = "".join([x.get("plain_text", "") for x in v])
                elif t == "select":
                    v = dados.get("select")
                    ln[col] = v.get("name") if v else ""
                elif t == "files":
                    v = dados.get("files", [])
                    if v:
                        f = v[0]
                        ln[col] = f.get("file", {}).get("url") or f.get("name", "")
                    else: ln[col] = ""
                else: ln[col] = str(dados.get(t, ""))
            linhas.append(ln)
        return pd.DataFrame(linhas)
    except: return pd.DataFrame()

def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO")
    df = carregar_dados()
    c_lat, c_lon = None, None
    for c in df.columns:
        if "LAT" in c.upper(): c_lat = c
        if "LON" in c.upper(): c_lon = c
    if c_lat and c_lon:
        df_mapa = df.copy()
        df_mapa[c_lat] = pd.to_numeric(df[c_lat].astype(str).str.replace(',', '.'), errors='coerce')
        df_mapa[c_lon] = pd.to_numeric(df[c_lon].astype(str).str.replace(',', '.'), errors='coerce')
        df_mapa = df_mapa.dropna(subset=[c_lat, c_lon])
        m = folium.Map(location=[-22.9, -43.2], zoom_start=11)
        mc = MarkerCluster().add_to(m)
        for _, row in df_mapa.iterrows():
            pop = f"<b>{row.get('DATA', 'S/D')}</b><br>{row.get('LOCAL', 'S/D')}"
            folium.Marker([row[c_lat], row[c_lon]], popup=pop).add_to(mc)
        st_folium(m, width=1200, height=600)
    else: st.error("Latitude/Longitude não encontradas.")

def tela_acesso():
    st.markdown("<h1 style='text-align: center;'>🛡️ ACESSO</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Entrar", "📝 Cadastro"])
    with tab1:
        mat = st.text_input("Matrícula")
        sen = st.text_input("Senha", type="password")
        if st.button("Acessar"):
            try:
                url = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/gviz/tq?tqx=out:csv&sheet=USUARIOS"
                df_u = pd.read_csv(url)
                df_u.columns = [str(c).strip().upper() for c in df_u.columns]
                match = df_u[(df_u['MATRICULA'].astype(str) == str(mat).strip()) & (df_u['SENHA'] == gerar_hash(sen))]
                if not match.empty and str(match.iloc[0]['STATUS']).upper() == 'APROVADO':
                    st.session_state.logado = True
                    st.session_state.user_nome = match.iloc[0]['NOME']
                    st.session_state.user_nivel = match.iloc[0]['NIVEL']
                    st.rerun()
                else: st.error("Acesso negado ou pendente.")
            except: st.error("Erro na base.")

def gerar_dashboard(df_f):
    c_vit = None
    for c in df_f.columns:
        if "VITIMAS" in str(c).upper() or "VÍTIMAS" in str(c).upper(): c_vit = c
    tot_p = len(df_f)
    tot_v = 0
    if c_vit:
        tot_v = pd.to_numeric(df_f[c_vit].astype(str).str.replace(',','.'), errors='coerce').fillna(0).sum()
    col1, col2 = st.columns(2)
    with col1: render_kpi("📊 PROCEDIMENTOS", tot_p, "#ff4b4b")
    with col2: render_kpi("👤 VÍTIMAS", int(tot_v), "#F1C40F")

if not st.session_state.logado:
    tela_acesso()
else:
    st.sidebar.markdown(f"### Olá, {st.session_state.user_nome}")
    menu = st.sidebar.radio("NAVEGAÇÃO", ["1. VISÃO GERAL", "2. ORCRIM", "3. MAPA"])
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    df = carregar_dados()

    if menu == "2. ORCRIM":
        st.header("📓 ÁREA 1 - INTELIGÊNCIA")
        df_n = carregar_dados_notion()
        if not df_n.empty:
            if "alvo_b" not in st.session_state: st.session_state.alvo_b = ""
            
            c_b, c_cl, _ = st.columns([3, 1, 6])
            alvo = c_b.selectbox("Alvo:", [""] + df_n["Nome"].tolist(), key="alvo_b")
            if c_cl.button("🧹 Limpar", key="btn_limp"):
                st.session_state.alvo_b = ""
                st.rerun()

            st.write("---")
            tab_d, tab_o = st.tabs(["📇 DOSSIÊ", "🕸️ ORGANOGRAMA"])
            
            with tab_d:
                if alvo:
                    d = df_n[df_n["Nome"] == alvo].iloc[0]
                    c_f, c_i = st.columns([1, 2])
                    if str(d.get("Foto","")).startswith("http"): c_f.image(d["Foto"])
                    c_i.markdown(f"## {alvo} ({d.get('Vulgo','N/I')})")
                    st.warning(d.get("Informe", "Sem informe."))
                else: st.info("Selecione um alvo.")

            with tab_o:
                if alvo:
                    d = df_n[df_n["Nome"] == alvo].iloc[0]
                    local = str(d.get("Atuação", "")).strip()
                    if local and local.upper() not in ["NAN", ""]:
                        st.markdown(f"### Território: **{local}**")
                        df_a = df_n[df_n["Atuação"] == local]
                        
                        # Construção do Organograma via Graphviz (Nativo)
                        dot = "digraph G {\n"
                        dot += '  graph [rankdir=TB, bgcolor="#0E1117"];\n'
                        dot += '  node [style=filled, fontname="Arial", fontsize=10];\n'
                        
                        def get_rank(f):
                            f = str(f).upper()
                            if "DONO" in f: return 0
                            if "FRENTE" in f: return 1
                            if "2º" in f or "SEGUNDO" in f: return 2
                            if "GERENTE" in f: return 3
                            if "LÍDER" in f or "LIDER" in f: return 4
                            return 5

                        orgs = df_a["Organização"].unique()
                        for org in orgs:
                            o_id = hashlib.md5(str(org).encode()).hexdigest()[:6]
                            dot += f'  "{o_id}" [label="🏢 {org}", fillcolor="#1E2130", fontcolor="white", shape=box];\n'
                            
                            df_o = df_a[df_area["Organização"] == org].copy()
                            df_o['r'] = df_o['Função'].apply(get_rank)
                            df_o = df_o.sort_values('r')

                            prev = o_id
                            for _, p in df_o.iterrows():
                                p_id = hashlib.md5(str(p['Nome']).encode()).hexdigest()[:6]
                                cor = "#4a4f63"
                                if p['Nome'] == alvo: cor = "#E74C3C"
                                label = f"{p['Nome']}\\n({p['Função']})"
                                dot += f'  "{p_id}" [label="{label}", fillcolor="{cor}", fontcolor="white"];\n'
                                dot += f'  "{prev}" -> "{p_id}" [color="#555555"];\n'
                        
                        dot += "}"
                        st.graphviz_chart(dot)
                    else: st.warning("Alvo sem território definido.")
                else: st.info("Selecione um alvo.")
