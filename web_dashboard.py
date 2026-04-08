import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CABEÇALHO COM LOGOMARCAS (USANDO ARQUIVOS LOCAIS) ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])

# Logomarca 1 - Canto Superior Esquerdo
with col_esq:
    # Coloque aqui o nome exato do arquivo que está na sua pasta
    st.image("logo1.png", width=150)

# Título Centralizado
with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ Monitoramento de Homicídios</h1>", unsafe_allow_html=True)

# Logomarca 2 - Canto Superior Direito
with col_dir:
    # Coloque aqui o nome exato do arquivo que está na sua pasta
    st.image("logo2.png", width=150)

st.write("---") # Linha divisória

# 2. Menu Lateral
menu = st.sidebar.selectbox(
    "Navegação",
    ["1. Ocorrências por Município",
     "2. Ocorrências por Dia da Semana",
     "3. Casos por Área",
     "4. Motivação / Delito"]
)

# 3. Função de Carga de Dados (Cache)
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    return df

# 4. Conteúdo das Páginas
if menu == "1. Ocorrências por Município":
    st.header("📍 Análise por Município")
    
    try:
        with st.spinner("Buscando dados..."):
            df = carregar_dados()

        if 'MUNICÍPIO' not in df.columns:
            st.error("Coluna 'MUNICÍPIO' não encontrada.")
        else:
            df = df.dropna(subset=['ANO'])
            df['ANO'] = df['ANO'].astype(int).astype(str)
            anos_disponiveis = sorted(df['ANO'].unique().tolist())
            opcoes_anos = ["Comparação (Todos os Anos)"] + anos_disponiveis

            ano_selecionado = st.selectbox("Selecione o Ano:", opcoes_anos)

            fig, ax = plt.subplots(figsize=(10, 5))

            if ano_selecionado == "Comparação (Todos os Anos)":
                top_municipios = df['MUNICÍPIO'].value_counts().head(10).index
                df_filtrado = df[df['MUNICÍPIO'].isin(top_municipios)]
                tabela_cruzada = pd.crosstab(df_filtrado['MUNICÍPIO'], df_filtrado['ANO'])
                tabela_cruzada['Total'] = tabela_cruzada.sum(axis=1)
                tabela_cruzada = tabela_cruzada.sort_values(by='Total', ascending=True).drop(columns='Total')
                tabela_cruzada.plot(kind='barh', ax=ax)
                ax.set_title("Comparativo Anual (Top 10)")
            else:
                df_filtrado = df[df['ANO'] == ano_selecionado]
                contagem = df_filtrado['MUNICÍPIO'].value_counts().head(10).sort_values(ascending=True)
                contagem.plot(kind='barh', color='darkred', ax=ax)
                ax.set_title(f"Volume em {ano_selecionado}")

            ax.set_xlabel("Número de Casos")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

# (As demais páginas seguem o mesmo padrão...)