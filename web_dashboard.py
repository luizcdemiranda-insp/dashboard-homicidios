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
            linha = {nome: str(d.get(d.get("type"), "")) for nome, d in props.items()}
            linhas.append(linha)
        return pd.DataFrame(linhas)
    except: return pd.DataFrame()

# =====================================================================
# 3. GEOPROCESSAMENTO DIRETO (PONTOS GPS)
# =====================================================================
def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO: LOCALIZAÇÃO DE FATOS")
    
    # 1. Obter dados e processar coordenadas das colunas M (Lat) e N (Lon)
    df = carregar_dados()
    
    # Identifica colunas de Latitude e Longitude (Geralmente chamadas de LATITUDE e LONGITUDE no CSV)
    # Se os nomes forem diferentes, ajustamos aqui.
    col_lat = next((c for c in df.columns if "LATITUDE" in c or "LAT" in c), None)
    col_lon = next((c for c in df.columns if "LONGITUDE" in c or "LON" in c), None)

    if col_lat and col_lon:
        # Limpeza Tática: Converte para número, força erro (#N/A) a virar nulo e remove nulos
        df[col_lat] = pd.to_numeric(df[col_lat], errors='coerce')
        df[col_lon] = pd.to_numeric(df[col_lon], errors='coerce')
        df_mapa = df.dropna(subset=[col_lat, col_lon])
        
        st.success(f"✅ {len(df_mapa)} pontos localizados via coordenadas GPS.")

        # 2. Configuração do Mapa
        m = folium.Map(location=[-22.9068, -43.1729], zoom_start=11, control_scale=True)

        # Camadas: Ruas e Satélite Híbrido (Google)
        folium.TileLayer('openstreetmap', name='Mapa de Ruas').add_to(m)
        folium.TileLayer(
            tiles='http://mt0.google.com/vt/lyrs=y&hl=pt-BR&x={x}&y={y}&z={z}',
            attr='Google',
            name='Satélite com Ruas (Híbrido)'
        ).add_to(m)

        # Ferramenta de Desenho Visual
        Draw(export=False, position='topleft').add_to(m)

        # 3. Plotagem dos Círculos
        for _, row in df_mapa.iterrows():
            popup_texto = f"<b>Data:</b> {row.get('DATA', 'S/D')}<br><b>Local:</b> {row.get('LOGRADOURO', 'S/D')}"
            folium.CircleMarker(
                location=[row[col_lat], row[col_lon]],
                radius=6,
                popup=folium.Popup(popup_texto, max_width=300),
                color='#8B0000',
                fill=True,
                fill_color='#FF0000',
                fill_opacity=0.6
            ).add_to(m)

        folium.LayerControl().add_to(m)
        st_folium(m, width=1200, height=600, returned_objects=[])
    else:
        st.error("⚠️ Colunas de Latitude/Longitude não encontradas na planilha.")

# =====================================================================
# 4. INTERFACE DE ACESSO E NAVEGAÇÃO
# =====================================================================
def tela_acesso():
    # ... (Sua função tela_acesso original se mantém aqui)
    pass

# Lógica de Navegação principal
if not st.session_state.logado:
    # Se você quiser simplificar para testes, pode setar logado=True aqui temporariamente
    # st.session_state.logado = True 
    # st.session_state.user_nome = "Comandante"
    # st.session_state.user_nivel = "Master"
    tela_acesso()
else:
    st.sidebar.markdown(f"### Olá, {st.session_state.user_nome}")
    lista_menu = ["1. VISÃO GERAL", "2. ORCRIM", "3. MAPA", "4. MODO ANALÍTICO", "5. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master": lista_menu.append("⚙️ CONFIGURAÇÕES")
    menu = st.sidebar.radio("NAVEGAÇÃO", lista_menu)

    # Submenu ORCRIM
    sub_menu_orcrim = None
    if menu == "2. ORCRIM":
        st.sidebar.markdown("---")
        sub_menu_orcrim = st.sidebar.radio("📂 ÁREA:", ["ÁREA 1", "ÁREA 2", "ÁREA 3", "ÁREA 4"])

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # Cabeçalho
    st.markdown("<h1 style='text-align: center;'>🛡️ MONITORAMENTO DE HOMICÍDIOS</h1>", unsafe_allow_html=True)
    st.write("---")

    if menu == "1. VISÃO GERAL":
        df = carregar_dados()
        # ... (Sua lógica de dashboard aqui)
    elif menu == "2. ORCRIM":
        if sub_menu_orcrim == "ÁREA 1":
            df_notion = carregar_dados_notion()
            st.dataframe(df_notion, use_container_width=True)
    elif menu == "3. MAPA":
        pagina_mapa()
    elif menu == "4. MODO ANALÍTICO":
        st.dataframe(carregar_dados())
    elif menu == "5. ASSISTENTE IA":
        st.write("Módulo de IA em desenvolvimento.")
