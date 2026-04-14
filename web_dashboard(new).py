import streamlit as st
import pandas as pd
import altair as alt
import hashlib
from streamlit_gsheets import GSheetsConnection

# =====================================================================
# 1. CONFIGURAÇÕES, SEGURANÇA E ESTADO
# =====================================================================
st.set_page_config(page_title="Monitoramento Criminal", layout="wide")

# IDs das suas planilhas
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
# 2. FUNÇÃO DE CARREGAMENTO (DADOS DE CRIMES)
# =====================================================================
@st.cache_data(ttl=600)
def carregar_dados():
    url = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA_CRIMES}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df

# =====================================================================
# 3. TELA DE ACESSO (LOGIN / CADASTRO)
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
                    
                    user_match = df_users[(df_users['MATRICULA'] == mat_login) & 
                                         (df_users['SENHA'] == gerar_hash(senha_login))]
                    
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
            s_cad = st.text_input("Defina uma Senha", type="password")
            if st.button("Enviar Solicitação"):
                if n_cad and m_cad and s_cad:
                    df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
                    if str(m_cad) in df_u['MATRICULA'].astype(str).values: st.warning("Matrícula já cadastrada.")
                    else:
                        novo = pd.DataFrame([{"NOME": n_cad, "MATRICULA": str(m_cad), "SENHA": gerar_hash(s_cad), "NIVEL": "Visitante", "STATUS": "Pendente"}])
                        conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=pd.concat([df_u, novo], ignore_index=True))
                        st.success("Solicitação enviada! Aguarde a ativação.")

