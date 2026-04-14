import streamlit as st
import pandas as pd
import altair as alt

# --- IMPORTANTE: Nova biblioteca da Inteligência Artificial ---
import google.generativeai as genai 

# 1. Configuração da Página
st.set_page_config(page_title="Monitoramento de Homicídios", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
    div[role="radiogroup"] > label > div:first-child,
    div[data-testid="stCheckbox"] > label > div:first-child { display: none; }
    
    div[role="radiogroup"] > label,
    div[data-testid="stCheckbox"] > label {
        background-color: #1E2130; border: 1px solid #4a4f63; padding: 10px 15px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: center; cursor: pointer;
        width: 100%;
    }
    
    div[role="radiogroup"] > label:hover,
    div[data-testid="stCheckbox"] > label:hover { border-color: #ff4b4b; }
    
    div[role="radiogroup"] > label:has(input:checked),
    div[data-testid="stCheckbox"] > label:has(input:checked) {
        background-color: #ff4b4b; color: white; border-color: #ff4b4b;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.3);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        justify-content: flex-start; padding-left: 20px;
    }

    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] {
        display: flex; flex-direction: row; flex-wrap: wrap; gap: 15px; width: 100%;
    }
    div[data-testid="stMainBlockContainer"] div[role="radiogroup"] > label {
        flex: 1; min-width: 150px; margin: 0; padding: 12px;
    }

    div[data-testid="stCheckbox"] > label {
        padding: 6px 0px; font-size: 14px; margin: 0;
    }
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stCheckbox"] {
        padding-bottom: 0px; margin-bottom: -10px;
    }

    @media (max-width: 768px) {
        div[data-testid="stMainBlockContainer"] div[role="radiogroup"] { flex-direction: column; gap: 5px; }
        h1 { font-size: 38px !important; }
        h2 { font-size: 42px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
col_esq, col_meio, col_dir = st.columns([1, 4, 1])
with col_esq:
    try: st.image("logo1.png", width=150)
    except: st.write("")
with col_meio:
    st.markdown("<h1 style='text-align: center;'>🛡️ MONITORAMENTO DE HOMICÍDIOS</h1>", unsafe_allow_html=True)
with col_dir:
    try: st.image("logo2.png", width=150)
    except: st.write("")
st.write("---")

# 2. Menu Lateral (Com a nova página de IA)
st.sidebar.markdown("### NAVEGAÇÃO")
menu = st.sidebar.radio(
    "", 
    [
        "1. VISÃO GERAL", 
        "2. CASOS POR ÁREA", 
        "3. MOTIVAÇÃO / DELITO",
        "4. MODO ANALÍTICO",
        "5. ASSISTENTE IA" # Nova página integrada!
    ]
)

# 3. Função de Carga de Dados
@st.cache_data
def carregar_dados():
    url = "https://docs.google.com/spreadsheets/d/1P7eT63dyYrfVKos5-34VtWjtjzZsDgVJTGm_yObHYkc/export?format=csv&gid=0"
    df = pd.read_csv(url)
    df.columns = [str(col).strip().upper() for col in df.columns]

    if 'ANO' not in df.columns and 'DATA' in df.columns:
        df['ANO'] = pd.to_datetime(df['DATA'], dayfirst=True, errors='coerce').dt.year
    
    return df

# =====================================================================
# FUNÇÃO REUTILIZÁVEL PARA GERAR OS GRÁFICOS E CARDS
# =====================================================================
def gerar_dashboard(df_filtrado):
    COL_DIA = next((c for c in df.columns if "DIA" in str(c) and "SEMANA" in str(c)), None)
    COL_CIRCUNSCRICAO = next((c for c in df.columns if "CIRCUNSCRI" in str(c)), None)
    COL_VITIMAS = next((c for c in df.columns if "VÍTIMAS" in str(c) or "VITIMAS" in str(c)), None)

    total_procedimentos = len(df_filtrado)
    
    if COL_VITIMAS and COL_VITIMAS in df_filtrado.columns:
        vitimas_raw = df_filtrado[COL_VITIMAS]
        if isinstance(vitimas_raw, pd.DataFrame): vitimas_raw = vitimas_raw.iloc[:, 0]
        total_vitimas = pd.to_numeric(vitimas_raw.astype(str).str.replace(',', '.'), errors='coerce').fillna(0).sum()
    else:
        total_vitimas = 0

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #ff4b4b; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2);"><h3 style="margin: 0; color: #b0b4c4; font-size: 16px;">📊 TOTAL DE PROCEDIMENTOS</h3><h1 style="margin: 15px 0 0 0; color: white; font-size: 48px; font-weight: bold;">{total_procedimentos:,}</h1></div>'.replace(',', '.'), 
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f'<div style="background-color: #1E2130; padding: 25px; border-radius: 12px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2);"><h3 style="margin: 0; color: #b0b4c4; font-size: 16px;">👤 TOTAL DE VÍTIMAS</h3><h1 style="margin: 15px 0 0 0; color: white; font-size: 48px; font-weight: bold;">{int(total_vitimas):,}</h1></div>'.replace(',', '.'), 
            unsafe_allow_html=True
        )

    st.write("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 CRIMES POR DIA DA SEMANA")
        if COL_DIA:
            tabela_dia = df_filtrado.groupby([COL_DIA, 'ANO']).size().reset_index(name='TOTAL')
            tabela_dia = tabela_dia[~tabela_dia[COL_DIA].astype(str).str.contains("NAN|NONE", case=False, na=False)]
            
            if not tabela_dia.empty:
                grafico_dia = alt.Chart(tabela_dia).mark_bar().encode(
                    x=alt.X('TOTAL:Q', title='Ocorrências'), y=alt.Y(f'{COL_DIA}:N', sort='-x', title=''),
                    color=alt.Color('ANO:N', legend=alt.Legend(title="Ano")), tooltip=[COL_DIA, 'ANO', 'TOTAL']
                ).properties(height=350)
                st.altair_chart(grafico_dia, use_container_width=True)
            else:
                st.info("Sem dados de Dia da Semana para este filtro.")
        else: st.info("Coluna de Dia da Semana não encontrada.")

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
            else:
                st.info("Sem dados de Circunscrição para este filtro.")
        else: st.info("Coluna de Circunscrição não encontrada.")

    st.write("<br>", unsafe_allow_html=True)

    st.markdown("### ⚖️ ATRIBUIÇÃO DE CRIMES (ORCRIM)")
    
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

        df_filtrado['ORCRIM_CLASSIFICADO'] = col_orcrim_data.apply(classificar_orcrim)
        
        tot_investiga = len(df_filtrado[df_filtrado['ORCRIM_CLASSIFICADO'] == 'EM INVESTIGAÇÃO'])
        tot_trafico = len(df_filtrado[df_filtrado['ORCRIM_CLASSIFICADO'] == 'TRÁFICO'])
        tot_milicia = len(df_filtrado[df_filtrado['ORCRIM_CLASSIFICADO'] == 'MILÍCIA'])
        tot_traf_mil = len(df_filtrado[df_filtrado['ORCRIM_CLASSIFICADO'] == 'TRÁFICO X MILÍCIA'])

        card1, card2, card3, card4 = st.columns(4)
        
        with card1:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #F1C40F; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">EM INVESTIGAÇÃO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_investiga}</h2></div>', unsafe_allow_html=True)
        with card2:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #E74C3C; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">TRÁFICO</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_trafico}</h2></div>', unsafe_allow_html=True)
        with card3:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #3498DB; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 14px;">MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_milicia}</h2></div>', unsafe_allow_html=True)
        with card4:
            st.markdown(f'<div style="background-color: #1E2130; padding: 20px; border-radius: 10px; border-top: 5px solid #9B59B6; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.2); height: 100%;"><h4 style="margin: 0; color: #b0b4c4; font-size: 13px;">TRÁFICO X MILÍCIA</h4><h2 style="margin: 15px 0 0 0; color: white; font-size: 54px; line-height: 1;">{tot_traf_mil}</h2></div>', unsafe_allow_html=True)


# =====================================================================
# 4. PÁGINA: VISÃO GERAL (SÓ ANO)
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
            modo_analise = st.radio("SELECIONE O FORMATO DA ANÁLISE:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"])

            anos_selecionados = []
            if modo_analise == "ANÁLISE INDIVIDUAL":
                col_drop, col_vazia = st.columns([2, 8]) 
                ano_escolhido = col_drop.selectbox("SELECIONE O ANO:", anos_disponiveis)
                anos_selecionados = [ano_escolhido]
            else:
                st.write("**SELECIONE OS ANOS PARA COMPARAR:**")
                def selecionar_todos_vg():
                    for a in anos_disponiveis: st.session_state[f"chk_vg_{a}"] = True
                def limpar_selecao_vg():
                    for a in anos_disponiveis: st.session_state[f"chk_vg_{a}"] = False

                for ano in anos_disponiveis:
                    if f"chk_vg_{ano}" not in st.session_state:
                        st.session_state[f"chk_vg_{ano}"] = True

                b1, b2, _ = st.columns([2, 2, 6])
                b1.button("✓ Todos os anos", on_click=selecionar_todos_vg, key="btn_all_vg")
                b2.button("✗ Limpar seleção", on_click=limpar_selecao_vg, key="btn_clear_vg")
                
                colunas_anos = st.columns(min(len(anos_disponiveis), 8) or 1, gap="small")
                for i, ano in enumerate(anos_disponiveis):
                    colunas_anos[i % len(colunas_anos)].checkbox(ano, key=f"chk_vg_{ano}")
                
                anos_selecionados = [ano for ano in anos_disponiveis if st.session_state[f"chk_vg_{ano}"]]

            if len(anos_selecionados) > 0:
                df_filtrado = df[df['ANO'].isin(anos_selecionados)].copy()
                st.write("---")
                if df_filtrado.empty:
                    st.warning("Nenhuma ocorrência encontrada para os anos selecionados.")
                else:
                    gerar_dashboard(df_filtrado)
            
        except Exception as e:
            st.error(f"Erro ao processar os gráficos. Detalhe técnico: {e}")

