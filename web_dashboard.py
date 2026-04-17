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
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

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
# 1.5 FUNÇÕES DE RENDERIZAÇÃO BLINDADAS (Anti-Quebra de Linha)
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
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers)
        if response.status_code != 200:
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
                    linha[nome_coluna] = f"🔗 {len(relacoes)} Vinculada(s)" if relacoes else ""
                elif tipo == "rollup":
                    rollup = dados_coluna.get("rollup", {})
                    if rollup.get("type") == "array":
                        vals = rollup.get("array", [])
                        textos = ["".join([t.get("plain_text", "") for t in v.get(v.get("type"), [])]) for v in vals]
                        linha[nome_coluna] = ", ".join(textos)
                    else:
                        linha[nome_coluna] = "Agregação"
                elif tipo == "files":
                    arquivos = dados_coluna.get("files", [])
                    if arquivos:
                        arq = arquivos[0]
                        linha[nome_coluna] = arq.get("file", {}).get("url") or arq.get("external", {}).get("url") or arq.get("name", "")
                    else:
                        linha[nome_coluna] = ""
                else:
                    linha[nome_coluna] = str(dados_coluna.get(tipo, ""))
            linhas.append(linha)
        return pd.DataFrame(linhas)
    except:
        return pd.DataFrame()

# =====================================================================
# 2.6 GEOPROCESSAMENTO E MAPA (AGRUPADOR TÁTICO E BALÕES INTELIGENTES)
# =====================================================================
def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO: LOCALIZAÇÃO DE FATOS")
    
    df = carregar_dados()
    
    col_lat = next((c for c in df.columns if "LAT" in c.upper()), None)
    col_lon = next((c for c in df.columns if "LON" in c.upper()), None)

    if col_lat and col_lon:
        df_lat_limpa = pd.to_numeric(df[col_lat].astype(str).str.replace(',', '.'), errors='coerce')
        df_lon_limpa = pd.to_numeric(df[col_lon].astype(str).str.replace(',', '.'), errors='coerce')
        
        df_mapa = df.copy()
        df_mapa[col_lat] = df_lat_limpa
        df_mapa[col_lon] = df_lon_limpa
        df_mapa = df_mapa.dropna(subset=[col_lat, col_lon])
        
        st.success(f"✅ {len(df_mapa)} pontos localizados via coordenadas da planilha.")

        m = folium.Map(location=[-22.9068, -43.1729], zoom_start=11, control_scale=True)

        folium.TileLayer('openstreetmap', name='Mapa de Ruas').add_to(m)
        folium.TileLayer(
            tiles='http://mt0.google.com/vt/lyrs=y&hl=pt-BR&x={x}&y={y}&z={z}',
            attr='Google',
            name='Satélite Híbrido'
        ).add_to(m)

        Draw(export=False, position='topleft').add_to(m)

        # Mapeamento Inteligente de Colunas para o Balão
        col_proc = next((c for c in df_mapa.columns if "PROC" in c or "RO" == c or "REGISTRO" in c), "PROCEDIMENTO")
        col_delito = next((c for c in df_mapa.columns if "DELITO" in c or "NATUREZA" in c or "CRIME" in c), "DELITO")
        col_circ = next((c for c in df_mapa.columns if "CIRCUNSCRI" in c or "DP" == c), "CIRCUNSCRIÇÃO")
        col_data = next((c for c in df_mapa.columns if "DATA" in c), "DATA")
        col_local = next((c for c in df_mapa.columns if "LOGRADOURO" in c or "LOCAL" in c or "ENDEREÇO" in c), "LOCAL")

        # Inicializa o Agrupador de Marcadores (MarkerCluster)
        mc = MarkerCluster(name="Ocorrências Mapeadas").add_to(m)

        for _, row in df_mapa.iterrows():
            
            # Construção do Balão Formato Tático em HTML
            html_popup = f"""
            <div style='min-width: 220px; font-family: sans-serif;'>
                <h4 style='margin-top: 0; margin-bottom: 5px; color: #8B0000;'>{row.get(col_proc, 'N/I')}</h4>
                <hr style='margin: 5px 0;'>
                <b>Delito:</b> {row.get(col_delito, 'N/I')}<br>
                <b>Data:</b> {row.get(col_data, 'N/I')}<br>
                <b>Circunscrição:</b> {row.get(col_circ, 'N/I')}<br>
                <b>Local:</b> {row.get(col_local, 'N/I')}
            </div>
            """
            
            folium.Marker(
                location=[row[col_lat], row[col_lon]],
                popup=folium.Popup(html_popup, max_width=350),
                icon=folium.Icon(color='darkred', icon='info-sign')
            ).add_to(mc)

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
                    st.error("Erro na base de usuários.")

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
                    except Exception as e:
                        st.error(f"Erro ao processar solicitação: {e}")
                else:
                    st.warning("Preencha todos os campos.")

