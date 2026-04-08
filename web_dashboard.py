import streamlit as st
import pandas as pd
import altair as alt

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CABEÇALHO ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])

with col_esq:
    try:
        st.image("logo1.png", width=150)
    except:
        st.write("")

with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ MONITORAMENTO DE HOMICÍDIOS</h1>", unsafe_allow_html=True)

with col_dir:
    try:
        st.image("logo2.png", width=150)
    except:
        st.write("")

st.write("---")

# 2. Menu Lateral (Título do Botão 1 atualizado e com proporções consistentes)
st.sidebar.markdown("### NAVEGAÇÃO")
menu = st.sidebar.radio(
    "", 
    [
        "1. VISÃO GERAL",  # Título atualizado
        "2. CASOS POR ÁREA", 
        "3. MOTIVAÇÃO / DELITO",
        "4. MODO ANALÍTICO"
    ]
)

# 3. Função de Carga de Dados (Com Detetive de Vítimas)
@st.cache_data
def carregar_dados():
    # Link padrão para a primeira aba
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    
    # Padroniza o cabeçalho para MAIÚSCULO
    df.columns = [str(col).strip().upper() for col in df.columns]

    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    return df

# =====================================================================
# 4. PÁGINA: VISÃO GERAL (MACRO)
# =====================================================================
if menu == "1. VISÃO GERAL":
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
            
            # Botões pares com proporções consistentes
            modo_analise = st.radio(
                "SELECIONE O FORMATO DA ANÁLISE:", 
                ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"], 
                horizontal=True
            )

            anos_selecionados = []
            if modo_analise == "ANÁLISE INDIVIDUAL":
                ano_escolhido = st.selectbox("SELECIONE O ANO:", anos_disponiveis)
                anos_selecionados = [ano_escolhido]
            else:
                st.write("**SELECIONE OS ANOS PARA COMPARAR:**")
                
                # Funções dos botões rápidos
                def selecionar_todos():
                    for a in anos_disponiveis: st.session_state[f"chk_{a}"] = True
                def limpar_selecao():
                    for a in anos_disponiveis: st.session_state[f"chk_{a}"] = False

                # Cria o estado na memória caso seja a primeira vez abrindo a página
                for ano in anos_disponiveis:
                    if f"chk_{ano}" not in st.session_state:
                        st.session_state[f"chk_{ano}"] = True # Começa com todos marcados

                # Botões de seleção rápida
                b1, b2, _ = st.columns([2, 2, 6])
                b1.button("✓ Todos os anos", on_click=selecionar_todos)
                b2.button("✗ Limpar seleção", on_click=limpar_selecao)
                
                # Exibe as caixinhas de marcação
                colunas_anos = st.columns(min(len(anos_disponiveis), 6) or 1)
                for i, ano in enumerate(anos_disponiveis):
                    colunas_anos[i % len(colunas_anos)].checkbox(ano, key=f"chk_{ano}")
                
                # Coleta quem ficou marcado
                anos_selecionados = [ano for ano in anos_disponiveis if st.session_state[f"chk_{ano}"]]

            if len(anos_selecionados) > 0:
                df_filtrado_ano = df[df['ANO'].isin(anos_selecionados)].copy()

                # --- FILTRO DE ÁREA (COM BLINDAGEM ANTI-ERRO) ---
                # Descobrindo a coluna de ÁREA (Coluna S = índice 18, mas vamos buscar pelo nome)
                COL_AREA = next((c for c in df.columns if "ÁREA" in str(c) or "AREA" in str(c)), None)
                if not COL_AREA and len(df.columns) > 18:
                    COL_AREA = df.columns[18]
                
                if COL_AREA:
                    # Tenta converter para texto maiúsculo e arrancar espaços em branco sobrando
                    df_filtrado_ano['AREA_LIMPA'] = df_filtrado_ano[COL_AREA].astype(str).str.strip().str.upper()
                    areas_disponiveis = sorted(df_filtrado_ano['AREA_LIMPA'].unique().tolist())
                    
                    # Remove lixos da lista de áreas
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
                    # --- BUSCA DE COLUNAS ---
                    COL_DIA = next((c for c in df.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
                    COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in str(c)), None)
                    COL_VITIMAS = next((c for c in df.columns if "VÍTIMAS" in str(c) or "VITIMAS" in str(c)), None)

                    # --- ANÁLISE 1: CARDS DE PROCEDIMENTOS E VÍTIMAS (NOVO DESIGN) ---
                    total_procedimentos = len(df_filtrado)
                    
                    # Contagem de vítimas (Coluna T), blindando contra erros
                    if COL_VITIMAS and COL_VITIMAS in df_filtrado.columns:
                        total_vitimas = df_filtrado[COL_VITIMAS].dropna().astype(float).sum()
                    else:
                        total_vitimas = 0 # Valor padrão se não achar a coluna

                    # Exibindo os Cards Grandes e de mesmo design
                    c1, c2 = st.columns(2)
                    with c1:
                        # Card para Total de Procedimentos
                        st.markdown(
                            f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #ff4b4b; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2);"><h3 style="margin: 0; color: #b0b4c4; font-size: 16px;">📊 TOTAL DE PROCEDIMENTOS</h3><h1 style="margin: 15px 0 0 0; color: white; font-size: 48px; font-weight: bold;">{total_procedimentos:,}</h1></div>'.replace(',', '.'), 
                            unsafe_allow_html=True
                        )
                    with c2:
                        # Card para Total de Vítimas
                        st.markdown(
                            f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2);"><h3 style="margin: 0; color: #b0b4c4; font-size: 16px;">👤 TOTAL DE VÍTIMAS</h3><h1 style="margin: 15px 0 0 0; color: white; font-size: 48px; font-weight: bold;">{int(total_vitimas):,}</h1></div>'.replace(',', '.'), 
                            unsafe_allow_html=True
                        )

                    st.write("<br>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)

                    # --- ANÁLISE 2: DIA DA SEMANA ---
                    with col1:
                        st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
                        if COL_DIA:
                            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
                            
                            # Filtra dias válidos e ordena (para garantir Seg a Dom se as colunas forem lidas na ordem certa)
                            tabela_dia = tabela_dia[~tabela_dia[COL_DIA].astype(str).str.contains("NAN|NONE", case=False, na=False)]
                            
                            grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                                x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''),
                                color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=[COL_DIA, 'ANO', 'TOTAL']
                            ).properties(height=350)
                            st.altair_chart(grafico_dia, use_container_width=True)
                        else: st.info("Coluna de Dia da Semana não encontrada.")

                    # --- ANÁLISE 3: CIRCUNSCRIÇÃO ---
                    with col2:
                        st.markdown("### 🗺️ CRIMES POR CIRCUNSCRIÇÃO")
                        if COL_CIRCUNSCRICAO:
                            tabela_circ = df_filtrado.groupby([COL_CIRCUNSCRICAO, 'ANO']).size().reset_index(name='TOTAL')
                            grafico_circ = alt.Chart(tabela_circ).mark_bar().encode(
                                x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y(f'{COL_CIRCUNSCRICAO}:N', sort='-x', title=''),
                                color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=[COL_CIRCUNSCRICAO, 'ANO', 'TOTAL']
                            ).properties(height=350)
                            st.altair_chart(grafico_circ, use_container_width=True)
                        else: st.info("Coluna de Circunscrição não encontrada.")

                    st.write("<br>", unsafe_allow_html=True)

                    # --- ANÁLISE 4: DISTRIBUIÇÃO DAS ORCRIM ---
                    st.markdown("### ⚖️ ATRIBUIÇÃO DE CRIMES (ORCRIM)")
                    
                    # Vamos tentar identificar a coluna automaticamente
                    sugestoes_orcrim = [c for c in df_filtrado.columns if "ORCRIM" in str(c) or "MOTIVAÇÃO" in str(c)]
                    col_orcrim = sugestoes_orcrim[0] if sugestoes_orcrim else (df_filtrado.columns[30] if len(df_filtrado.columns) > 30 else None)

                    if col_orcrim:
                        # Limpeza forçada: converte para texto, tira espaços e deixa maiúsculo
                        df_filtrado['ORCRIM_LIMPO'] = df_filtrado[col_orcrim].astype(str).str.strip().str.upper()
                        
                        def classificar_orcrim(texto):
                            if "INVESTIGA" in texto: return "EM INVESTIGAÇÃO"
                            if "X MIL" in texto or "VS MIL" in texto: return "TRÁFICO X MILÍCIA"
                            if "TRÁFICO" in texto or "TRAFICO" in texto: return "TRÁFICO"
                            if "MILÍCIA" in texto or "MILICIA" in texto: return "MILÍCIA"
                            return "OUTROS"

                        df_filtrado['ORCRIM_CLASSIFICADO'] = df_filtrado['ORCRIM_LIMPO'].apply(classificar_orcrim)
                        
                        df_orcrim = df_filtrado[df_filtrado['ORCRIM_CLASSIFICADO'] != "OUTROS"]
                        
                        if not df_orcrim.empty:
                            # Contagem para o gráfico
                            tabela_orcrim = df_orcrim.groupby(['ORCRIM_CLASSIFICADO', 'ANO']).size().reset_index(name='TOTAL')
                            
                            grafico_orcrim = alt.Chart(tabela_orcrim).mark_bar().encode(
                                x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y('ORCRIM_CLASSIFICADO:N', sort='-x', title=''),
                                color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=['ORCRIM_CLASSIFICADO', 'ANO', 'TOTAL']
                            ).properties(height=300)
                            st.altair_chart(grafico_orcrim, use_container_width=True)
                        else:
                            st.info("Nenhum dado válido de Tráfico, Milícia ou Investigação encontrado para este filtro.")
            
        except Exception as e:
            st.error(f"Erro ao processar os gráficos. Detalhe técnico: {e}")

# --- Outras Páginas ---
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
            
            # Ocultando as colunas que contenham a palavra 'NEUTRA' no cabeçalho
            colunas_limpas = [col for col in df_raiox.columns if "NEUTRA" not in str(col)]
            df_limpo = df_raiox[colunas_limpas]
            
            st.dataframe(df_limpo)
    except Exception as e:
        st.error(f"Erro ao gerar a tabela: {e}")
