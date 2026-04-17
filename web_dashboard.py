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
                        if "file" in arq:
                            linha[nome_coluna] = arq["file"].get("url", "")
                        elif "external" in arq:
                            linha[nome_coluna] = arq["external"].get("url", "")
                        else:
                            linha[nome_coluna] = arq.get("name", "")
                    else:
                        linha[nome_coluna] = ""
                else:
                    linha[nome_coluna] = str(dados_coluna.get(tipo, ""))
                    
            linhas.append(linha)
            
        return pd.DataFrame(linhas)
        
    except Exception as e:
        st.error(f"Erro no sistema de extração do Notion: {e}")
        return pd.DataFrame()

# =====================================================================
# 2.6 GEOPROCESSAMENTO E MAPA (NOVO MÉTODO)
# =====================================================================
def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO: LOCALIZAÇÃO DE FATOS")
    
    df = carregar_dados()
    
    col_lat = next((c for c in df.columns if "LAT" in c), None)
    col_lon = next((c for c in df.columns if "LON" in c), None)

    if col_lat and col_lon:
        df_lat_limpa = pd.to_numeric(df[col_lat].astype(str).str.replace(',', '.'), errors='coerce')
        df_lon_limpa = pd.to_numeric(df[col_lon].astype(str).str.replace(',', '.'), errors='coerce')
        
        df_mapa = df.copy()
        df_mapa[col_lat] = df_lat_limpa
        df_mapa[col_lon] = df_lon_limpa
        df_mapa = df_mapa.dropna(subset=[col_lat, col_lon])
        
        st.success(f"✅ {len(df_mapa)} pontos localizados via coordenadas da planilha.")

        m = folium.Map(location=[-22.9068, -43.1729], zoom_start=11, control_scale=True)

        folium.TileLayer('openstreetmap', name='Mapa de Ruas (OpenStreetMap)').add_to(m)
        folium.TileLayer(
            tiles='http://mt0.google.com/vt/lyrs=y&hl=pt-BR&x={x}&y={y}&z={z}',
            attr='Google',
            name='Satélite com Ruas (Google Hybrid)'
        ).add_to(m)

        Draw(
            export=False,
            position='topleft',
            draw_options={
                'polyline': True, 'rectangle': True, 'polygon': True,
                'circle': False, 'marker': True, 'circlemarker': False
            }
        ).add_to(m)

        for index, row in df_mapa.iterrows():
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
                    st.error("Erro na base de usuários. Verifique se a planilha está como 'Qualquer pessoa com o link'.")

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

                        corpo = f"""
                        NOVA SOLICITAÇÃO DE ACESSO - DASHBOARD
                        
                        Nome: {n_cad}
                        Matrícula: {m_cad}
                        Senha Escolhida: {s_cad}
                        
                        Hash SHA256 (Copie este código para a planilha):
                        {senha_hash}
                        
                        Instruções para o Master:
                        1. Verifique a identidade do servidor.
                        2. Acesse a planilha de usuários.
                        3. Adicione o Nome, Matrícula e cole o Hash SHA256 acima na coluna SENHA.
                        4. Defina o Status como 'Aprovado'.
                        """

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

                        st.success("✅ Solicitação enviada! O Administrador fará a liberação.")
                        st.info("Sua senha foi registrada de forma segura.")
                        
                    except Exception as e:
                        st.error(f"Erro ao processar solicitação: {e}")
                        st.info("Certifique-se de configurar as credenciais de e-mail no painel de Secrets.")
                else:
                    st.warning("Por favor, preencha todos os campos, incluindo a senha.")

