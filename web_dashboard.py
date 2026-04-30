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
import time
from io import StringIO

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E CSS
# =====================================================================
st.set_page_config(page_title="🛡️ Sistema Mercúrio", layout="wide")

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
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;
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
# 1.5 FUNÇÕES DE RENDERIZAÇÃO BLINDADAS
# =====================================================================
def render_kpi(titulo, valor, cor):
    s_div = "background-color:#1E2130; padding:25px; border-radius:12px; "
    s_div += f"border-top:5px solid {cor}; text-align:center;"
    s_h3 = "color:#b0b4c4; font-size:16px;"
    s_h1 = "color:white; font-size:48px;"
    html = f"<div style='{s_div}'><h3 style='{s_h3}'>{titulo}</h3><h1 style='{s_h1}'>{valor}</h1></div>"
    st.markdown(html, unsafe_allow_html=True)

def render_card(titulo, valor, cor):
    s_div = "background-color:#1E2130; padding:20px; border-radius:10px; "
    s_div += f"border-top:5px solid {cor}; text-align:center; "
    s_div += "box-shadow:2px 2px 10px rgba(0,0,0,0.2); height:100%;"
    s_h4 = "margin:0; color:#b0b4c4; font-size:14px;"
    s_h2 = "margin:15px 0 0 0; color:white; font-size:54px; line-height:1;"
    html = f"<div style='{s_div}'><h4 style='{s_h4}'>{titulo}</h4><h2 style='{s_h2}'>{valor}</h2></div>"
    st.markdown(html, unsafe_allow_html=True)

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
        headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
        
        dados_brutos = []
        tem_mais = True
        cursor = None
        
        # Loop de Paginação: Varre o banco de dados rompendo o limite de 100
        while tem_mais:
            payload = {}
            if cursor:
                payload["start_cursor"] = cursor
                
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200: 
                break
                
            json_data = response.json()
            dados_brutos.extend(json_data.get("results", []))
            
            # Checa se o Notion tem mais páginas a fornecer
            tem_mais = json_data.get("has_more", False)
            cursor = json_data.get("next_cursor", None)
            
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
                elif tipo == "number": linha[nome_coluna] = dados_coluna.get("number")
                elif tipo == "date":
                    val = dados_coluna.get("date")
                    linha[nome_coluna] = val.get("start") if val else ""
                elif tipo == "checkbox": linha[nome_coluna] = dados_coluna.get("checkbox")
                
                # --- AJUSTE PARA LER RELAÇÕES (CUIDADO: RETORNA IDs E NÃO TEXTOS) ---
                elif tipo == "relation":
                    relacoes = dados_coluna.get("relation", [])
                    if relacoes:
                        # Extrai o ID da relação, pois o Notion não envia o nome aqui
                        ids_relacionados = [r.get("id")[:8] for r in relacoes]
                        linha[nome_coluna] = f"ID: {', '.join(ids_relacionados)}..."
                    else:
                        linha[nome_coluna] = ""
                
                # --- CHAVE MESTRA: EXTRATOR UNIVERSAL DE ROLLUP ---
                elif tipo == "rollup":
                    rollup = dados_coluna.get("rollup", {})
                    r_type = rollup.get("type")
                    if r_type == "array":
                        textos = []
                        for val in rollup.get("array", []):
                            v_type = val.get("type")
                            if v_type in ["title", "rich_text"]:
                                textos.append("".join([t.get("plain_text", "") for t in val.get(v_type, [])]))
                            elif v_type == "select":
                                sel = val.get("select")
                                if sel: textos.append(sel.get("name", ""))
                            elif v_type == "multi_select":
                                msel = val.get("multi_select", [])
                                textos.append(", ".join([s.get("name", "") for s in msel]))
                        linha[nome_coluna] = ", ".join(filter(None, textos))
                    elif r_type == "string":
                        linha[nome_coluna] = str(rollup.get("string", ""))
                    else:
                        linha[nome_coluna] = str(rollup.get(r_type, "Agregação"))
                
                # --- EXTRATOR DE FÓRMULAS ---
                elif tipo == "formula":
                    form = dados_coluna.get("formula", {})
                    f_type = form.get("type")
                    linha[nome_coluna] = str(form.get(f_type, ""))
                
                elif tipo == "files":
                    arquivos = dados_coluna.get("files", [])
                    if arquivos:
                        arq = arquivos[0]
                        linha[nome_coluna] = arq.get("file", {}).get("url") or arq.get("external", {}).get("url") or arq.get("name", "")
                    else: linha[nome_coluna] = ""
                else: linha[nome_coluna] = str(dados_coluna.get(tipo, ""))
            linhas.append(linha)
        return pd.DataFrame(linhas)
    except: return pd.DataFrame()

