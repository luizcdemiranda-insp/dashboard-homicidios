import streamlit as st
import pandas as pd
import altair as alt

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    div[role="radiogroup"] > label > div:first-child { display: none; }
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
    div[role="radiogroup"] > label:hover {
        background-color: #ff4b4b;
        color: white;
        border-color: #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
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

# 2. Menu Lateral
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
    
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    # Padroniza todas as colunas do cabeçalho para MAIÚSCULO
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
            df_filtrado = df[df['ANO'].isin(anos_selecionados)].copy()

            # --- BUSCA DE COLUNAS ---
            COL_DIA = next((c for c in df.columns if "DIA" in c and "SEMANA" in c), None)
            COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in c), None)
            
            # O SEGREDO DA COLUNA AE: Pegamos a coluna pelo índice exato (30 = AE)
            # Se a planilha tiver menos que 31 colunas, o código não quebra, ele apenas avisa.
            if len(df.columns) >= 31:
                COL_ORCRIM = df.columns[30] 
            else:
                COL_ORCRIM = None

            # --- ANÁLISE 1: QUANTIDADE DE PROCEDIMENTOS ---
            total_procedimentos = len(df_filtrado)
            st.metric(label="📊 TOTAL DE PROCEDIMENTOS (OCORRÊNCIAS) NO PERÍODO", value=f"{total_procedimentos:,}".replace(',', '.'))
            st.write("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)

            # --- ANÁLISE 2: DIA DA SEMANA ---
            with col1:
                st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                if COL_DIA:
                    tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
                    grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''),
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

            # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM (COLUNA AE) ---
            st.markdown("### ⚖️ DISTRIBUIÇÃO DE ORCRIM")
            if COL_ORCRIM:
                # Limpeza de texto: tira espaços e deixa tudo em maiúsculo
                df_filtrado[COL_ORCRIM] = df_filtrado[COL_ORCRIM].astype(str).str.strip().str.upper()
                
                # Vamos remover o que estiver vazio ('NAN', 'NONE', '')
                df_orcrim = df_filtrado[~df_filtrado[COL_ORCRIM].isin(["NAN", "NONE", "", "NA"])]
                
                if len(df_orcrim) > 0:
                    tabela_orcrim = df_orcrim.groupby([COL_ORCRIM, 'ANO']).size().reset_index(name='TOTAL')
                    
                    grafico_orcrim = alt.Chart(tabela_orcrim).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_ORCRIM}:N', sort='-x', title=''),
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=[COL_ORCRIM, 'ANO', 'TOTAL']
                    ).properties(height=300)
                    
                    st.altair_chart(grafico_orcrim, use_container_width=True)
                else:
                    st.info("Nenhuma classificação de ORCRIM encontrada para os anos selecionados.")
            else:
                st.warning("A coluna AE (índice 30) não foi encontrada na planilha exportada.")

        else:
            st.info("POR FAVOR, SELECIONE PELO MENOS UM ANO PARA GERAR AS ANÁLISES.")

# --- Outras Páginas ---
elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    st.info("Página em construção...")

elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")