# =====================================================================
# 4. DASHBOARD 
# =====================================================================
def gerar_dashboard(df_filtrado):
    COL_DIA = next((c for c in df_filtrado.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
    COL_CIRCUNSCRICAO = next((c for c in df_filtrado.columns if "CIRCUNSCRI" in str(c)), None)
    COL_VITIMAS = next((c for c in df_filtrado.columns if "VÍTIMAS" in str(c) or "VITIMAS" in str(c)), None)

    total_procedimentos = len(df_filtrado)
    
    if COL_VITIMAS and COL_VITIMAS in df_filtrado.columns:
        vitimas_raw = df_filtrado[COL_VITIMAS]
        total_vitimas = pd.to_numeric(vitimas_raw.astype(str).str.replace(',', '.'), errors='coerce').fillna(0).sum()
    else: 
        total_vitimas = 0

    c1, c2 = st.columns(2)
    with c1: 
        render_kpi("📊 TOTAL PROCEDIMENTOS", f"{total_procedimentos:,}".replace(',', '.'), "#ff4b4b")
    with c2: 
        render_kpi("👤 TOTAL VÍTIMAS", f"{int(total_vitimas):,}".replace(',', '.'), "#F1C40F")

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
        if isinstance(col_orcrim_data, pd.DataFrame): col_orcrim_data = col_orcrim_data.iloc[:, 0]
        
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
        with card1: render_card("EM INVESTIGAÇÃO", tot_investiga, "#F1C40F")
        with card2: render_card("TRÁFICO", tot_trafico, "#E74C3C")
        with card3: render_card("MILÍCIA", tot_milicia, "#3498DB")
        with card4: render_card("TRÁFICO X MILÍCIA", tot_traf_mil, "#9B59B6")

# =====================================================================
# 5. LÓGICA DE NAVEGAÇÃO PRINCIPAL
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
    
    df = carregar_dados()

    if menu == "1. VISÃO GERAL":
        st.header("📊 VISÃO GERAL")
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disp = sorted(df['ANO'].unique().tolist(), reverse=True)
        
        st.subheader("FILTROS DE ANÁLISE")
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
            for i, ano in enumerate(anos_disp):
                col_a[i % len(col_a)].checkbox(ano, key=f"chk_vg_{ano}")
            
            anos_selecionados = [a for a in anos_disp if st.session_state.get(f"chk_vg_{a}", False)]

        if len(anos_selecionados) > 0:
            df_filtrado = df[df['ANO'].isin(anos_selecionados)].copy()
            st.write("---")
            if df_filtrado.empty: st.warning("Nenhuma ocorrência encontrada.")
            else: gerar_dashboard(df_filtrado)
        else:
            st.warning("⚠️ Selecione pelo menos um ano.")

    elif menu == "2. ORCRIM":
        area_selecionada = str(sub_menu_orcrim)
        if area_selecionada == "ÁREA 1":
            st.header("📓 ÁREA 1")
            with st.spinner("Sincronizando..."):
                df_notion = carregar_dados_notion()
            if not df_notion.empty:
                st.success(f"✅ {len(df_notion)} registros encontrados.")
                ordem_ideal = ["Nome", "Vulgo", "RG", "Foto", "Atuação", "Organização", "Função", "Situação", "Rede social", "Informe"] 
                c_ex = [c for c in ordem_ideal if c in df_notion.columns]
                c_extra = [c for c in df_notion.columns if c not in c_ex]
                df_notion = df_notion[c_ex + c_extra]

                with st.expander("🔍 FILTROS", expanded=True):
                    col_at = next((c for c in df_notion.columns if "ATUAÇÃO" in c.upper() or "ATUACAO" in c.upper()), None)
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
        else:
            st.info(f"O painel da {area_selecionada} está em estruturação.")

    elif menu == "3. MAPA":
        pagina_mapa()

    elif menu == "4. MODO ANALÍTICO":
        st.header("📑 MODO ANALÍTICO")
        st.dataframe(df)

    elif menu == "5. ASSISTENTE IA":
        st.header("🤖 Analista Criminal Virtual")
        api_key = st.sidebar.text_input("🔑 Chave Gemini:", type="password")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("Sistemas prontos.")
            except:
                st.error("Erro na chave.")

    elif menu == "⚙️ CONFIGURAÇÕES":
        st.header("⚙️ Administrador")
        try: st.dataframe(conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS"))
        except: st.error("Erro ao carregar usuários.")