# =====================================================================
# 4. FUNÇÃO REUTILIZÁVEL DO DASHBOARD
# =====================================================================
def gerar_dashboard(df_filtrado):
    COL_DIA = next((c for c in df_filtrado.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
    COL_CIRCUNSCRICAO = next((c for c in df_filtrado.columns if "CIRCUNSCRI" in str(c)), None)
    COL_VITIMAS = next((c for c in df_filtrado.columns if "VÍTIMAS" in str(c) or "VITIMAS" in str(c)), None)

    total_procedimentos = len(df_filtrado)
    
    if COL_VITIMAS and COL_VITIMAS in df_filtrado.columns:
        vitimas_raw = df_filtrado[COL_VITIMAS]
        total_vitimas = pd.to_numeric(vitimas_raw.astype(str).str.replace(',', '.'), errors='coerce').fillna(0).sum()
    else: total_vitimas = 0

    c1, c2 = st.columns(2)
    
    html_c1 = f"""
    <div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #ff4b4b; text-align: center;">
        <h3 style="color: #b0b4c4; font-size: 16px;">📊 TOTAL PROCEDIMENTOS</h3>
        <h1 style="color: white; font-size: 48px;">{total_procedimentos:,}</h1>
    </div>
    """.replace(',', '.')
    with c1: st.markdown(html_c1, unsafe_allow_html=True)
    
    html_c2 = f"""
    <div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #F1C40F; text-align: center;">
        <h3 style="color: #b0b4c4; font-size: 16px;">👤 TOTAL VÍTIMAS</h3>
        <h1 style="color: white; font-size: 48px;">{int(total_vitimas):,}</h1>
    </div>
    """.replace(',', '.')
    with c2: st.markdown(html_c2, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 POR DIA DA SEMANA")
        if COL_DIA:
            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
            filtro = ~tabela_dia[COL_DIA].astype(str).str.contains("NAN|NONE", case=False, na=False)
            tabela_dia = tabela_dia[filtro]
            if not tabela_dia.empty:
                grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                    x='TOTAL:Q', y=alt.Y(f'{COL_DIA}:N', sort='-x'), color='ANO:N'
                ).properties(height=350)
                st.altair_chart(grafico_dia, use_container_width=True)

    with col2:
        st.markdown("### 🗺️ POR CIRCUNSCRIÇÃO")
        if COL_CIRCUNSCRICAO:
            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
            if not tabela_circ.empty:
                grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                    x='TOTAL:Q', y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x'), color='ANO:N'
                ).properties(height=350)
                st.altair_chart(grafico_circ, use_container_width=True)

    st.write("<br>", unsafe_allow_html=True)

    st.markdown("### ⚖️ ATRIBUIÇÃO DE CRIMES (ORCRIM)")
    
    sugestoes_orcrim = [c for c in df_filtrado.columns if "ORCRIM" in str(c) or "MOTIVAÇÃO" in str(c)]
    col_orcrim = sugestoes_orcrim[0] if sugestoes_orcrim else (df_filtrado.columns[30] if len(df_filtrado.columns) > 30 else None)

    if col_orcrim:
        col_orcrim_data = df_filtrado[col_orcrim]
        if isinstance(col_orcrim_data, pd.DataFrame):
            col_orcrim_data = col_orcrim_data.iloc[:, 0]
        
        def classificar_orcrim(texto):
            texto = str(texto).strip().upper() 
            if "INVESTIGA" in texto: return "EM INVESTIGAÇÃO"
            if "X MIL" in texto or "VS MIL" in texto: return "TRÁFICO X MILÍCIA"
            if "TRÁFICO" in texto or "TRAFICO" in texto: return "TRÁFICO"
            if "MILÍCIA" in texto or "MILICIA" in texto: return "MILÍCIA"
            return "OUTROS"

        df_filtrado_orcrim = df_filtrado.copy()
        df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] = col_orcrim_data.apply(classificar_orcrim)
        
        tot_investiga = len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'EM INVESTIGAÇÃO'])
        tot_trafico = len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'TRÁFICO'])
        tot_milicia = len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'MILÍCIA'])
        tot_traf_mil = len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'TRÁFICO X MILÍCIA'])

        card1, card2, card3, card4 = st.columns(4)
        
        html_card1 = f"""
        <div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;">
            <h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">EM INVESTIGAÇÃO</h4>
            <h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_investiga}</h2>
        </div>
        """
        with card1: st.markdown(html_card1, unsafe_allow_html=True)
        
        html_card2 = f"""
        <div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #E74C3C; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;">
            <h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">TRÁFICO</h4>
            <h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_trafico}</h2>
        </div>
        """
        with card2: st.markdown(html_card2, unsafe_allow_html=True)
        
        html_card3 = f"""
        <div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #3498DB; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;">
            <h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">MILÍCIA</h4>
            <h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_milicia}</h2>
        </div>
        """
        with card3: st.markdown(html_card3, unsafe_allow_html=True)
        
        html_card4 = f"""
        <div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #9B59B6; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;">
            <h4 style="margin: 0; color: #b0b4c4; font-size: 13px;">TRÁFICO X MILÍCIA</h4>
            <h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_traf_mil}</h2>
        </div>
        """
        with card4: st.markdown(html_card4, unsafe_allow_html=True)

