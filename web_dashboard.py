import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard de Ocorrências", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1E2130; border: 1px solid #4a4f63; padding: 10px 15px;
        border-radius: 8px; margin-bottom: 8px; text-align: center; font-weight: bold; transition: 0.3s;
    }
    div[role="radiogroup"] > label:hover { background-color: #ff4b4b; color: white; border-color: #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])
with col_esq:
    try: st.image("logo1.png", width=150)
    except: st.write("")
with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ DASHBOARD DE OCORRÊNCIAS</h1>", unsafe_allow_html=True)
with col_dir:
    try: st.image("logo2.png", width=150)
    except: st.write("")
st.write("---")

# --- MENU LATERAL ---
st.sidebar.markdown("### NAVEGAÇÃO")
menu = st.sidebar.radio("", ["1. VISÃO GERAL (MACRO)", "2. CASOS POR ÁREA", "3. MOTIVAÇÃO / DELITO"])

# =====================================================================
# 3. FUNÇÃO DE CARGA DE DADOS (COM LINK INTELIGENTE)
# =====================================================================
@st.cache_data
def carregar_dados():
    # =================================================================
    # 🔴 PASSO CRÍTICO: COLOQUE O LINK DA ABA DE DADOS AQUI!
    # Vá no Google Sheets, clique na aba que tem as 30+ colunas (os dados brutos),
    # copie o link lá de cima do navegador e cole entre as aspas abaixo:
    # =================================================================
    link_do_navegador = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/edit?gid=0#gid=0" 
    
    # O Python converte o link normal para link de download automaticamente
    if "/edit" in link_do_navegador:
        partes = link_do_navegador.split("/edit")
        url_csv = partes[0] + "/export?format=csv"
        if len(partes) > 1 and "#gid=" in partes[1]:
            url_csv += "&gid=" + partes[1].split("#gid=")[1]
    else:
        url_csv = link_do_navegador

    df = pd.read_csv(url_csv)
    
    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
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
            st.error(f"Erro ao baixar a planilha. Verifique o link e o acesso. Erro técnico: {e}")
            sucesso_dados = False

    if sucesso_dados:
        try:
            df = df.dropna(subset=['ANO'])
            df['ANO'] = df['ANO'].astype(int).astype(str)
            anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

            st.subheader("FILTROS DE ANÁLISE")
            
            modo_analise = st.radio("SELECIONE O FORMATO DA ANÁLISE:", ["ANÁLISE INDIVIDUAL (1 ANO)", "ANÁLISE COMPARATIVA (MÚLTIPLOS ANOS)"], horizontal=True)

            anos_selecionados = []
            if modo_analise == "ANÁLISE INDIVIDUAL (1 ANO)":
                ano_escolhido = st.selectbox("SELECIONE O ANO:", anos_disponiveis)
                anos_selecionados = [ano_escolhido]
            else:
                anos_selecionados = st.multiselect("SELECIONE OS ANOS PARA COMPARAR:", anos_disponiveis, default=anos_disponiveis[:2])

            if len(anos_selecionados) > 0:
                df_filtrado_ano = df[df['ANO'].isin(anos_selecionados)].copy()

                # --- FILTRO DE ÁREA (COM LIMPEZA DE MAIÚSCULAS) ---
                COL_AREA = next((c for c in df.columns if "ÁREA" in c or "AREA" in c), None)
                
                if COL_AREA:
                    # Limpa a coluna área: converte para texto, arranca espaços e deixa maiúsculo
                    df_filtrado_ano['AREA_LIMPA'] = df_filtrado_ano[COL_AREA].astype(str).str.strip().str.upper()
                    
                    areas_disponiveis = sorted(df_filtrado_ano['AREA_LIMPA'].unique().tolist())
                    areas_disponiveis = [a for a in areas_disponiveis if a not in ["", "NAN", "NONE"]]
                    
                    area_selecionada = st.selectbox("SELECIONE A ÁREA:", ["TODAS AS ÁREAS"] + areas_disponiveis)
                    
                    if area_selecionada != "TODAS AS ÁREAS":
                        df_filtrado = df_filtrado_ano[df_filtrado_ano['AREA_LIMPA'] == area_selecionada].copy()
                    else:
                        df_filtrado = df_filtrado_ano.copy()
                else:
                    df_filtrado = df_filtrado_ano.copy()
                    st.warning("⚠️ Coluna de ÁREA não encontrada na aba baixada.")

                st.write("---")

                # Se após os filtros o dataframe ficar vazio, avisamos sem quebrar
                if df_filtrado.empty:
                    st.warning("Nenhuma ocorrência encontrada para os filtros selecionados.")
                else:
                    COL_DIA = next((c for c in df.columns if "DIA" in c and "SEMANA" in c), None)
                    COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in c), None)

                    # --- ANÁLISE 1: PROCEDIMENTOS ---
                    total_procedimentos = len(df_filtrado)
                    st.metric(label="📊 TOTAL DE PROCEDIMENTOS (OCORRÊNCIAS) NO PERÍODO E ÁREA SELECIONADOS", value=f"{total_procedimentos:,}".replace(',', '.'))
                    st.write("<br>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)

                    # --- ANÁLISE 2: DIA DA SEMANA ---
                    with col1:
                        st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                        if COL_DIA:
                            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
                            if not tabela_dia.empty:
                                grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                                    x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''),
                                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=[COL_DIA, 'ANO', 'TOTAL']
                                ).properties(height=350)
                                st.altair_chart(grafico_dia, use_container_width=True)
                            else: st.info("Sem dados.")
                        else: st.info("Coluna não encontrada.")

                    # --- ANÁLISE 3: CIRCUNSCRIÇÃO ---
                    with col2:
                        st.markdown("### 🗺️ CRIMES POR CIRCUNSCRIÇÃO")
                        if COL_CIRCUNSCRICAO:
                            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
                            if not tabela_circ.empty:
                                grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                                    x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x', title=''),
                                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=[COL_CIRCUNSCRICAO, 'ANO', 'TOTAL']
                                ).properties(height=350)
                                st.altair_chart(grafico_circ, use_container_width=True)
                            else: st.info("Sem dados.")
                        else: st.info("Coluna não encontrada.")

                    st.write("<br>", unsafe_allow_html=True)

                    # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM ---
                    st.markdown("### ⚖️ DISTRIBUIÇÃO DE ORCRIM")
                    
                    # Deixei o seletor manual mais inteligente, ele busca palavras chave.
                    sugestoes_orcrim = [i for i, c in enumerate(df_filtrado.columns) if "ORCRIM" in c or "MOTIVAÇÃO" in c]
                    indice_sugestao = sugestoes_orcrim[0] if sugestoes_orcrim else (30 if len(df_filtrado.columns) > 30 else 0)

                    coluna_orcrim_escolhida = st.selectbox(
                        "Selecione a coluna que contém os dados de ORCRIM:", 
                        options=df_filtrado.columns.tolist(),
                        index=indice_sugestao
                    )

                    if coluna_orcrim_escolhida:
                        # Limpeza bruta: Maiúsculo e sem espaços sobrando
                        orcrim_raw = df_filtrado[coluna_orcrim_escolhida].astype(str).str.strip().str.upper()
                        
                        def classificar_orcrim(texto):
                            if "INVESTIGA" in texto: return "EM INVESTIGAÇÃO"
                            if "X MIL" in texto or "VS MIL" in texto: return "TRÁFICO X MILÍCIA"
                            if "TRÁFICO" in texto or "TRAFICO" in texto: return "TRÁFICO"
                            if "MILÍCIA" in texto or "MILICIA" in texto: return "MILÍCIA"
                            return "OUTROS"

                        df_filtrado['ORCRIM_LIMPO'] = orcrim_raw.apply(classificar_orcrim)
                        df_orcrim = df_filtrado[df_filtrado['ORCRIM_LIMPO'] != "OUTROS"]
                        
                        if not df_orcrim.empty:
                            tabela_orcrim = df_orcrim.groupby(['ORCRIM_LIMPO', 'ANO']).size().reset_index(name='TOTAL')
                            grafico_orcrim = alt.Chart(tabela_orcrim).mark_bar().encode(
                                x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y('ORCRIM_LIMPO:N', sort='-x', title=''),
                                color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=['ORCRIM_LIMPO', 'ANO', 'TOTAL']
                            ).properties(height=300)
                            st.altair_chart(grafico_orcrim, use_container_width=True)
                        else:
                            st.info("Nenhum dado válido de Tráfico, Milícia ou Investigação encontrado para este filtro.")
            
        except Exception as e:
            # Se der erro de processamento, mostra um aviso amigável ao invés de tela vermelha
            st.error(f"Erro ao processar os gráficos. Detalhe técnico: {e}")
            st.info("Dica: Use o Modo Raio-X abaixo para conferir se a planilha correta foi importada.")

        # --- MODO RAIO-X (Sempre útil) ---
        st.write("---")
        with st.expander("🕵️‍♂️ Modo Raio-X (Ver como o sistema enxerga a planilha)"):
            st.dataframe(df.head())

# --- Outras Páginas ---
elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    st.info("Página em construção...")

elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")
