import streamlit as st
import pandas as pd
import altair as alt # Nova ferramenta para gráficos mais precisos

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CSS PERSONALIZADO (Para transformar o Radio em Botões Elegantes) ---
st.markdown("""
    <style>
    /* Esconde as bolinhas do Radio */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    
    /* Transforma o texto em um botão estilo bloco */
    div[role="radiogroup"] > label {
        background-color: #1E2130;
        border: 1px solid #4a4f63;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 8px;
        text-align: center;
        font-weight: bold;
        transition: 0.3s;
    }
    
    /* Efeito de passar o mouse */
    div[role="radiogroup"] > label:hover {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO COM LOGOMARCAS ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])

with col_esq:
    try:
        st.image("logo1.png", width=150)
    except:
        st.write("")

with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ VISÃO GERAL DE MONITORAMENTO</h1>", unsafe_allow_html=True)

with col_dir:
    try:
        st.image("logo2.png", width=150)
    except:
        st.write("")

st.write("---")

# 2. Menu Lateral (Agora esteticamente como botões e em CAIXA ALTA)
st.sidebar.markdown("### NAVEGAÇÃO")
menu = st.sidebar.radio(
    "", 
    ["1. VISÃO GERAL (MACRO)",
     "2. CASOS POR ÁREA",
     "3. MOTIVAÇÃO / DELITO"]
)

# 3. Função de Carga de Dados
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    
    # Detetive de Datas
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    # Padroniza todas as colunas para MAIÚSCULO
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df

# =====================================================================
# 4. PÁGINA: VISÃO GERAL (MACRO)
# =====================================================================
if menu == "1. VISÃO GERAL (MACRO)":
    
    with st.spinner("Sincronizando banco de dados..."):
        try:
            df = carregar_dados()
            sucesso_dados = True
        except Exception as e:
            st.error(f"Erro ao baixar a planilha: {e}")
            sucesso_dados = False

    if sucesso_dados:
        df = df.dropna(subset=['ANO'])
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

        # --- CONTROLES DE FILTRO ---
        st.subheader("FILTROS DE ANÁLISE")
        
        modo_analise = st.radio(
            "SELECIONE O FORMATO DA ANÁLISE:",
            ["ANÁLISE INDIVIDUAL (1 ANO)", "ANÁLISE COMPARATIVA (MÚLTIPLOS ANOS)"],
            horizontal=True
        )

        anos_selecionados = []

        if modo_analise == "ANÁLISE INDIVIDUAL (1 ANO)":
            ano_escolhido = st.selectbox("SELECIONE O ANO:", anos_disponiveis)
            anos_selecionados = [ano_escolhido]
        else:
            anos_selecionados = st.multiselect("SELECIONE OS ANOS PARA COMPARAR:", anos_disponiveis, default=anos_disponiveis[:2])

        st.write("---")

        if len(anos_selecionados) > 0:
            df_filtrado = df[df['ANO'].isin(anos_selecionados)]

            # --- O NOVO DETETIVE IMPLACÁVEL ---
            # Ele procura "pedaços" da palavra na coluna, ignorando espaços extras
            COL_DIA = next((c for c in df.columns if "DIA" in c and "SEMANA" in c), None)
            COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in c), None)
            COL_ORCRIM = next((c for c in df.columns if "ORCRIM" in c), None)

            # --- ANÁLISE 1: QUANTIDADE DE PROCEDIMENTOS ---
            total_procedimentos = len(df_filtrado)
            st.metric(label="📊 TOTAL DE PROCEDIMENTOS (OCORRÊNCIAS) NO PERÍODO", value=f"{total_procedimentos:,}".replace(',', '.'))
            st.write("<br>", unsafe_allow_html=True)
            
            # Divide a tela em duas colunas para os gráficos
            col1, col2 = st.columns(2)

            # --- ANÁLISE 2: DIA DA SEMANA ---
            with col1:
                st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                if COL_DIA:
                    # Conta os casos
                    tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
                    
                    # Gráfico Altair para forçar ordem de barras
                    grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''), # sort='-x' garante do maior pro menor
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=[COL_DIA, 'ANO', 'TOTAL']
                    ).properties(height=350)
                    
                    st.altair_chart(grafico_dia, use_container_width=True)
                else:
                    st.warning("Coluna de Dia da Semana não encontrada.")

            # --- ANÁLISE 3: CIRCUNSCRIÇÃO ---
            with col2:
                st.markdown("### 🗺️ CRIMES POR CIRCUNSCRIÇÃO")
                if COL_CIRCUNSCRICAO:
                    tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
                    
                    # Gráfico Altair com ordem rigorosa
                    grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x', title=''),
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=[COL_CIRCUNSCRICAO, 'ANO', 'TOTAL']
                    ).properties(height=350)
                    
                    st.altair_chart(grafico_circ, use_container_width=True)
                else:
                    st.warning("Coluna de Circunscrição não encontrada.")

            st.write("<br>", unsafe_allow_html=True)

            # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM ---
            st.markdown("### ⚖️ DISTRIBUIÇÃO DE ORCRIM")
            if COL_ORCRIM:
                # Limpeza rigorosa do texto para padronizar EM INVESTIGAÇÃO, TRÁFICO, etc.
                df_filtrado = df_filtrado.copy()
                df_filtrado[COL_ORCRIM] = df_filtrado[COL_ORCRIM].astype(str).str.strip().str.upper()
                
                # Exclui linhas vazias identificadas como "NAN"
                df_orcrim = df_filtrado[df_filtrado[COL_ORCRIM] != "NAN"]
                
                tabela_orcrim = df_orcrim.groupby([COL_ORCRIM, 'ANO']).size().reset_index(name='TOTAL')
                
                grafico_orcrim = alt.Chart(tabela_orcrim).mark_bar().encode(
                    x=alt.X('TOTAL:Q', title='Ocorrências'),
                    y=alt.Y(f'{COL_ORCRIM}:N', sort='-x', title=''),
                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                    tooltip=[COL_ORCRIM, 'ANO', 'TOTAL']
                ).properties(height=300)
                
                st.altair_chart(grafico_orcrim, use_container_width=True)
            else:
                st.warning("Coluna ORCRIM não encontrada.")

        else:
            st.info("POR FAVOR, SELECIONE PELO MENOS UM ANO PARA GERAR AS ANÁLISES.")

# --- Outras Páginas ---
elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    st.info("Página em construção...")

elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")