# =====================================================================
# 5. LÓGICA DE NAVEGAÇÃO (LOGADO)
# =====================================================================
if not st.session_state.logado:
    tela_acesso()
else:
    st.sidebar.markdown(f"### Olá, {st.session_state.user_nome}")
    
    lista_menu = ["1. VISÃO GERAL", "2. ORCRIM", "3. MAPA", "4. MODO ANALÍTICO", "5. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master":
        lista_menu.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("NAVEGAÇÃO", lista_menu)

    # --- LÓGICA DE SUBMENU PARA ORCRIM ---
    sub_menu_orcrim = None
    if menu == "2. ORCRIM":
        st.sidebar.markdown("---")
        st.sidebar.markdown("📂 **SELECIONE A ÁREA:**")
        sub_menu_orcrim = st.sidebar.radio("", ["ÁREA 1", "ÁREA 2", "ÁREA 3", "ÁREA 4"], label_visibility="collapsed")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# ==========================================================
# ---> CABEÇALHO OFICIAL (COM LOGOS) <---
# ==========================================================
    col_esq, col_meio, col_dir = st.columns([1, 4, 1])
    with col_esq:
        try: st.image("logo1.png", width=150)
        except: st.write("")
    with col_meio:
        st.markdown("<h1 style='text-align: center;'>🛡️ MONITORAMENTO DE HOMICÍDIOS</h1>", unsafe_allow_html=True)
    with col_dir:
        try: st.image("logo2.png", width=150)
        except: st.write("")
    st.write("---")
# ==========================================================
    
    df = carregar_dados()

    if menu == "1. VISÃO GERAL":
        st.header("📊 VISÃO GERAL")
        
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disp = sorted(df['ANO'].unique().tolist(), reverse=True)
        
        st.subheader("FILTROS DE ANÁLISE")
        modo_analise = st.radio("SELECIONE O FORMATO DA ANÁLISE:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"], key="modo_vg")

        anos_selecionados = []
        
        if modo_analise == "ANÁLISE INDIVIDUAL":
            col_drop, _ = st.columns([2, 8]) 
            ano_escolhido = col_drop.selectbox("SELECIONE O ANO:", anos_disp, key="ano_ind_vg")
            anos_selecionados = [ano_escolhido]
            
        else:
            st.write("**SELECIONE OS ANOS PARA COMPARAR:**")
            
            def selecionar_todos_vg():
                for a in anos_disp: st.session_state[f"chk_vg_{a}"] = True
            def limpar_selecao_vg():
                for a in anos_disp: st.session_state[f"chk_vg_{a}"] = False

            for ano in anos_disp:
                if f"chk_vg_{ano}" not in st.session_state:
                    st.session_state[f"chk_vg_{ano}"] = True

            b1, b2, _ = st.columns([2, 2, 6])
            b1.button("✓ Todos os anos", on_click=selecionar_todos_vg, key="btn_all_vg")
            b2.button("✗ Limpar seleção", on_click=limpar_selecao_vg, key="btn_clear_vg")
            
            colunas_anos = st.columns(min(len(anos_disp), 8) or 1, gap="small")
            for i, ano in enumerate(anos_disp):
                colunas_anos[i % len(colunas_anos)].checkbox(ano, key=f"chk_vg_{ano}")
            
            anos_selecionados = [ano for ano in anos_disp if st.session_state.get(f"chk_vg_{ano}", False)]

        if len(anos_selecionados) > 0:
            df_filtrado = df[df['ANO'].isin(anos_selecionados)].copy()
            st.write("---")
            if df_filtrado.empty:
                st.warning("Nenhuma ocorrência encontrada para os anos selecionados.")
            else:
                gerar_dashboard(df_filtrado)
        else:
            st.warning("⚠️ Selecione pelo menos um ano para visualizar os dados.")

    elif menu == "2. ORCRIM":
        if sub_menu_
