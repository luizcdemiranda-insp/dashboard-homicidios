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
from geopy.geocoders import Nominatim
from folium.plugins import Draw
import time

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
# 2.6 GEOLOCALIZADOR E MAPA
# =====================================================================
geolocator = Nominatim(user_agent="monitor_homicidios_app")

@st.cache_data
def geocodificar_endereco(endereco):
    try:
        location = geolocator.geocode(endereco)
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
        return None, None

def pagina_mapa():
    st.header("📍 GEOPROCESSAMENTO E ANÁLISE TERRITORIAL")
    
    df = carregar_dados() 
    
    with st.expander("🌐 Processar Pontos da Planilha", expanded=False):
        st.write("Convertendo endereços em marcadores. Isso pode levar alguns minutos dependendo do tamanho da planilha...")
        pontos_mapeados = []
        
        # --- REMOVIDA A TRAVA DE 10 LINHAS ---
        # Adicionada uma barra de progresso visual
        df_validos = df.dropna(subset=['LOGRADOURO', 'BAIRRO']).copy()
        total_linhas = len(df_validos)
        
        # Se for muita coisa, vamos limitar a 100 por segurança temporária, 
        # mas você pode tirar o .head(100) quando quiser testar tudo.
        df_processar = df_validos.head(100) 
        
        barra_progresso = st.progress(0)
        texto_progresso = st.empty()
        
        for i, (index, row) in enumerate(df_processar.iterrows()):
            endereco_completo = f"{row.get('LOGRADOURO', '')}, {row.get('BAIRRO', '')}, {row.get('MUNICÍPIO', '')}, RJ, Brasil"
            lat, lon = geocodificar_endereco(endereco_completo)
            
            if lat:
                pontos_mapeados.append({
                    "lat": lat, 
                    "lon": lon, 
                    "info": f"<b>Local:</b> {row.get('LOGRADOURO', '')}<br><b>Bairro:</b> {row.get('BAIRRO', '')}"
                })
                
            # Atualiza a barra de progresso
            percentual = int(((i + 1) / len(df_processar)) * 100)
            barra_progresso.progress(percentual)
            texto_progresso.text(f"Processando endereço {i+1} de {len(df_processar)}...")
            
            time.sleep(1) # Respeito ao servidor gratuito (Obrigatório)
            
        st.success(f"Geocodificação concluída! {len(pontos_mapeados)} locais encontrados com sucesso.")

    m = folium.Map(location=[-22.9068, -43.1729], zoom_start=11, control_scale=True)

    # 1. Camadas de Fundo (Agora com Google Hybrid)
    folium.TileLayer('openstreetmap', name='Mapa de Ruas').add_to(m)
    folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=y&hl=pt-BR&x={x}&y={y}&z={z}',
        attr='Google',
        name='Satélite com Ruas (Google)'
    ).add_to(m)

    Draw(
        export=False,
        position='topleft',
        draw_options={
            'polyline': True,
            'rectangle': True,
            'polygon': True,
            'circle': False,
            'marker': True,
            'circlemarker': False
        }
    ).add_to(m)

    # 3. Plotagem Tática (Círculos de Incidência em vez de Alfinetes Quebrados)
    for p in pontos_mapeados:
        folium.CircleMarker(
            location=[p['lat'], p['lon']], 
            radius=7, # Tamanho da bolinha
            popup=folium.Popup(p['info'], max_width=300), 
            color='#8B0000', # Borda vermelho escuro
            fill=True,
            fill_color='#FF0000', # Preenchimento vermelho forte
            fill_opacity=0.7
        ).add_to(m)

    folium.LayerControl().add_to(m)

    st_folium(m, width=1200, height=600, returned_objects=[])

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
    with c1: st.markdown(f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #ff4b4b; text-align: center;"><h3 style="color: #b0b4c4; font-size: 16px;">📊 TOTAL PROCEDIMENTOS</h3><h1 style="color: white; font-size: 48px;">{total_procedimentos:,}</h1></div>'.replace(',', '.'), unsafe_allow_html=True)
    with c2: st.markdown(f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #F1C40F; text-align: center;"><h3 style="color: #b0b4c4; font-size: 16px;">👤 TOTAL VÍTIMAS</h3><h1 style="color: white; font-size: 48px;">{int(total_vitimas):,}</h1></div>'.replace(',', '.'), unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 POR DIA DA SEMANA")
        if COL_DIA:
            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
            tabela_dia = tabela_dia[~tabela_dia[COL_DIA].astype(str).str.contains("NAN|NONE", case=False, na=False)]
            if not tabela_dia.empty:
                grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_DIA}:N', sort='-x'), color='ANO:N').properties(height=350)
                st.altair_chart(grafico_dia, use_container_width=True)

    with col2:
        st.markdown("### 🗺️ POR CIRCUNSCRIÇÃO")
        if COL_CIRCUNSCRICAO:
            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
            if not tabela_circ.empty:
                grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x'), color='ANO:N').properties(height=350)
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
        
        with card1:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">EM INVESTIGAÇÃO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_investiga}</h2></div>', unsafe_allow_html=True)
        with card2:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #E74C3C; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">TRÁFICO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_trafico}</h2></div>', unsafe_allow_html=True)
        with card3:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #3498DB; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_milicia}</h2></div>', unsafe_allow_html=True)
        with card4:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #9B59B6; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 13px;">TRÁFICO X MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_traf_mil}</h2></div>', unsafe_allow_html=True)

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
        if sub_menu_orcrim == "ÁREA 1":
            st.header("📓 ÁREA 1")
            st.write("Dados extraídos em tempo real da Central de Inteligência.")
            
            with st.spinner("Sincronizando com o Notion..."):
                df_notion = carregar_dados_notion()
                
            if not df_notion.empty:
                st.success(f"✅ Conexão estabelecida! {len(df_notion)} registros encontrados.")
                
                # ==========================================
                # 🛠️ AJUSTE DA ORDEM DAS COLUNAS
                # ==========================================
                ordem_ideal = [ 
                    "Nome",
                    "Vulgo",
                    "RG",
                    "Foto",
                    "Atuação",
                    "Organização",
                    "Função",
                    "Situação",
                    "Rede social",
                    "Informe"
                ] 
                
                colunas_existentes = [col for col in ordem_ideal if col in df_notion.columns]
                colunas_extras = [col for col in df_notion.columns if col not in colunas_existentes]
                
                df_notion = df_notion[colunas_existentes + colunas_extras]
                # ==========================================

                # --- GAVETA DE FILTROS INTELIGENTES ---
                with st.expander("🔍 FILTROS AVANÇADOS", expanded=True):
                    col_atuacao = next((c for c in df_notion.columns if "ATUAÇÃO" in c.upper() or "ATUACAO" in c.upper()), None)
                    col_funcao = next((c for c in df_notion.columns if "FUNÇÃO" in c.upper() or "FUNCAO" in c.upper()), None)
                    col_org = next((c for c in df_notion.columns if "ORGANIZAÇÃO" in c.upper() or "ORGANIZACAO" in c.upper() or "ORCRIM" in c.upper()), None)
                    
                    df_filtrado_notion = df_notion.copy()
                    
                    c1, c2, c3 = st.columns(3)
                    
                    if col_atuacao:
                        lista_atuacao = df_notion[col_atuacao].dropna().unique().tolist()
                        sel_atuacao = c1.multiselect(f"Filtrar por {col_atuacao}:", lista_atuacao)
                        if sel_atuacao:
                            df_filtrado_notion = df_filtrado_notion[df_filtrado_notion[col_atuacao].isin(sel_atuacao)]
                            
                    if col_funcao:
                        lista_funcao = df_notion[col_funcao].dropna().unique().tolist()
                        sel_funcao = c2.multiselect(f"Filtrar por {col_funcao}:", lista_funcao)
                        if sel_funcao:
                            df_filtrado_notion = df_filtrado_notion[df_filtrado_notion[col_funcao].isin(sel_funcao)]
                            
                    if col_org:
                        lista_org = df_notion[col_org].dropna().unique().tolist()
                        sel_org = c3.multiselect(f"Filtrar por {col_org}:", lista_org)
                        if sel_org:
                            df_filtrado_notion = df_filtrado_notion[df_filtrado_notion[col_org].isin(sel_org)]
                            
                    if not any([col_atuacao, col_funcao, col_org]):
                        st.info("💡 Dica: Para os filtros aparecerem, certifique-se de que as colunas na sua tabela do Notion se chamem 'Atuação', 'Função' ou 'Organização'.")

                st.write("---")
                
                # ==========================================
                # 🖼️ MOTOR DE RENDERIZAÇÃO DE IMAGENS E LINKS
                # ==========================================
                config_colunas = {}
                for col in df_filtrado_notion.columns:
                    if "FOTO" in col.upper() or "IMAGEM" in col.upper():
                        config_colunas[col] = st.column_config.ImageColumn(col, width="small") 
                    elif df_filtrado_notion[col].astype(str).str.startswith("http").any():
                        config_colunas[col] = st.column_config.LinkColumn(col, display_text="🔗 Acessar")

                st.dataframe(df_filtrado_notion, column_config=config_colunas, use_container_width=True)
                
            else:
                st.warning("Verifique a conexão ou se a tabela da ÁREA 1 possui dados.")

        elif sub_menu_orcrim in ["ÁREA 2", "ÁREA 3", "ÁREA 4"]:
            st.header(f"🗺️ {sub_menu_orcrim}")
            st.info(f"O painel analítico da {sub_menu_orcrim} está em fase de estruturação de dados.")
            st.write("Aguardando integração das tabelas correspondentes.")
            
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
                st.success("Sistemas de IA prontos. Insira a lógica do chat aqui.")
            except:
                st.error("Erro na chave de API.")

    elif menu == "⚙️ CONFIGURAÇÕES":
        st.header("⚙️ Painel do Administrador")
        try:
            df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
            st.dataframe(df_u)
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")