# =====================================================================
# 2.6 GEOPROCESSAMENTO E MAPA 
# =====================================================================
def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO: LOCALIZAÇÃO DE FATOS")
    
    with st.spinner("📡 Baixando coordenadas da base central..."):
        df = carregar_dados()
        
    col_lat = next((c for c in df.columns if "LAT" in c.upper()), None)
    col_lon = next((c for c in df.columns if "LON" in c.upper()), None)

    if col_lat and col_lon:
        with st.spinner("⚙️ Limpando e processando dados geográficos..."):
            df_lat_limpa = pd.to_numeric(df[col_lat].astype(str).str.replace(',', '.'), errors='coerce')
            df_lon_limpa = pd.to_numeric(df[col_lon].astype(str).str.replace(',', '.'), errors='coerce')
            df_mapa = df.copy()
            df_mapa[col_lat] = df_lat_limpa
            df_mapa[col_lon] = df_lon_limpa
            df_mapa = df_mapa.dropna(subset=[col_lat, col_lon])
            
            total_pontos = len(df_mapa)
            
            # --- TRAVA DE SEGURANÇA CONTRA CONGELAMENTO DE TELA ---
            limite_tatico = 1000
            if total_pontos > limite_tatico:
                st.warning(f"⚠️ Base massiva detectada ({total_pontos} registros). Plotando as {limite_tatico} ocorrências mais recentes para estabilizar o navegador.")
                df_mapa = df_mapa.tail(limite_tatico)
            else:
                st.success(f"✅ {total_pontos} pontos prontos para plotagem.")

        with st.spinner("🗺️ Renderizando satélite e inserindo alvos (isso pode levar alguns segundos)..."):
            m = folium.Map(location=[-22.9068, -43.1729], zoom_start=11, control_scale=True)
            folium.TileLayer('openstreetmap', name='Mapa de Ruas').add_to(m)
            folium.TileLayer(tiles='http://mt0.google.com/vt/lyrs=y&hl=pt-BR&x={x}&y={y}&z={z}', attr='Google', name='Satélite Híbrido').add_to(m)
            Draw(export=False, position='topleft').add_to(m)

            col_proc = next((c for c in df_mapa.columns if "PROC" in c or "RO" == c or "REGISTRO" in c), "PROCEDIMENTO")
            col_delito = next((c for c in df_mapa.columns if "DELITO" in c or "NATUREZA" in c or "CRIME" in c), "DELITO")
            col_circ = next((c for c in df_mapa.columns if "CIRCUNSCRI" in c or "DP" == c), "CIRCUNSCRIÇÃO")
            col_data = next((c for c in df_mapa.columns if "DATA" in c), "DATA")
            col_local = next((c for c in df_mapa.columns if "LOGRADOURO" in c or "LOCAL" in c or "ENDEREÇO" in c), "LOCAL")

            mc = MarkerCluster(name="Ocorrências Mapeadas").add_to(m)
            for _, row in df_mapa.iterrows():
                html_popup = f"""<div style='min-width: 220px; font-family: sans-serif;'><h4 style='margin-top: 0; margin-bottom: 5px; color: #8B0000;'>{row.get(col_proc, 'N/I')}</h4><hr style='margin: 5px 0;'><b>Delito:</b> {row.get(col_delito, 'N/I')}<br><b>Data:</b> {row.get(col_data, 'N/I')}<br><b>Circunscrição:</b> {row.get(col_circ, 'N/I')}<br><b>Local:</b> {row.get(col_local, 'N/I')}</div>"""
                folium.Marker(location=[row[col_lat], row[col_lon]], popup=folium.Popup(html_popup, max_width=350), icon=folium.Icon(color='darkred', icon='info-sign')).add_to(mc)
            
            folium.LayerControl().add_to(m)
            st_folium(m, width=1200, height=600, returned_objects=[])
            
    else: st.error("⚠️ Colunas de Latitude/Longitude não encontradas na base do Google Sheets.")

