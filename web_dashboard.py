import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard de Ocorrências", layout="wide")

# --- CSS PERSONALIZADO (Ajustado para alinhamentos perfeitos) ---
st.markdown("""
    <style>
    /* Ocultar bolinhas e quadradinhos padrão */
    div[role="radiogroup"] > label > div:first-child,
    div[data-testid="stCheckbox"] > label > div:first-child { display: none; }
    
    /* Estilo base de todos os botões */
    div[role="radiogroup"] > label,
    div[data-testid="stCheckbox"] > label {
        background-color: #1E2130; border: 1px solid #4a4f63; 
        border-radius: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        margin: 0;
    }
    
    /* Efeito ao passar o mouse */
    div[role="radiogroup"] > label:hover,
    div[data-testid="stCheckbox"] > label:hover { border-color: #ff4b4b; }
    
    /* Efeito de Botão SELECIONADO (Ativo) */
    div[role="radiogroup"] > label:has(input:checked),
    div[data-testid="stCheckbox"] > label:has(input:checked) {
        background-color: #ff4b4b; color: white; border-color: #ff4b4b;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);
    }

    /* --- ESPECÍFICO 1: Menu Lateral (Empilhado e à Esquerda) --- */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 8px;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        width: 100%; justify-content: flex-start; padding: 10px 15px; padding-left: 20px;
    }

    /* --- ESPECÍFICO 2: Filtros Principais (Lado a Lado / 50% pra cada) --- */
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex; flex-direction: row; gap: 15px; width: 100%;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label {
        flex: 1; padding: 12px;
    }

    /* --- ESPECÍFICO 3: Checkboxes dos Anos (Coladinhos) --- */
    div[data-testid="stCheckbox"] > label {
        width: 100%; padding: 6px 0px; font-size: 14px;
    }
    /* Reduz espaço vertical extra criado pelo Streamlit nos checkboxes */
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stCheckbox"] {
        padding-bottom: 0px; margin-bottom: -10px;
    }
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
menu = st.sidebar.radio(
    "", 
    [
        "1. VISÃO GERAL (MACRO)", 
        "2. CASOS POR ÁREA", 
        "3. MOTIVAÇÃO / DELITO",
        "4. MODO ANALÍTICO"
    ]
)

# =====================================================================
# 3. FUNÇÃO DE CARGA DE DADOS
# =====================================================================
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    
    df.columns = [str(col).strip().upper() for col in df.columns]

    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    return df

# =====================================================================
# 4. PÁGINAS DO SISTEMA
# =====================================================================
if menu == "1. VISÃO GERAL (MACRO)":
    with st.spinner("Sincronizando banco de dados..."):
        try:
            df = carregar_dados()
            sucesso_dados = True
        except Exception as e:
            st.error(f"Erro ao baixar a planilha. Detalhe técnico: {e}")
            sucesso_dados = False

    if sucesso_dados:
        try:
            df = df.dropna(subset=['ANO'])
            df['ANO'] = df['ANO'].astype(int).astype(str)
            anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

            st.subheader("FILTROS DE ANÁLISE")
            
            # Títulos ajustados (removido o múltiplos anos)
            modo_analise = st.radio("SELECIONE O FORMATO DA ANÁLISE:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"])

            anos_selecionados = []
            
            if modo_analise == "ANÁLISE INDIVIDUAL":
                ano_escolhido = st.selectbox("SELECIONE O ANO:", anos_disponiveis)
                anos_selecionados = [ano_escolhido]
            else:
                st.write("**SELECIONE OS ANOS PARA COMPARAR:**")
                
                def selecionar_todos():
                    for a in anos_disponiveis: st.session_state[f"chk_{a}"] = True
                def limpar_selecao():
                    for a in anos_disponiveis: st.session_state[f"chk_{a}"] = False

                for ano in anos_disponiveis:
                    if f"chk_{ano}" not in st.session_state:
                        st.session_state[f"chk_{ano}"] = True

                b1, b2, _ = st.columns([2, 2, 6])
                b1.button("✓ Todos os anos", on_click=selecionar_todos)
                b2.button("✗ Limpar seleção", on_click=limpar_selecao)
                
                # Aumentei para 8 colunas e adicionei gap="small" para aproximar os botões
                colunas_anos = st.columns(min(len(anos_disponiveis), 8) or 1, gap="small")
                for i, ano in enumerate(anos_disponiveis):
                    colunas_anos[i % len(colunas_anos)].checkbox(ano, key=f"chk_{ano}")
                
                anos_selecionados = [ano for ano in anos_disponiveis if st.session_state[f"chk_{ano}"]]

            if len(anos_selecionados) > 0:
                df_filtrado_ano = df[df['ANO'].isin(anos_selecionados)].copy()

                COL_AREA = next((c for c in df.columns if "ÁREA" in str(c) or "AREA" in str(c)), None)
                
                if COL_AREA:
                    col_area_data = df_filtrado_ano[COL_AREA]
                    if isinstance(col_area_data, pd.DataFrame): col_area_data = col_area_data.iloc[:, 0]

                    df_filtrado_ano['AREA_LIMPA'] = col_area_data.apply(lambda x: str(x).strip().upper())
                    areas_disponiveis = sorted(df_filtrado_ano['AREA_LIMPA'].unique().tolist())
                    areas_disponiveis = [a for a in areas_disponiveis if a not in ["", "NAN", "NONE", "NAT"]]
                    
                    area_selecionada = st.selectbox("SELECIONE A ÁREA:", ["TODAS AS ÁREAS"] + areas_disponiveis)
                    
                    if area_selecionada != "TODAS AS ÁREAS":
                        df_filtrado = df_filtrado_ano[df_filtrado_ano['AREA_LIMPA'] == area_selecionada].copy()
                    else:
                        df_filtrado = df_filtrado_ano.copy()
                else:
                    df_filtrado = df_filtrado_ano.copy()

                st.write("---")

                if df_filtrado.empty:
                    st.warning("Nenhuma ocorrência encontrada para os filtros selecionados.")
                else:
                    COL_DIA = next((c for c in df.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
                    COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in str(c)), None)

                    total_procedimentos = len(df_filtrado)
                    st.metric(label="📊 TOTAL DE PROCEDIMENTOS (OCORRÊNCIAS)", value=f"{total_procedimentos:,}".replace(',', '.'))
                    st.write("<br>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                        if COL_DIA:
                            col_dia_data = df_filtrado[COL_DIA]
                            if isinstance(col_dia_data, pd.DataFrame): col_dia_data = col_dia_data.iloc[:, 0]
                            
                            df_filtrado['DIA_LIMPO'] = col_dia_data.apply(lambda x: str(x).strip())
                            tabela_dia = df_filtrado.groupby(['DIA_LIMPO', 'ANO']).size().reset_index(name='TOTAL')
                            tabela_dia = tabela_dia[~tabela_dia['DIA_LIMPO'].isin(["nan", "NAN", "", "None"])]

                            if not tabela_dia.empty:
                                grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                                    x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y('DIA_LIMPO:N', sort='-x', title=''),
                                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=['DIA_LIMPO', 'ANO', 'TOTAL']
                                ).properties(height=350)
                                st.altair_chart(grafico_dia, use_container_width=True)
                            else: st.info("Sem dados válidos para Dia da Semana.")
                        else: st.info("Coluna não encontrada.")

                    with col2:
                        st.markdown("### 🗺️ CRIMES POR CIRCUNSCRIÇÃO")
                        if COL_CIRCUNSCRICAO:
                            col_circ_data = df_filtrado[COL_CIRCUNSCRICAO]
                            if isinstance(col_circ_data, pd.DataFrame): col_circ_data = col_circ_data.iloc[:, 0]
                            
                            df_filtrado['CIRC_LIMPA'] = col_circ_data.apply(lambda x: str(x).strip())
                            tabela_circ = df_filtrado.groupby(['CIRC_LIMPA', 'ANO']).size().reset_index(name='TOTAL')
                            tabela_circ = tabela_circ[~tabela_circ['CIRC_LIMPA'].isin(["nan", "NAN", "", "None"])]

                            if not tabela_circ.empty:
                                grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                                    x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y('CIRC_LIMPA:N', sort='-x', title=''),
                                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=['CIRC_LIMPA', 'ANO', 'TOTAL']
                                ).properties(height=350)
                                st.altair_chart(grafico_circ, use_container_width=True)
                            else: st.info("Sem dados válidos para Circunscrição.")
                        else: st.info("Coluna não encontrada.")

                    st.write("<br>", unsafe_allow_html=True)

                    # --- ANÁLISE 4: ATRIBUIÇÃO DE CRIMES (CARDS COM FONTE GIGANTE) ---
                    st.markdown("### ⚖️ ATRIBUIÇÃO DE CRIMES")
                    
                    sugestoes_orcrim = [c for c in df_filtrado.columns if "ORCRIM" in str(c) or "MOTIVAÇÃO" in str(c)]
                    col_orcrim = sugestoes_orcrim[0] if sugestoes_orcrim else (df_filtrado.columns[30] if len(df_filtrado.columns) > 30 else None)

                    if col_orcrim:
                        col_orcrim_data = df_filtrado[col_orcrim]
                        if isinstance(col_orcrim_data, pd.DataFrame):
                            col_orcrim_data = col_orcrim_data.iloc[:, 0]
                        
                        def classificar_orcrim(texto):
                            texto = str(texto).strip().upper() 
                            if "INVESTIGA" in texto: return "EM INVESTIGAÇÃO"
                            if "X MIL" in texto or "VS MIL" in texto: return "TRÁFICO X MILÍCIA"
                            if "TRÁFICO" in texto or "TRAFICO" in texto: return "TRÁFICO"
                            if "MILÍCIA" in texto or "MILICIA" in texto: return "MILÍCIA"
                            return "OUTROS"

                        df_filtrado['ORCRIM_LIMPO'] = col_orcrim_data.apply(classificar_orcrim)
                        
                        tot_investiga = len(df_filtrado[df_filtrado['ORCRIM_LIMPO'] == 'EM INVESTIGAÇÃO'])
                        tot_trafico = len(df_filtrado[df_filtrado['ORCRIM_LIMPO'] == 'TRÁFICO'])
                        tot_milicia = len(df_filtrado[df_filtrado['ORCRIM_LIMPO'] == 'MILÍCIA'])
                        tot_traf_mil = len(df_filtrado[df_filtrado['ORCRIM_LIMPO'] == 'TRÁFICO X MILÍCIA'])

                        card1, card2, card3, card4 = st.columns(4)
                        
                        # Fonte aumentada para 54px e ajustada para preencher bem o Card
                        with card1:
                            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">EM INVESTIGAÇÃO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_investiga}</h2></div>', unsafe_allow_html=True)
                        with card2:
                            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #E74C3C; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">TRÁFICO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_trafico}</h2></div>', unsafe_allow_html=True)
                        with card3:
                            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #3498DB; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_milicia}</h2></div>', unsafe_allow_html=True)
                        with card4:
                            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #9B59B6; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 13px;">TRÁFICO X MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_traf_mil}</h2></div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Erro ao processar os gráficos. Detalhe técnico: {e}")

elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    st.info("Página em construção...")

elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")

elif menu == "4. MODO ANALÍTICO":
    st.header("🕵️‍♂️ Modo Analítico - Visualização da Planilha")
    st.write("Esta tela permite que você veja os dados brutos exatamente como o sistema está lendo da nuvem.")
    try:
        with st.spinner("Carregando tabela completa..."):
            df_raiox = carregar_dados()
            colunas_limpas = [col for col in df_raiox.columns if "NEUTRA" not in str(col)]
            df_limpo = df_raiox[colunas_limpas]
            st.dataframe(df_limpo)
    except Exception as e:
        st.error(f"Erro ao gerar a tabela: {e}")
