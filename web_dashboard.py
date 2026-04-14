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

# Substitua pelo ID da sua nova planilha de ACESSO
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
# 2. FUNÇÕES DE APOIO (DADOS E LOGIN)
# =====================================================================

def carregar_dados_seguros():
    # Aqui você coloca a sua função carregar_dados() que já funciona
    # Aquela que lê a planilha de crimes principal
    pass 

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
                # Busca na planilha de usuários
                # Substitua o comando de leitura por este:
                    url_users = f"https://docs.google.com/spreadsheets/d/1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw/export?format=csv&gid=0"
                   df_users = pd.read_csv(url_users)
                # Garante que matrícula seja string para comparar
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
                        st.error("Seu acesso ainda está PENDENTE de aprovação pelo Administrador.")
                else:
                    st.error("Matrícula ou Senha incorretos.")

        with aba_cadastro:
            nome_cad = st.text_input("Nome Completo")
            mat_cad = st.text_input("Matrícula Funcional")
            senha_cad = st.text_input("Defina uma Senha", type="password")
            
            if st.button("Solicitar Acesso"):
                if nome_cad and mat_cad and senha_cad:
                    df_users = conn.read(spreadsheet="1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw", worksheet="USUARIOS")
                    if mat_cad in df_users['MATRICULA'].astype(str).values:
                        st.warning("Esta matrícula já possui solicitação ou cadastro.")
                    else:
                        novo_u = pd.DataFrame([{
                            "NOME": nome_cad, "MATRICULA": str(mat_cad),
                            "SENHA": gerar_hash(senha_cad), "NIVEL": "Visitante", "STATUS": "Pendente"
                        }])
                        df_updated = pd.concat([df_users, novo_u], ignore_index=True)
                        conn.update(spreadsheet=1B_THJwz9AQ-UFxwYmXXUzA70BGzPTwNBp-7YlSBFrDw, worksheet="USUARIOS", data=df_updated)
                        st.success("Solicitação enviada! Aguarde a ativação pelo Administrador.")
                else:
                    st.error("Preencha todos os campos.")

# =====================================================================
# 4. LOGICA PRINCIPAL (DASHBOARD)
# =====================================================================

if not st.session_state.logado:
    tela_acesso()
else:
    # --- BARRA LATERAL ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.sidebar.title(f"Bem-vindo, {st.session_state.user_nome}")
    st.sidebar.write(f"Nível: **{st.session_state.user_nivel}**")
    
    # Opções do Menu baseadas no Nível
    opcoes_menu = ["1. VISÃO GERAL", "2. CASOS POR ÁREA", "3. MODO ANALÍTICO", "4. ASSISTENTE IA"]
    if st.session_state.user_nivel == "Master":
        opcoes_menu.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("Selecione a página:", opcoes_menu)
    
    if st.sidebar.button("Sair do Sistema"):
        st.session_state.logado = False
        st.rerun()

    # --- NAVEGAÇÃO ENTRE PÁGINAS ---
    
    if menu == "1. VISÃO GERAL":
        st.title("📊 Visão Geral do Monitoramento")
        # COLOQUE AQUI O SEU CÓDIGO DA VISÃO GERAL...

    elif menu == "2. CASOS POR ÁREA":
        st.title("📍 Análise Regional")
        # COLOQUE AQUI O SEU CÓDIGO DE CASOS POR ÁREA...

    elif menu == "⚙️ CONFIGURAÇÕES":
        st.title("⚙️ Painel do Administrador (Master)")
        # AQUI VAI O CÓDIGO DE APROVAÇÃO QUE TE MANDEI ANTES
        # (Ler a planilha, mostrar pendentes e botões de Aprovar/Rejeitar)

    elif menu == "4. ASSISTENTE IA":
        # AQUI VAI O CÓDIGO DO ANALISTA VIRTUAL...
        pass