# =====================================================================
# 4. DASHBOARD (O QUE APARECE APÓS O LOGIN)
# =====================================================================
if not st.session_state.logado:
    tela_acesso()
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state.user_nome}")
    st.sidebar.write(f"Nível: **{st.session_state.user_nivel}**")
    
    opcoes = ["1. VISÃO GERAL", "2. MOTIVAÇÃO / DELITO"]
    if st.session_state.user_nivel == "Master":
        opcoes.append("⚙️ CONFIGURAÇÕES")
        
    menu = st.sidebar.radio("Navegação:", opcoes)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PÁGINA 1: VISÃO GERAL (Placeholder ou seu código anterior) ---
    if menu == "1. VISÃO GERAL":
        st.title("📊 Visão Geral")
        st.write("Bem-vindo ao sistema de monitoramento.")

    # --- PÁGINA: MOTIVAÇÃO / DELITO (SEU CÓDIGO RECUPERADO) ---
    elif menu == "2. MOTIVAÇÃO / DELITO":
        st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO E DELITO")
        
        try:
            df = carregar_dados()
            # Tratamento de data para extrair ano caso não exista
            if 'ANO' not in df.columns and 'DATA' in df.columns:
                df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
                
            df = df.dropna(subset=['ANO'])
            df['ANO'] = df['ANO'].astype(int).astype(str)
            anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

            st.subheader("FILTROS DE ANÁLISE")
            modo_analise = st.radio("SELECIONE O FORMATO:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"], key="modo_motivo")

            anos_selecionados = []
            if modo_analise == "ANÁLISE INDIVIDUAL":
                col_drop, _ = st.columns([2, 8]) 
                ano_escolhido = col_drop.selectbox("SELECIONE O ANO:", anos_disponiveis, key="ano_motivo_ind")
                anos_selecionados = [ano_escolhido]
            else:
                st.write("**SELECIONE OS ANOS:**")
                col_btn1, col_btn2, _ = st.columns([2, 2, 6])
                if col_btn1.button("✓ Todos", key="all_mot"):
                    for a in anos_disponiveis: st.session_state[f"chk_mot_{a}"] = True
                if col_btn2.button("✗ Limpar", key="none_mot"):
                    for a in anos_disponiveis: st.session_state[f"chk_mot_{a}"] = False

                for a in anos_disponiveis:
                    if f"chk_mot_{a}" not in st.session_state: st.session_state[f"chk_mot_{a}"] = True
                
                cols = st.columns(min(len(anos_disponiveis), 8) or 1, gap="small")
                for i, a in enumerate(anos_disponiveis):
                    cols[i % 8].checkbox(a, key=f"chk_mot_{a}")
                anos_selecionados = [a for a in anos_disponiveis if st.session_state.get(f"chk_mot_{a}", False)]

            if anos_selecionados:
                df_motivo = df[df['ANO'].isin(anos_selecionados)].copy()
                
                col_motivo = next((c for c in df_motivo.columns if "MOTIVO" in str(c) or "MOTIVAÇÃO" in str(c)), None)
                col_meio = next((c for c in df_motivo.columns if "MEIO" in str(c) or "INSTRUMENTO" in str(c)), None)

                st.write("---")
                
                if not col_motivo and not col_meio:
                    st.warning("⚠️ Colunas de 'MOTIVO' ou 'MEIO' não identificadas.")
                else:
                    col_esq, col_dir = st.columns(2)

                    with col_esq:
                        st.markdown("### 🎯 PRINCIPAIS MOTIVAÇÕES")
                        if col_motivo:
                            raw_motivo = df_motivo.loc[:, col_motivo]
                            dados_motivo = raw_motivo.astype(str).str.strip().str.upper()
                            dados_motivo = dados_motivo[~dados_motivo.isin(["NAN", "NONE", "", "-", " ", "0", "0.0"])]
                            
                            if not dados_motivo.empty:
                                tabela_motivo = dados_motivo.value_counts().reset_index()
                                tabela_motivo.columns = ['MOTIVO', 'TOTAL']
                                grafico_motivo = alt.Chart(tabela_motivo.head(10)).mark_arc(innerRadius=50).encode(
                                    theta="TOTAL:Q", 
                                    color=alt.Color("MOTIVO:N", legend=alt.Legend(title="Motivo")),
                                    tooltip=['MOTIVO', 'TOTAL']
                                ).properties(height=400)
                                st.altair_chart(grafico_motivo, use_container_width=True)
                            else: st.info("Dados de motivação vazios.")

                    with col_dir:
                        st.markdown("### 🔪 MEIO EMPREGADO")
                        if col_meio:
                            raw_meio = df_motivo.loc[:, col_meio]
                            dados_meio = raw_meio.astype(str).str.strip().str.upper()
                            dados_meio = dados_meio[~dados_meio.isin(["NAN", "NONE", "", "-", " ", "0", "0.0"])]
                            
                            if not dados_meio.empty:
                                tabela_meio = dados_meio.value_counts().reset_index()
                                tabela_meio.columns = ['MEIO', 'TOTAL']
                                grafico_meio = alt.Chart(tabela_meio.head(10)).mark_bar(color='#ff4b4b').encode(
                                    x='TOTAL:Q', y=alt.Y('MEIO:N', sort='-x', title=''), tooltip=['MEIO', 'TOTAL']
                                ).properties(height=400)
                                st.altair_chart(grafico_meio, use_container_width=True)
                            else: st.info("Dados de meio empregado vazios.")

        except Exception as e:
            st.error(f"Erro técnico: {e}")

    # --- PÁGINA: CONFIGURAÇÕES (GESTÃO DE USUÁRIOS) ---
    elif menu == "⚙️ CONFIGURAÇÕES":
        st.title("⚙️ Painel Master")
        df_u = conn.read(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS")
        pendentes = df_u[df_u['STATUS'] == 'Pendente']
        
        if not pendentes.empty:
            for i, r in pendentes.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{r['NOME']}** (Mat: {r['MATRICULA']})")
                if c2.button("Aprovar", key=f"ap_{i}"):
                    df_u.at[i, 'STATUS'] = 'Aprovado'
                    conn.update(spreadsheet=ID_PLANILHA_ACESSO, worksheet="USUARIOS", data=df_u)
                    st.rerun()
        st.dataframe(df_u)
