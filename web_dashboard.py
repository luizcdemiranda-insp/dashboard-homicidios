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
    # Título atualizado conforme solicitado!
    st.markdown("<h1 style='text-align: center;'>🛡️ DASHBOARD DE OCORRÊNCIAS</h1>", unsafe_allow_html=True)

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
    
    # Padroniza o cabeçalho para MAIÚSCULO
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
        
        # Filtro 1: Modo de Análise e Ano
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

        # Se o ano foi escolhido, prosseguimos para o Filtro de Área
        if len(anos_selecionados) > 0:
            df_filtrado_ano = df[df['ANO'].isin(anos_selecionados)].copy()

            # Descobrindo a coluna de ÁREA (Coluna S = índice 18, mas vamos buscar pelo nome para garantir)
            COL_AREA = next((c for c in df.columns if "ÁREA" in c or "AREA" in c), None)
            if not COL_AREA and len(df.columns) > 18:
                COL_AREA = df.columns[18] # Força a coluna S caso o nome esteja estranho
            
            # Filtro 2: ÁREA
            if COL_AREA:
                areas_disponiveis = sorted(df_filtrado_ano[COL_AREA].dropna().astype(str).unique().tolist())
                # Remove lixos da lista de áreas
                areas_disponiveis = [a for a in areas_disponiveis if a.strip() != "" and a != "NAN"]
                
                area_selecionada = st.selectbox("SELECIONE A ÁREA:", ["TODAS AS ÁREAS"] + areas_disponiveis)
                
                # Aplica o filtro de área se não for "TODAS"
                if area_selecionada != "TODAS AS ÁREAS":
                    df_filtrado = df_filtrado_ano[df_filtrado_ano[COL_AREA].astype(str) == area_selecionada].copy()
                else:
                    df_filtrado = df_filtrado_ano.copy()
            else:
                df_filtrado = df_filtrado_ano.copy()
                st.warning("Coluna de ÁREA não encontrada. Exibindo dados gerais.")

            st.write("---")

            # --- BUSCA DE COLUNAS RESTANTES ---
            COL_DIA = next((c for c in df.columns if "DIA" in c and "SEMANA" in c), None)
            COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in c), None)

            # --- ANÁLISE 1: QUANTIDADE DE PROCEDIMENTOS ---
            total_procedimentos = len(df_filtrado)
            st.metric(label="📊 TOTAL DE PROCEDIMENTOS (OCORRÊNCIAS) NO PERÍODO E ÁREA SELECIONADOS", value=f"{total_procedimentos:,}".replace(',', '.'))
            st.write("<br>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)

            # --- ANÁLISE 2: DIA DA SEMANA ---
            with col1:
                st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                if COL_DIA and total_procedimentos > 0:
                    tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
                    grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''),
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=[COL_DIA, 'ANO', 'TOTAL']
                    ).properties(height=350)
                    st.altair_chart(grafico_dia, use_container_width=True)
                else:
                    st.info("Sem dados suficientes para o Dia da Semana.")

            # --- ANÁLISE 3: CIRCUNSCRIÇÃO ---
            with col2:
                st.markdown("### 🗺️ CRIMES POR CIRCUNSCRIÇÃO")
                if COL_CIRCUNSCRICAO and total_procedimentos > 0:
                    tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
                    grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x', title=''),
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=[COL_CIRCUNSCRICAO, 'ANO', 'TOTAL']
                    ).properties(height=350)
                    st.altair_chart(grafico_circ, use_container_width=True)
                else:
                    st.info("Sem dados suficientes para Circunscrição.")

            st.write("<br>", unsafe_allow_html=True)

            # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM (SOLUÇÃO DEFINITIVA) ---
            st.markdown("### ⚖️ DISTRIBUIÇÃO DE ORCRIM")
            
            # Pegando a coluna AE (Índice 30, pois o Python começa no 0)
            if len(df.columns) > 30 and total_procedimentos > 0:
                # Extrai a coluna AE bruta e converte para texto maiúsculo
                orcrim_raw = df_filtrado.iloc[:, 30].astype(str).str.upper()
                
                # Função "à prova de balas" para classificar os textos bagunçados
                def classificar_orcrim(texto):
                    if "INVESTIGA" in texto: return "EM INVESTIGAÇÃO"
                    if "X MIL" in texto or "VS MIL" in texto: return "TRÁFICO X MILÍCIA"
                    if "TRÁFICO" in texto or "TRAFICO" in texto: return "TRÁFICO"
                    if "MILÍCIA" in texto or "MILICIA" in texto: return "MILÍCIA"
                    return "OUTROS" # Ignora células vazias ou não identificadas

                # Aplica a função e cria uma nova coluna limpa
                df_filtrado['ORCRIM_LIMPO'] = orcrim_raw.apply(classificar_orcrim)
                
                # Filtra apenas as 4 categorias que você pediu
                df_orcrim = df_filtrado[df_filtrado['ORCRIM_LIMPO'] != "OUTROS"]
                
                if len(df_orcrim) > 0:
                    tabela_orcrim = df_orcrim.groupby(['ORCRIM_LIMPO', 'ANO']).size().reset_index(name='TOTAL')
                    
                    grafico_orcrim = alt.Chart(tabela_orcrim).mark_bar().encode(
                        x=alt.X('TOTAL:Q', title='Ocorrências'),
                        y=alt.Y('ORCRIM_LIMPO:N', sort='-x', title=''),
                        color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")),
                        tooltip=['ORCRIM_LIMPO', 'ANO', 'TOTAL']
                    ).properties(height=300)
                    
                    st.altair_chart(grafico_orcrim, use_container_width=True)
                else:
                    st.info("Nenhuma das 4 classificações de ORCRIM foi encontrada para os filtros selecionados.")
            else:
                st.warning("Não foi possível acessar a coluna AE ou não há dados para analisar.")

        else:
            st.info("POR FAVOR, SELECIONE PELO MENOS UM ANO PARA GERAR AS ANÁLISES.")

# --- Outras Páginas ---
elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    st.info("Página em construção...")

elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")