# =====================================================================
# 3. INTERFACE DE ACESSO
# =====================================================================
@st.cache_data(ttl=5) 
def carregar_usuarios():
    url = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/gviz/tq?tqx=out:csv&sheet=USUARIOS"
    for _ in range(3): 
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                df = pd.read_csv(StringIO(res.text))
                df.columns = [str(c).strip().upper() for c in df.columns]
                df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
                return df
        except:
            time.sleep(1)
    return pd.DataFrame()

def tela_acesso():
    col_esq, col_meio, col_dir = st.columns([1, 4, 1])
    with col_meio:
        st.markdown("<h1 style='text-align: center;'>🛡️ ACESSO AO SISTEMA</h1>", unsafe_allow_html=True)
        aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Solicitar Cadastro"])
        
        with aba_login:
            mat_login = st.text_input("Matrícula", key="login_mat_input")
            senha_login = st.text_input("Senha", type="password", key="login_pass_input")
            
            if st.button("Acessar Painel"):
                with st.spinner("Autenticando..."):
                    df_users = carregar_usuarios()
                    
                    if not df_users.empty:
                        senha_hash = gerar_hash(senha_login)
                        user_match = df_users[(df_users['MATRICULA'] == str(mat_login).strip()) & (df_users['SENHA'] == senha_hash)]
                        
                        if not user_match.empty:
                            if str(user_match.iloc[0]['STATUS']).strip().upper() == 'APROVADO':
                                st.session_state.logado = True
                                st.session_state.user_nivel = user_match.iloc[0]['NIVEL']
                                st.session_state.user_nome = user_match.iloc[0]['NOME']
                                st.rerun()
                            else: 
                                st.warning("Acesso Pendente. Aguarde a liberação do Administrador.")
                        else: 
                            st.error("Matrícula ou Senha incorretos.")
                    else:
                        st.error("Falha ao contatar o servidor de credenciais. Tente novamente.")

        with aba_cadastro:
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
                        corpo = f"NOVA SOLICITAÇÃO\nNome: {n_cad}\nMatrícula: {m_cad}\nHash SHA256: {senha_hash}"
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
                    except: st.error("Erro ao processar solicitação.")
                else: st.warning("Preencha todos os campos.")

# =====================================================================
# 4. DASHBOARD 
# =====================================================================
def gerar_dashboard(df_filtrado):
    COL_DIA = next((c for c in df_filtrado.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
    COL_CIRCUNSCRICAO = next((c for c in df_filtrado.columns if "CIRCUNSCRI" in str(c)), None)
    
    COL_VITIMAS = None
    for c in df_filtrado.columns:
        if "VÍTIMAS" in str(c).upper() or "VITIMAS" in str(c).upper():
            COL_VITIMAS = c
            break

    total_procedimentos = len(df_filtrado)
    if COL_VITIMAS and COL_VITIMAS in df_filtrado.columns:
        total_vitimas = pd.to_numeric(df_filtrado[COL_VITIMAS].astype(str).str.replace(',', '.'), errors='coerce').fillna(0).sum()
    else: total_vitimas = 0

    c1, c2 = st.columns(2)
    with c1: render_kpi("📊 TOTAL PROCEDIMENTOS", f"{total_procedimentos:,}".replace(',', '.'), "#ff4b4b")
    with c2: render_kpi("👤 TOTAL VÍTIMAS", f"{int(total_vitimas):,}".replace(',', '.'), "#F1C40F")

    st.write("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 POR DIA DA SEMANA")
        if COL_DIA:
            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
            tabela_dia = tabela_dia[~tabela_dia[COL_DIA].astype(str).str.contains("NAN|NONE", case=False, na=False)]
            if not tabela_dia.empty: st.altair_chart(alt.Chart(tabela_dia).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_DIA}:N', sort='-x'), color='ANO:N').properties(height=350), use_container_width=True)

    with col2:
        st.markdown("### 🗺️ POR CIRCUNSCRIÇÃO")
        if COL_CIRCUNSCRICAO:
            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
            if not tabela_circ.empty: st.altair_chart(alt.Chart(tabela_circ).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x'), color='ANO:N').properties(height=350), use_container_width=True)

    st.write("<br>", unsafe_allow_html=True)
    st.markdown("### ⚖️ ATRIBUIÇÃO DE CRIMES (ORCRIM)")
    sugestoes_orcrim = [c for c in df_filtrado.columns if "ORCRIM" in str(c) or "MOTIVAÇÃO" in str(c)]
    col_orcrim = sugestoes_orcrim[0] if sugestoes_orcrim else (df_filtrado.columns[30] if len(df_filtrado.columns) > 30 else None)

    if col_orcrim:
        col_orcrim_data = df_filtrado[col_orcrim].iloc[:, 0] if isinstance(df_filtrado[col_orcrim], pd.DataFrame) else df_filtrado[col_orcrim]
        def classificar_orcrim(texto):
            t = str(texto).strip().upper() 
            if "INVESTIGA" in t: return "EM INVESTIGAÇÃO"
            if "X MIL" in t or "VS MIL" in t: return "TRÁFICO X MILÍCIA"
            if "TRÁFICO" in t or "TRAFICO" in t: return "TRÁFICO"
            if "MILÍCIA" in t or "MILICIA" in t: return "MILÍCIA"
            return "OUTROS"

        df_filtrado_orcrim = df_filtrado.copy()
        df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] = col_orcrim_data.apply(classificar_orcrim)
        
        card1, card2, card3, card4 = st.columns(4)
        with card1: render_card("EM INVESTIGAÇÃO", len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'EM INVESTIGAÇÃO']), "#F1C40F")
        with card2: render_card("TRÁFICO", len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'TRÁFICO']), "#E74C3C")
        with card3: render_card("MILÍCIA", len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'MILÍCIA']), "#3498DB")
        with card4: render_card("TRÁFICO X MILÍCIA", len(df_filtrado_orcrim[df_filtrado_orcrim['ORCRIM_CLASSIFICADO'] == 'TRÁFICO X MILÍCIA']), "#9B59B6")