# =====================================================================
# 5. PÁGINA: CASOS POR ÁREA (ANO + ÁREA)
# =====================================================================
elif menu == "2. CASOS POR ÁREA":
    st.header("🗺️ CASOS POR ÁREA DE POLICIAMENTO")
    
    with st.spinner("Sincronizando banco de dados..."):
        try:
            df = carregar_dados()
            sucesso_dados = True
        except Exception as e:
            st.error(f"Erro ao baixar a planilha. Detalhe técnico: {e}")
            sucesso_dados = False

    if sucesso_dados:
        df = df.dropna(subset=['ANO'])
        df['ANO'] = df['ANO'].astype(int).astype(str)
        anos_disponiveis = sorted(df['ANO'].unique().tolist(), reverse=True)

        st.subheader("FILTROS DE ANÁLISE")
        modo_analise = st.radio("SELECIONE O FORMATO DA ANÁLISE:", ["ANÁLISE INDIVIDUAL", "ANÁLISE COMPARATIVA"], key="modo_analise_area")

        anos_selecionados = []
        if modo_analise == "ANÁLISE INDIVIDUAL":
            col_drop, _ = st.columns([2, 8]) 
            ano_escolhido = col_drop.selectbox("SELECIONE O ANO:", anos_disponiveis, key="ano_ind_area")
            anos_selecionados = [ano_escolhido]
        else:
            st.write("**SELECIONE OS ANOS PARA COMPARAR:**")
            def selecionar_todos_ar():
                for a in anos_disponiveis: st.session_state[f"chk_ar_{a}"] = True
            def limpar_selecao_ar():
                for a in anos_disponiveis: st.session_state[f"chk_ar_{a}"] = False

            for ano in anos_disponiveis:
                if f"chk_ar_{ano}" not in st.session_state:
                    st.session_state[f"chk_ar_{ano}"] = True

            b1, b2, _ = st.columns([2, 2, 6])
            b1.button("✓ Todos os anos", on_click=selecionar_todos_ar, key="btn_all_ar")
            b2.button("✗ Limpar seleção", on_click=limpar_selecao_ar, key="btn_clear_ar")
            
            colunas_anos = st.columns(min(len(anos_disponiveis), 8) or 1, gap="small")
            for i, ano in enumerate(anos_disponiveis):
                colunas_anos[i % len(colunas_anos)].checkbox(ano, key=f"chk_ar_{ano}")
            
            anos_selecionados = [ano for ano in anos_disponiveis if st.session_state[f"chk_ar_{ano}"]]

        if len(anos_selecionados) > 0:
            df_filtrado_ano = df[df['ANO'].isin(anos_selecionados)].copy()

            st.write("**SELECIONE A ÁREA:**")
            COL_AREA = next((c for c in df.columns if "ÁREA" in str(c) or "AREA" in str(c)), None)
            if not COL_AREA and len(df.columns) > 18:
                COL_AREA = df.columns[18]
            
            if COL_AREA:
                col_area_data = df_filtrado_ano[COL_AREA]
                if isinstance(col_area_data, pd.DataFrame): col_area_data = col_area_data.iloc[:, 0]

                df_filtrado_ano['AREA_LIMPA'] = col_area_data.apply(lambda x: str(x).strip().upper())
                areas_disponiveis = sorted(df_filtrado_ano['AREA_LIMPA'].unique().tolist())
                areas_disponiveis = [a for a in areas_disponiveis if a not in ["", "NAN", "NONE", "NAT", "-", "--"]]
                
                area_selecionada = st.radio("", ["TODAS AS ÁREAS"] + areas_disponiveis, horizontal=True, key="radio_area_selecionada")
                
                if area_selecionada != "TODAS AS ÁREAS":
                    df_filtrado = df_filtrado_ano[df_filtrado_ano['AREA_LIMPA'] == area_selecionada].copy()
                else:
                    df_filtrado = df_filtrado_ano.copy()
            else:
                df_filtrado = df_filtrado_ano.copy()

            st.write("---")
            if df_filtrado.empty:
                st.warning(f"Nenhuma ocorrência encontrada na área selecionada para os anos informados.")
            else:
                gerar_dashboard(df_filtrado)

