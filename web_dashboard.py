import streamlit as st
import pandas as pd
import altair as alt
import hashlib
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E ESTADO
# =====================================================================
st.set_page_config(page_title="Monitoramento Criminal v2.0", layout="wide")

ID_PLANILHA_ACESSO = "1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw"
ID_PLANILHA_CRIMES = "1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc"

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
# 2. FUNÇÕES DE CARREGAMENTO DE DADOS (CRIMES)
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
# 3. INTERFACE DE ACESSO (LOGIN/CADASTRO)
# =====================================================================
def tela_acesso():
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🛡️ SISTEMA DE INTELIGÊNCIA</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        aba_login, aba_cadastro = st.tabs(["🔐 Acessar", "📝 Solicitar Cadastro"])
        with aba_login:
            mat_login = st.text_input("Matrícula")
            senha_login = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                try:
                    url_users = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/export?format=csv&gid=0"
                    df_users = pd.read_csv(url_users)
                    df_users['MATRICULA'] = df_users['MATRICULA'].astype(str)
                    user_match = df_users[(df_users['MATRICULA'] == mat_login) & (df_users['SENHA'] == gerar_hash(senha_login))]
                    if not user_match.empty:
                        if user_match.iloc[0]['STATUS'] == 'Aprovado':
                            st.session_state.logado = True
                            st.session_state.user_nivel = user_match.iloc[0]['NIVEL']
                            st.session_state.user_nome = user_match.iloc[0]['NOME']
                            st.rerun()
                        else: st.error("Acesso PENDENTE de aprovação.")
                    else: st.error("Credenciais incorretas.")
                except Exception as e: st.error(f"Erro na base de usuários: {e}")

        with aba_cadastro:
            n_cad = st.text_input("Nome Completo")
            m_cad = st.text_input("Matrícula Funcional")
            s_cad = st.text_input("Senha")
            if st.button("Solicitar Cadastro"):
                df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
                if str(m_cad) in df_u['MATRICULA'].astype(str).values: st.warning("Matrícula já existe.")
                else:
                    novo = pd.DataFrame([{"NOME": n_cad, "MATRICULA": str(m_cad), "SENHA": gerar_hash(s_cad), "NIVEL": "Visitante", "STATUS": "Pendente"}])
                    conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=pd.concat([df_u, novo], ignore_index=True))
                    st.success("Enviado para aprovação!")

# =====================================================================
# 4. DASHBOARD PRINCIPAL (LOGADO)
# =====================================================================
if not st.session_state.logado:
    tela_acesso()
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.user_nome}")
    st.sidebar.info(f"Nível: {st.session_state.user_nivel}")
    
    opcoes = ["1. VISÃO GERAL", "2. CASOS POR ÁREA", "3. MODO ANALÍTICO", "4. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master": opcoes.append("⚙️ CONFIGURAÇÕES")
    menu = st.sidebar.radio("Navegação:", opcoes)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    df = carregar_dados()

    # --- PÁGINA 1: VISÃO GERAL ---
    if menu == "1. VISÃO GERAL":
        st.title("📊 Visão Geral")
        anos = sorted(df['ANO'].dropna().unique().cast(int), reverse=True)
        ano_sel = st.selectbox("Ano de Referência", anos)
        df_ano = df[df['ANO'] == ano_sel]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Ocorrências", len(df_ano))
        # Adicione aqui os demais cards que criamos...
        
        grafico = alt.Chart(df_ano).mark_bar().encode(x='count()', y=alt.Y('MUNICIPIO:N', sort='-x'))
        st.altair_chart(grafico, use_container_width=True)

    # --- PÁGINA 2: ÁREA ---
    elif menu == "2. CASOS POR ÁREA":
        st.title("📍 Análise por Área")
        municipios = sorted(df['MUNICIPIO'].unique())
        mun_sel = st.multiselect("Selecione os Municípios", municipios, default=municipios[:3])
        df_mun = df[df['MUNICIPIO'].isin(mun_sel)]
        st.line_chart(df_mun.groupby(['ANO', 'MUNICIPIO']).size().unstack().fillna(0))

    # --- PÁGINA 4: ASSISTENTE IA (SISTEMA RECUPERADO) ---
    elif menu == "4. ASSISTENTE IA":
        st.header("🤖 Analista Criminal Virtual")
        api_key = st.sidebar.text_input("Chave API Gemini:", type="password")
        
        if not api_key:
            st.warning("Insira a chave API para ativar a IA.")
        else:
            try:
                genai.configure(api_key=api_key.strip())
                if "modelo_oficial" not in st.session_state:
                    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    st.session_state.modelo_oficial = next((m for m in modelos if "1.5-flash" in m), modelos[0])
                
                model = genai.GenerativeModel(st.session_state.modelo_oficial)
                if "chat" not in st.session_state:
                    st.session_state.chat = model.start_chat(history=[])
                    st.session_state.mensagens = [{"role": "assistant", "content": "Análise pronta. O que deseja saber?"}]

                for m in st.session_state.mensagens:
                    with st.chat_message(m["role"]): st.markdown(m["content"])

                if prompt := st.chat_input("Dúvida técnica sobre os dados?"):
                    st.session_state.mensagens.append({"role": "user", "content": prompt})
                    with st.chat_message("user"): st.markdown(prompt)
                    
                    with st.spinner("Analisando..."):
                        ctx = f"Dados: {len(df)} registros. Colunas: {list(df.columns)}"
                        resp = st.session_state.chat.send_message(f"{ctx}\n\nPergunta: {prompt}")
                        st.session_state.mensagens.append({"role": "assistant", "content": resp.text})
                        with st.chat_message("assistant"): st.markdown(resp.text)
            except Exception as e: st.error(f"Erro IA: {e}")

    # --- PÁGINA ⚙️ CONFIGURAÇÕES (MASTER) ---
    elif menu == "⚙️ CONFIGURAÇÕES":
        st.title("⚙️ Gestão de Usuários")
        df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
        st.subheader("Solicitações Pendentes")
        pendentes = df_u[df_u['STATUS'] == 'Pendente']
        if not pendentes.empty:
            for i, r in pendentes.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{r['NOME']}** (Mat: {r['MATRICULA']})")
                if col2.button("Aprovar", key=f"apr_{i}"):
                    df_u.at[i, 'STATUS'] = 'Aprovado'
                    conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=df_u)
                    st.rerun()
        st.write("---")
        st.dataframe(df_u)
