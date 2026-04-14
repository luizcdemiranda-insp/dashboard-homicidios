import streamlit as st
import pandas as pd
import altair as alt
import hashlib
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# 1. CONFIGURAÇÕES INICIAIS E SEGURANÇA
# =====================================================================
st.set_page_config(page_title="Monitoramento Criminal", layout="wide")

# ID da sua planilha de ACESSO
ID_PLANILHA_ACESSO = "1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw"

# Função para criptografar senha
def gerar_hash(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# Inicialização do estado de login
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_nivel" not in st.session_state:
    st.session_state.user_nivel = None
if "user_nome" not in st.session_state:
    st.session_state.user_nome = None

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# =====================================================================
# 2. FUNÇÕES DE APOIO (DADOS)
# =====================================================================

@st.cache_data
def carregar_dados_crimes():
    # URL da sua planilha PRINCIPAL de crimes (a que usávamos antes)
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [str(col).strip().upper() for col in df.columns]
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    return df

# =====================================================================
# 3. INTERFACE DE LOGIN E CADASTRO
# =====================================================================

def tela_acesso():
    st.markdown("<h1 style='text-align: center;'>🛡️ SISTEMA DE INTELIGÊNCIA</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        aba_login, aba_cadastro = st.tabs(["🔐 Acessar", "📝 Solicitar Cadastro"])
        
        with aba_login:
            mat_login = st.text_input("Matrícula")
            senha_login = st.text_input("Senha", type="password")
            
            if st.button("Entrar"):
                # URL de exportação para CSV da planilha de USUÁRIOS
                url_users = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_ACESSO}/export?format=csv&gid=0"
                try:
                    df_users = pd.read_csv(url_users)
                    df_users['MATRICULA'] = df_users['MATRICULA'].astype(str)
                    
                    user_match = df_users[(df_users['MATRICULA'] == mat_login) & 
                                         (df_users['SENHA'] == gerar_hash(senha_login))]
                    
                    if not user_match.empty:
                        if user_match.iloc[0]['STATUS'] == 'Aprovado':
                            st.session_state.logado = True
                            st.session_state.user_nivel = user_match.iloc[0]['NIVEL']
                            st.session_state.user_nome = user_match.iloc[0]['NOME']
                            st.rerun()
                        else:
                            st.error("Seu acesso ainda está PENDENTE de aprovação.")
                    else:
                        st.error("Matrícula ou Senha incorretos.")
                except Exception as e:
                    st.error(f"Erro ao conectar na base de usuários: {e}")

        with aba_cadastro:
            nome_cad = st.text_input("Nome Completo")
            mat_cad = st.text_input("Matrícula Funcional")
            senha_cad = st.text_input("Defina uma Senha", type="password")
            
            if st.button("Solicitar Acesso"):
                if nome_cad and mat_cad and senha_cad:
                    try:
                        # Usando a conexão st.connection para gravar (update)
                        df_users = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
                        if str(mat_cad) in df_users['MATRICULA'].astype(str).values:
                            st.warning("Esta matrícula já possui cadastro ou solicitação.")
                        else:
                            novo_u = pd.DataFrame([{
                                "NOME": nome_cad, 
                                "MATRICULA": str(mat_cad),
                                "SENHA": gerar_hash(senha_cad), 
                                "NIVEL": "Visitante", 
                                "STATUS": "Pendente"
                            }])
                            df_updated = pd.concat([df_users, novo_u], ignore_index=True)
                            conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=df_updated)
                            st.success("Solicitação enviada! Aguarde a ativação.")
                    except Exception as e:
                        st.error(f"Erro ao salvar cadastro: {e}")
                else:
                    st.error("Preencha todos os campos.")

# =====================================================================
# 4. LOGICA PRINCIPAL (DASHBOARD)
# =====================================================================

if not st.session_state.logado:
    tela_acesso()
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.user_nome}")
    st.sidebar.write(f"Nível: **{st.session_state.user_nivel}**")
    
    opcoes_menu = ["1. VISÃO GERAL", "2. CASOS POR ÁREA", "3. MODO ANALÍTICO", "4. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master":
        opcoes_menu.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("Selecione a página:", opcoes_menu)
    
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- NAVEGAÇÃO ENTRE PÁGINAS ---
    # Aqui você deve inserir as lógicas das páginas que já fizemos
    if menu == "1. VISÃO GERAL":
        st.title("📊 Visão Geral do Monitoramento")
        # Insira o código dos cards e gráficos aqui...

    elif menu == "⚙️ CONFIGURAÇÕES":
        st.title("⚙️ Gestão de Acessos")
        # Código para o Master aprovar usuários...
        df_adm = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
        st.dataframe(df_adm)
