import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CABEÇALHO COM LOGOMARCAS ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])

with col_esq:
    # Lembre-se de usar o nome correto da imagem que você salvou na pasta
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

# 2. Menu Lateral Atualizado
menu = st.sidebar.selectbox(
    "Navegação",
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
    
    # Padroniza todas as colunas para MAIÚSCULO para evitar erros de digitação (ex: Orcrim vs ORCRIM)
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
        anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True) # Ordem decrescente (mais recente primeiro)

        # --- CONTROLES DE FILTRO (No topo da página) ---
        st.subheader("Filtros de Análise")
        
        # Opção Radio para escolher o tipo de análise
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

        # Se houver ano(s) selecionado(s), prosseguimos com os gráficos
        if len(anos_selecionados) > 0:
            # Filtramos a base inteira para deixar só os anos selecionados
            df_filtrado = df[df['ANO'].isin(anos_selecionados)]

            # --- VERIFICAÇÃO DE COLUNAS ---
            # Aqui você pode mudar o nome se na sua planilha estiver diferente!
            COL_PROCEDIMENTO = "PROCEDIMENTO" if "PROCEDIMENTO" in df.columns else None
            COL_DIA = "DIA DA SEMANA" if "DIA DA SEMANA" in df.columns else None
            COL_CIRCUNSCRICAO = "CIRCUNSCRIÇÃO" if "CIRCUNSCRIÇÃO" in df.columns else None
            COL_ORCRIM = "ORCRIM" if "ORCRIM" in df.columns else "MOTIVAÇÃO" # Tenta achar ORCRIM, se não, tenta MOTIVAÇÃO

            # --- ANÁLISE 1: QUANTIDADE DE PROCEDIMENTOS (Destaque) ---
            # Conta o número de linhas (ocorrências) filtradas
            total_procedimentos = len(df_filtrado)
            st.metric(label="📊 Total de Procedimentos (Ocorrências) no período", value=f"{total_procedimentos:,}".replace(',', '.'))
            
            # --- PREPARAÇÃO DOS GRÁFICOS (Layout em Colunas) ---
            st.write("<br>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)

            # --- ANÁLISE 2: DIA DA SEMANA ---
            with col1:
                st.markdown("### 📅 Crimes por Dia da Semana")
                if COL_DIA:
                    # Agrupa Dia da Semana x Ano e conta as linhas
                    tabela_dia = pd.crosstab(df_filtrado[COL_DIA], df_filtrado['ANO'])
                    
                    # Para organizar de Seg a Dom, precisaria de uma lista manual, 
                    # mas o Streamlit já desenha bonito.
                    st.bar_chart(tabela_dia)
                else:
                    st.warning("Coluna 'DIA DA SEMANA' não encontrada na planilha.")

            # --- ANÁLISE 3: CIRCUNSCRIÇÃO ---
            with col2:
                st.markdown("### 🗺️ Crimes por Circunscrição")
                if COL_CIRCUNSCRICAO:
                    tabela_circ = pd.crosstab(df_filtrado[COL_CIRCUNSCRICAO], df_filtrado['ANO'])
                    st.bar_chart(tabela_circ)
                else:
                    st.warning("Coluna 'CIRCUNSCRIÇÃO' não encontrada na planilha.")

            st.write("<br>", unsafe_allow_html=True)

            # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM ---
            st.markdown("### ⚖️ Distribuição de ORCRIM (Organização Criminosa / Motivação)")
            if COL_ORCRIM in df.columns:
                tabela_orcrim = pd.crosstab(df_filtrado[COL_ORCRIM], df_filtrado['ANO'])
                # Gráfico de área/barras focado nas motivações
                st.bar_chart(tabela_orcrim)
            else:
                st.warning(f"Coluna 'ORCRIM' ou 'MOTIVAÇÃO' não encontrada. Verifique o nome exato na planilha.")

        else:
            st.info("Por favor, selecione pelo menos um ano para gerar as análises.")


# --- Outras Páginas em Construção ---
elif menu == "2. Casos por Área":
    st.header("🗺️ Casos por Área de Policiamento")
    st.info("Página em construção...")

elif menu == "3. Motivação / Delito":
    st.header("🔍 Detalhamento de Motivação")
    st.info("Página em construção...")
