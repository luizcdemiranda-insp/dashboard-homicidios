import streamlit as st
import pandas as pd
import altair as alt
import hashlib
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E CSS
# =====================================================================
st.set_page_config(page_title="🛡️ Monitoramento de Homicídios", layout="wide")

# IDs das Planilhas
ID_PLANILHA_ACESSO = "1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw"
ID_PLANILHA_CRIMES = "1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc"

# --- CSS PERSONALIZADO (Design de Ontem) ---
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
# 3. INTERFACE DE ACESSO (CORRIGIDA)
# =====================================================================
def tela_acesso():
    col_esq, col_meio, col_dir = st.columns([1, 4, 1])
    with col_meio:
        st.markdown("<h1 style='text-align: center;'>🛡️ ACESSO AO SISTEMA</h1>", unsafe_allow_html=True)
        aba_login, aba_cadastro = st.tabs(["🔐 Entrar", "📝 Solicitar Cadastro"])
        
        with aba_login:
            mat_login = st.text_input("Matrícula", key="login_mat")
            senha_login = st.text_input("Senha", type="password", key="login_pass")
            
            if st.button("Acessar Painel"):
                try:
                    # Link de exportação direta da aba USUARIOS
                    url_users = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/gviz/tq?tqx=out:csv&sheet=USUARIOS"
                    df_users = pd.read_csv(url_users)
                    
                    # Padronização de colunas (Remove espaços e coloca em maiúsculo)
                    df_users.columns = [str(col).strip().upper() for col in df_users.columns]
                    
                    # Converte matrícula para string e limpa espaços
                    df_users['MATRICULA'] = df_users['MATRICULA'].astype(str).str.strip()
                    mat_login_limpa = str(mat_login).strip()
                    
                    # Criptografia da senha digitada
                    senha_hash = gerar_hash(senha_login)
                    
                    # Busca o usuário
                    user_match = df_users[(df_users['MATRICULA'] == mat_login_limpa) & 
                                         (df_users['SENHA'] == senha_hash)]
                    
                    if not user_match.empty:
                        # Verifica o Status (Aprovado / Pendente)
                        status = str(user_match.iloc[0]['STATUS']).strip().upper()
                        if status == 'APROVADO':
                            st.session_state.logado = True
                            st.session_state.user_nivel = user_match.iloc[0]['NIVEL']
                            st.session_state.user_nome = user_match.iloc[0]['NOME']
                            st.rerun()
                        else:
                            st.error(f"Acesso negado. Seu status atual é: {status}")
                    else:
                        st.error("Matrícula ou Senha inválidos.")
                except Exception as e:
                    st.error("⚠️ Erro de conexão com a base de usuários.")
                    st.info("Certifique-se de que a planilha de acesso está compartilhada como 'Qualquer pessoa com o link'.")

        with aba_cadastro:
            n_cad = st.text_input("Nome Completo", key="cad_nome")
            m_cad = st.text_input("Matrícula", key="cad_mat")
            s_cad = st.text_input("Defina uma Senha", type="password", key="cad_pass")
            
            if st.button("Enviar Solicitação"):
                if n_cad and m_cad and s_cad:
                    try:
                        df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
                        if str(m_cad) in df_u['MATRICULA'].astype(str).values:
                            st.warning("Esta matrícula já possui cadastro.")
                        else:
                            novo = pd.DataFrame([{
                                "NOME": n_cad, 
                                "MATRICULA": str(m_cad), 
                                "SENHA": gerar_hash(s_cad), 
                                "NIVEL": "Visitante", 
                                "STATUS": "Pendente"
                            }])
                            df_updated = pd.concat([df_users if 'df_users' in locals() else df_u, novo], ignore_index=True)
                            conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=df_updated)
                            st.success("Solicitação enviada com sucesso!")
                    except:
                        st.error("Erro ao gravar cadastro. Verifique as permissões da planilha.")

        with aba_cadastro:
            n_cad = st.text_input("Nome Completo", key="cad_nome")
            m_cad = st.text_input("Matrícula", key="cad_mat") # O KEY resolve o erro de ID duplicado
            s_cad = st.text_input("Defina uma Senha", type="password", key="cad_pass")
            if st.button("Enviar Solicitação"):
                if n_cad and m_cad and s_cad:
                    df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
                    if str(m_cad) in df_u['MATRICULA'].astype(str).values: st.warning("Matrícula já cadastrada.")
                    else:
                        novo = pd.DataFrame([{"NOME": n_cad, "MATRICULA": str(m_cad), "SENHA": gerar_hash(s_cad), "NIVEL": "Visitante", "STATUS": "Pendente"}])
                        conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=pd.concat([df_u, novo], ignore_index=True))
                        st.success("Solicitação enviada! Aguarde a liberação.")

# =====================================================================
# 4. FUNÇÃO REUTILIZÁVEL DO DASHBOARD (MÃE)
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
            grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_DIA}:N', sort='-x'), color='ANO:N').properties(height=350)
            st.altair_chart(grafico_dia, use_container_width=True)

    with col2:
        st.markdown("### 🗺️ POR CIRCUNSCRIÇÃO")
        if COL_CIRCUNSCRICAO:
            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
            grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(x='TOTAL:Q', y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x'), color='ANO:N').properties(height=350)
            st.altair_chart(grafico_circ, use_container_width=True)

# =====================================================================
# 5. LÓGICA DE NAVEGAÇÃO (LOGADO)
# =====================================================================
if not st.session_state.logado:
    tela_acesso()
else:
    st.sidebar.markdown(f"### Olá, {st.session_state.user_nome}")
    
    lista_menu = ["1. VISÃO GERAL", "2. CASOS POR ÁREA", "3. MOTIVAÇÃO / DELITO", "4. MODO ANALÍTICO", "5. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master":
        lista_menu.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("NAVEGAÇÃO", lista_menu)
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    df = carregar_dados()

    if menu == "1. VISÃO GERAL":
        st.header("📊 VISÃO GERAL")
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disp = sorted(df['ANO'].unique().tolist(), reverse=True)
        ano_sel = st.selectbox("ANO:", anos_disp)
        gerar_dashboard(df[df['ANO'] == ano_sel])

    elif menu == "2. CASOS POR ÁREA":
        st.header("🗺️ CASOS POR ÁREA")
        # Aqui você pode colar a lógica de filtros de ÁREA de ontem
        st.write("Selecione os filtros de área no Modo Comparativo.")

    elif menu == "5. ASSISTENTE IA":
        st.header("🤖 Analista Criminal Virtual")
        # Lógica da IA preservada
        api_key = st.sidebar.text_input("🔑 Chave Gemini:", type="password")
        if api_key:
            genai.configure(api_key=api_key)
            st.info("Sistemas de IA prontos.")