# --- Outras Páginas ---
elif menu == "3. MOTIVAÇÃO / DELITO":
    st.header("🔍 DETALHAMENTO DE MOTIVAÇÃO")
    st.info("Página em construção...")

elif menu == "4. MODO ANALÍTICO":
    st.header("MODO ANALÍTICO")
    try:
        with st.spinner("Carregando tabela completa..."):
            df_raiox = carregar_dados()
            colunas_limpas = [col for col in df_raiox.columns if "NEUTRA" not in str(col)]
            df_limpo = df_raiox[colunas_limpas]
            st.dataframe(df_limpo)
    except Exception as e:
        st.error(f"Erro ao gerar a tabela: {e}")

# =====================================================================
# 6. PÁGINA: ASSISTENTE IA (VERSÃO AUTO-ADAPTÁVEL)
# =====================================================================
elif menu == "5. ASSISTENTE IA":
    st.header("🤖 Analista Criminal Virtual")
    st.markdown("Converse com a Inteligência Artificial sobre os padrões e dados do monitoramento.")
    
    api_key_input = st.sidebar.text_input("🔑 Sua Chave API do Gemini:", type="password")
    st.write("---")

    if not api_key_input:
        st.warning("👈 Insira sua chave de API no menu lateral.")
    else:
        try:
            chave_limpa = api_key_input.strip()
            genai.configure(api_key=chave_limpa)
            
            # Carrega dados para o Analista saber do que estamos falando
            df_contexto = carregar_dados()
            contexto_dados = f"Você é um analista criminal. O banco de dados tem {len(df_contexto)} registros com as colunas: {', '.join(df_contexto.columns)}."

            # --- MÁGICA: DESCOBRINDO O MODELO DISPONÍVEL ---
            if "modelo_ativo" not in st.session_state:
                modelos_possiveis = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.0-pro']
                modelo_escolhido = None
                
                # Testamos qual modelo sua chave aceita
                for m in modelos_possiveis:
                    try:
                        teste_model = genai.GenerativeModel(m)
                        teste_model.generate_content("Oi", generation_config={"max_output_tokens": 1})
                        modelo_escolhido = m
                        break
                    except:
                        continue
                
                if modelo_escolhido:
                    st.session_state.modelo_ativo = modelo_escolhido
                else:
                    st.session_state.modelo_ativo = "gemini-1.5-flash" # Fallback

            # Inicializa o modelo com o que funcionou no teste
            model = genai.GenerativeModel(st.session_state.modelo_ativo)
            
            if "chat_gemini" not in st.session_state:
                st.session_state.chat_gemini = model.start_chat(history=[])
                st.session_state.mensagens_front = [
                    {"role": "model", "content": f"Sistemas prontos (Modelo: {st.session_state.modelo_ativo}). Como posso ajudar?"}
                ]
            
            for msg in st.session_state.mensagens_front:
                role_tela = "assistant" if msg["role"] == "model" else "user" 
                with st.chat_message(role_tela):
                    st.markdown(msg["content"])

            pergunta = st.chat_input("Digite sua pergunta...")
            
            if pergunta:
                with st.chat_message("user"):
                    st.markdown(pergunta)
                st.session_state.mensagens_front.append({"role": "user", "content": pergunta})
                
                with st.spinner("Analisando..."):
                    # Enviamos o contexto junto com a pergunta para garantir que a IA saiba dos dados
                    prompt_completo = f"CONTEXTO: {contexto_dados}\n\nPERGUNTA DO USUÁRIO: {pergunta}"
                    response = st.session_state.chat_gemini.send_message(prompt_completo)
                
                with st.chat_message("assistant"):
                    st.markdown(response.text)
                st.session_state.mensagens_front.append({"role": "model", "content": response.text})

        except Exception as e:
            st.error(f"Erro de Conexão: {e}")