# =====================================================================
# 5. LÓGICA DE NAVEGAÇÃO PRINCIPAL E MÓDULOS DE ORCRIM
# =====================================================================
if not st.session_state.logado:
    tela_acesso()
else:
    st.sidebar.markdown(f"### Olá, {st.session_state.user_nome}")
    lista_menu = ["1. VISÃO GERAL", "2. ORCRIM", "3. MAPA", "4. MODO ANALÍTICO", "5. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master": lista_menu.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("NAVEGAÇÃO", lista_menu)

    sub_menu_orcrim = None
    if menu == "2. ORCRIM":
        st.sidebar.markdown("---")
        st.sidebar.markdown("📂 **SELECIONE A ÁREA:**")
        sub_menu_orcrim = st.sidebar.radio("Areas", ["ÁREA 1", "ÁREA 2", "ÁREA 3", "ÁREA 4"], label_visibility="collapsed")

    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # =====================================================================
    # CABEÇALHO - SISTEMA MERCÚRIO (Blindagem Mobile)
    # =====================================================================
    col_logos, col_titulo = st.columns([1.5, 4])
    
    with col_logos:
        logos_ativos = []
        try: 
            open("logo1.png")
            logos_ativos.append("logo1.png")
        except: pass
        
        try: 
            open("logo2.png")
            logos_ativos.append("logo2.png")
        except: pass
        
        if logos_ativos:
            st.image(logos_ativos, width=85)
            
    with col_titulo:
        st.markdown("<h1 style='text-align: left; margin-top: 10px;'>🛡️ SISTEMA MERCÚRIO</h1>", unsafe_allow_html=True)
        
    st.write("---")
    
    df = carregar_dados()

    if menu == "1. VISÃO GERAL":
        st.header("📊 VISÃO GERAL")
        
        try:
            data_atualizacao = df.iloc[-1, 5] 
            st.markdown(f"""
                <div style='color:#2ecc71; font-size:11px; font-style:italic; margin-top:-15px; margin-bottom:15px;'>
                    Base atualizada em: {data_atualizacao}
                </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            pass 

        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disp = sorted(df['ANO'].unique().tolist(), reverse=True)
        modo_analise = st.radio("SELECIONE O FORMATO:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"], key="modo_vg")

        anos_selecionados = []
        if modo_analise == "ANÁLISE INDIVIDUAL":
            col_drop, _ = st.columns([2, 8]) 
            anos_selecionados = [col_drop.selectbox("SELECIONE O ANO:", anos_disp, key="ano_ind")]
        else:
            st.write("**SELECIONE OS ANOS:**")
            def sel_all():
                for a in anos_disp: st.session_state[f"chk_vg_{a}"] = True
            def limp_all():
                for a in anos_disp: st.session_state[f"chk_vg_{a}"] = False
            for ano in anos_disp:
                if f"chk_vg_{ano}" not in st.session_state: st.session_state[f"chk_vg_{ano}"] = True

            b1, b2, _ = st.columns([2, 2, 6])
            b1.button("✓ Todos", on_click=sel_all, key="btn_all_vg")
            b2.button("✗ Limpar", on_click=limp_all, key="btn_clear_vg")
            col_a = st.columns(min(len(anos_disp), 8) or 1, gap="small")
            for i, ano in enumerate(anos_disp): col_a[i % len(col_a)].checkbox(ano, key=f"chk_vg_{ano}")
            anos_selecionados = [a for a in anos_disp if st.session_state.get(f"chk_vg_{a}", False)]

        if len(anos_selecionados) > 0:
            df_filtrado = df[df['ANO'].isin(anos_selecionados)].copy()
            st.write("---")
            if df_filtrado.empty: st.warning("Nenhuma ocorrência encontrada.")
            else: gerar_dashboard(df_filtrado) 
        else: st.warning("⚠️ Selecione pelo menos um ano.")

    elif menu == "2. ORCRIM":
        area_selecionada = str(sub_menu_orcrim)
        if area_selecionada == "ÁREA 1":
            st.header("📓 ÁREA 1 - INTELIGÊNCIA")
            
            with st.spinner("Sincronizando Central..."):
                df_notion = carregar_dados_notion()
                
            if not df_notion.empty:
                st.success(f"✅ {len(df_notion)} registros ativos no banco de dados.")
                
                st.markdown("### 🎯 Busca Integrada de Alvos")
                if "alvo_busca" not in st.session_state: st.session_state.alvo_busca = ""
                def limpar_alvo(): st.session_state.alvo_busca = ""

                nomes_disponiveis = df_notion["Nome"].dropna().unique().tolist()
                
                col_busca, col_btn, _ = st.columns([3, 1, 6])
                alvo_selecionado = col_busca.selectbox("Selecione o Alvo:", [""] + nomes_disponiveis, key="alvo_busca")
                col_btn.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                col_btn.button("🧹 Limpar", on_click=limpar_alvo)
                
                st.write("---")
                
                aba_dossie, aba_organograma, aba_tabela = st.tabs(["📇 DOSSIÊ TÁTICO", "🕸️ ORGANOGRAMA", "📋 TABELA GERAL"])
                
                with aba_dossie:
                    if alvo_selecionado:
                        dados_alvo = df_notion[df_notion["Nome"] == alvo_selecionado].iloc[0]
                        col_foto, col_info = st.columns([1, 2])
                        with col_foto:
                            foto_url = dados_alvo.get("Foto", "")
                            if str(foto_url).startswith("http"): st.image(foto_url, use_container_width=True)
                            else: st.info("👤 Sem foto no arquivo.")
                                
                        with col_info:
                            vulgo = dados_alvo.get("Vulgo", "N/I")
                            st.markdown(f"<h2>{alvo_selecionado} <span style='color:#E74C3C; font-size:24px;'>({vulgo})</span></h2>", unsafe_allow_html=True)
                            st.markdown(f"**RG:** {dados_alvo.get('RG', 'N/I')}")
                            st.markdown(f"**Organização:** {dados_alvo.get('Organização', 'N/I')}")
                            st.markdown(f"**Função / Hierarquia:** {dados_alvo.get('Função', 'N/I')}")
                            
                            col_territorio = next((c for c in df_notion.columns if "TERRITÓRIO" in c.upper() or "TERRITORIO" in c.upper()), "Território")
                            st.markdown(f"**Área de Atuação:** {dados_alvo.get(col_territorio, 'N/I')}")
                            
                            st.markdown(f"**Situação Atual:** {dados_alvo.get('Situação', 'N/I')}")
                            st.markdown(f"**Redes Sociais Monitoradas:** {dados_alvo.get('Rede social', 'N/I')}")
                            
                        if str(dados_alvo.get("Informe", "")).strip() and str(dados_alvo.get("Informe", "")) != "nan":
                            st.write("---")
                            st.markdown("#### 📝 Informe Analítico")
                            st.warning(dados_alvo.get("Informe", ""))
                    else:
                        st.info("Aguardando seleção de alvo no buscador acima.")
                
                with aba_organograma:
                    if alvo_selecionado:
                        dados_alvo = df_notion[df_notion["Nome"] == alvo_selecionado].iloc[0]
                        
                        col_territorio = next((c for c in df_notion.columns if "TERRITÓRIO" in c.upper() or "TERRITORIO" in c.upper()), "Território")
                        atuacao_alvo = str(dados_alvo.get(col_territorio, "")).strip()

                        if atuacao_alvo and atuacao_alvo.upper() not in ["NAN", "N/I", "NONE", "AGREGAÇÃO", ""]:
                            df_area = df_notion[df_notion[col_territorio] == atuacao_alvo]
                            
                            def clean_text(txt): return str(txt).replace('"', '').replace('\n', ' ').strip()

                            # --- CÉREBRO HIERÁRQUICO (4 NÍVEIS RIGOROSOS) ---
                            def get_nivel(funcao):
                                f_up = str(funcao).upper()
                                
                                if "DONO" in f_up: 
                                    return 1, "DONO"
                                elif "FRENTE" in f_up: 
                                    return 2, "FRENTE"
                                elif "GERENTE" in f_up or "LÍDER" in f_up or "LIDER" in f_up: 
                                    return 3, "GERÊNCIA / LIDERANÇA"
                                else: 
                                    return 4, "INTEGRANTES / OUTRAS FUNÇÕES"
                            
                            orgs = df_area["Organização"].dropna().unique().tolist()
                            
                            html_organograma = ""
                            html_organograma += f"<div style='background-color:#1E2130; padding:20px; border-radius:10px; margin-bottom:20px; text-align:center;'>"
                            html_organograma += f"<h2 style='color:#ffffff; margin:0;'>🏢 TERRITÓRIO: {atuacao_alvo.upper()}</h2>"
                            html_organograma += "</div>"
                            
                            for org in orgs:
                                org_cl = clean_text(org)
                                if org_cl.upper() in ["NAN", "N/I", "", "-"]: continue
                                
                                html_organograma += f"<div style='border:2px solid #ff4b4b; padding:15px; border-radius:10px; margin-bottom:30px;'>"
                                html_organograma += f"<h3 style='text-align:center; color:#ff4b4b; margin-top:0;'>⚙️ ORCRIM: {org_cl}</h3>"

                                html_organograma += "<style>"
                                html_organograma += ".tatico-card { transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); position: relative; }"
                                html_organograma += ".tatico-card:hover { transform: scale(1.15); z-index: 999; box-shadow: 0 14px 28px rgba(0,0,0,0.5), 0 10px 10px rgba(0,0,0,0.4) !important; }"
                                html_organograma += ".tatico-card .info-oculta { max-height: 0; opacity: 0; overflow: hidden; transition: all 0.3s ease; }"
                                html_organograma += ".tatico-card:hover .info-oculta { max-height: 100px; opacity: 1; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #7f8c8d; }"
                                html_organograma += ".tatico-card img { transition: all 0.3s ease; }"
                                html_organograma += ".tatico-card:hover img { width: 145px !important; height: 145px !important; border-radius: 12px !important; margin-bottom: 12px; }"
                                html_organograma += "</style>"

                                df_org = df_area[df_area["Organização"] == org]
                                ranks = {}
                                for _, r in df_org.iterrows():
                                    func = clean_text(r.get("Função", ""))
                                    nome = clean_text(r.get("Nome", ""))
                                    foto = r.get("Foto", "")
                                    vulgo = clean_text(r.get("Vulgo", "N/I"))
                                    rg = clean_text(r.get("RG", "N/I"))
                                    
                                    if nome.upper() in ["NAN", "N/I", "", "-"]: continue
                                    idx, nome_nivel = get_nivel(func)
                                    if idx not in ranks: ranks[idx] = []
                                    ranks[idx].append((nome, func, foto, vulgo, rg)) 

                                for rank_idx in sorted(ranks.keys()):
                                    nome_nivel = get_nivel(ranks[rank_idx][0][1])[1]
                                    
                                    html_organograma += f"<div style='background-color:#2d3446; padding:8px; border-radius:5px; margin-top:20px; margin-bottom:10px; text-align:center; color:#F1C40F; font-weight:bold; font-size:14px; letter-spacing:1px;'>{nome_nivel}</div>"
                                    
                                    html_organograma += "<div style='display:flex; flex-wrap:wrap; justify-content:center; gap:12px;'>"
                                    
                                    for p_nome, p_func, p_foto, p_vulgo, p_rg in ranks[rank_idx]:
                                        if p_nome == clean_text(alvo_selecionado):
                                            bg_color = "#E74C3C"
                                            b_color = "#ffffff"
                                        else:
                                            bg_color = "#4a4f63"
                                            b_color = "#333333"
                                            
                                        img_html = ""
                                        if str(p_foto).startswith("http"):
                                            img_html = f"<img src='{p_foto}' style='width:135px; height:135px; border-radius:50%; object-fit:cover; margin-bottom:6px; border:2px solid {b_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.4);'>"
                                            
                                        html_organograma += f"<div class='tatico-card' style='background-color:{bg_color}; border:2px solid {b_color}; border-radius:8px; padding:15px 10px; min-width:180px; max-width:240px; flex: 1 1 auto; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); display: flex; flex-direction: column; align-items: center; justify-content: flex-start; cursor: crosshair;'>"
                                        html_organograma += f"{img_html}"
                                        html_organograma += f"<div style='color:white; font-size:13px; font-weight:bold;'>{p_nome}</div>"
                                        
                                        if p_vulgo and p_vulgo.upper() not in ["NAN", "N/I", ""]:
                                            html_organograma += f"<div style='color:#F1C40F; font-size:12px; font-style:italic; margin-top:2px;'>\"{p_vulgo}\"</div>"
                                            
                                        html_organograma += f"<div style='color:#e0e0e0; font-size:11px; margin-top:4px;'>({p_func})</div>"
                                        html_organograma += f"<div class='info-oculta'>"
                                        html_organograma += f"<div style='color:#b0b4c4; font-size:11px; padding-bottom:4px;'><b>RG:</b> {p_rg}</div>"
                                        html_organograma += f"</div></div>"
                                        
                                    html_organograma += "</div>"
                                html_organograma += "</div>"
                                
                            st.markdown(html_organograma, unsafe_allow_html=True)

                        else:
                            st.warning("O alvo não possui um território cadastrado para mapeamento.")
                    else:
                        st.info("Selecione um alvo na busca acima para gerar o organograma territorial da sua área.")

                with aba_tabela:
                    ordem_ideal = ["Nome", "Vulgo", "RG", "Foto", "Território", "Organização", "Função", "Situação", "Rede social", "Informe"] 
                    c_ex = [c for c in ordem_ideal if c in df_notion.columns]
                    c_extra = [c for c in df_notion.columns if c not in c_ex]
                    df_notion = df_notion[c_ex + c_extra]

                    with st.expander("🔍 FILTROS DA TABELA GERAL", expanded=False):
                        col_at = next((c for c in df_notion.columns if "TERRITÓRIO" in c.upper() or "TERRITORIO" in c.upper()), None)
                        col_fn = next((c for c in df_notion.columns if "FUNÇÃO" in c.upper() or "FUNCAO" in c.upper()), None)
                        col_org = next((c for c in df_notion.columns if "ORGANIZAÇÃO" in c.upper() or "ORCRIM" in c.upper()), None)
                        
                        df_filt = df_notion.copy()
                        c1, c2, c3 = st.columns(3)
                        
                        if col_at:
                            sel_at = c1.multiselect(f"{col_at}:", df_notion[col_at].dropna().unique().tolist())
                            if sel_at: df_filt = df_filt[df_filt[col_at].isin(sel_at)]
                        if col_fn:
                            sel_fn = c2.multiselect(f"{col_fn}:", df_notion[col_fn].dropna().unique().tolist())
                            if sel_fn: df_filt = df_filt[df_filt[col_fn].isin(sel_fn)]
                        if col_org:
                            sel_org = c3.multiselect(f"{col_org}:", df_notion[col_org].dropna().unique().tolist())
                            if sel_org: df_filt = df_filt[df_filt[col_org].isin(sel_org)]

                    st.write("---")
                    cfg = {}
                    for c in df_filt.columns:
                        if "FOTO" in c.upper() or "IMAGEM" in c.upper(): cfg[c] = st.column_config.ImageColumn(c, width="small") 
                        elif df_filt[c].astype(str).str.startswith("http").any(): cfg[c] = st.column_config.LinkColumn(c, display_text="🔗")

                    st.dataframe(df_filt, column_config=cfg, use_container_width=True)
            else:
                st.warning("Sem dados.")
