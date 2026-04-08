import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CABEÇALHO COM LOGOMARCAS ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])

with col_esq:
    try:
        st.image("logo1.png", width=150)
    except:
        st.write("Logo 1")

with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ Visão Geral de Monitoramento</h1>", unsafe_allow_html=True)

with col_dir:
    try:
        st.image("logo2.png", width=150)
    except:
        st.write("Logo 2")

st.write("---")

# 2. Menu Lateral Atualizado (Botões visíveis simultaneamente)
st.sidebar.markdown("### Menu de Navegação")
menu = st.sidebar.radio(
    "", # Deixei o título em branco pois já tem o markdown acima
    ["1. Visão Geral (Macro)",
     "2. Casos por Área",
     "3. Motivação / Delito"]
)

# 3. Função de Carga de Dados
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    
    # Detetive de Datas
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    # Padroniza todas as colunas para MAIÚSCULO para evitar erros de digitação
    df.columns = [str(col).strip().upper() for col in df.columns]
    
    return df

# =====================================================================
# 4. PÁGINA: VISÃO GERAL (MACRO)
# =====================================================================
if menu == "1. Visão Geral (Macro)":
    
    with st.spinner("Sincronizando banco de dados..."):
        try:
            df = carregar_dados()
            sucesso_dados = True
        except Exception as e:
            st.error(f"Erro ao baixar a planilha: {e}")
            sucesso_dados = False

    if sucesso_dados:
        # Preparar os anos disponíveis
        df = df.dropna(subset=['ANO'])
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

        # --- CONTROLES DE FILTRO ---
        st.subheader("Filtros de Análise")
        
        modo_analise = st.radio(
            "Selecione o formato da análise:",
            ["Análise Individual (1 ano)", "Análise Comparativa (Múltiplos anos)"],
            horizontal=True
        )

        anos_selecionados = []

        if modo_analise == "Análise Individual (1 ano)":
            ano_escolhido = st.selectbox("Selecione o Ano:", anos_disponiveis)
            anos_selecionados = [ano_escolhido]
        else:
            anos_selecionados = st.multiselect("Selecione os Anos para comparar:", anos_disponiveis, default=anos_disponiveis[:2])

        st.write("---")

        if len(anos_selecionados) > 0:
            df_filtrado = df[df['ANO'].isin(anos_selecionados)]

            # --- VERIFICAÇÃO DE COLUNAS AJUSTADA ---
            COL_DIA = "DIA SEMANA" if "DIA SEMANA" in df.columns else None
            COL_CIRCUNSCRICAO = "CIRCUNSCRIÇÃO" if "CIRCUNSCRIÇÃO" in df.columns else None
            COL_ORCRIM = "ORCRIM" if "ORCRIM" in df.columns else None

            # --- ANÁLISE 1: QUANTIDADE DE PROCEDIMENTOS ---
            total_procedimentos = len(df_filtrado)
            st.metric(label="📊 Total de Procedimentos (Ocorrências) no período", value=f"{total_procedimentos:,}".replace(',', '.'))
            
            st.write("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            # --- ANÁLISE 2: DIA DA SEMANA ---
            with col1:
                st.markdown("### 📅 Crimes por Dia da Semana")
                if COL_DIA:
                    tabela_dia = pd.crosstab(df_filtrado[COL_DIA], df_filtrado['ANO'])
                    
                    # Ordena do dia com MAIS crimes para o com MENOS crimes
                    tabela_dia['Total'] = tabela_dia.sum(axis=1)
                    tabela_dia = tabela_dia.sort_values('Total', ascending=False).drop(columns=['Total'])
                    
                    st.bar_chart(tabela_dia)
                else:
                    st.warning("Coluna 'DIA SEMANA' não encontrada.")

            # --- ANÁLISE 3: CIRCUNSCRIÇÃO (Ordem Decrescente) ---
            with col2:
                st.markdown("### 🗺️ Crimes por Circunscrição")
                if COL_CIRCUNSCRICAO:
                    tabela_circ = pd.crosstab(df_filtrado[COL_CIRCUNSCRICAO], df_filtrado['ANO'])
                    
                    # Lógica para Ordenação Decrescente
                    tabela_circ['Total'] = tabela_circ.sum(axis=1)
                    tabela_circ = tabela_circ.sort_values('Total', ascending=False).drop(columns=['Total'])
                    
                    st.bar_chart(tabela_circ)
                else:
                    st.warning("Coluna 'CIRCUNSCRIÇÃO' não encontrada.")

            st.write("<br>", unsafe_allow_html=True)

            # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM ---
            st.markdown("### ⚖️ Distribuição de ORCRIM")
            if COL_ORCRIM:
                # Padronizar o texto da coluna para agrupar certinho
                df_filtrado.loc[:, COL_ORCRIM] = df_filtrado[COL_ORCRIM].astype(str).str.strip().str.upper()
                
                # Vamos remover da contagem caso haja linhas em branco preenchidas como "NAN"
                df_orcrim = df_filtrado[df_filtrado[COL_ORCRIM] != "NAN"]
                
                tabela_orcrim = pd.crosstab(df_orcrim[COL_ORCRIM], df_orcrim['ANO'])
                
                # Ordenar de forma decrescente os tipos de ORCRIM
                tabela_orcrim['Total'] = tabela_orcrim.sum(axis=1)
                tabela_orcrim = tabela_orcrim.sort_values('Total', ascending=False).drop(columns=['Total'])
                
                st.bar_chart(tabela_orcrim)
            else:
                st.warning("Coluna 'ORCRIM' não encontrada.")

        else:
            st.info("Por favor, selecione pelo menos um ano para gerar as análises.")

# --- Outras Páginas ---
elif menu == "2. Casos por Área":
    st.header("🗺️ Casos por Área de Policiamento")
    st.info("Página em construção...")

elif menu == "3. Motivação / Delito":
    st.header("🔍 Detalhamento de Motivação")
    st.info("Página em construção...")
