# ==========================================================
                        # 1. CSS HÍBRIDO (TELA ESCURA / IMPRESSÃO CLARA E COMPACTA)
                        # ==========================================================
                        st.markdown("""
                        <style>
                        /* ----- ESTILOS DA TELA (MODO ESCURO - MANTIDOS INTACTOS) ----- */
                        .org-header { background-color:#1E2130; padding:15px; border-radius:10px; margin-bottom:15px; text-align:center; }
                        .org-header h2 { color:#ffffff; margin:0; font-family: sans-serif; }
                        
                        .orcrim-box { border:2px solid #ff4b4b; padding:15px; border-radius:10px; margin-bottom:20px; font-family: sans-serif; }
                        .orcrim-box h3 { text-align:center; color:#ff4b4b; margin-top:0; }
                        
                        .nivel-header { background-color:#2d3446; padding:6px; border-radius:5px; margin-top:15px; margin-bottom:10px; text-align:center; color:#F1C40F; font-weight:bold; font-size:13px; letter-spacing:1px; font-family: sans-serif; }
                        
                        .cards-container { display:flex; flex-wrap:wrap; justify-content:center; gap:12px; }
                        
                        .tatico-card { background-color:#4a4f63; border:2px solid #333333; border-radius:8px; padding:15px 10px; min-width:180px; max-width:240px; flex: 1 1 auto; text-align:center; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); display: flex; flex-direction: column; align-items: center; justify-content: flex-start; cursor: crosshair; transition: transform 0.2s; font-family: sans-serif; }
                        .tatico-card:hover { transform: scale(1.05); z-index: 10; }
                        .tatico-card.alvo { background-color:#E74C3C; border-color:#ffffff; }
                        
                        .tatico-card img { width:135px; height:135px; border-radius:50%; object-fit:cover; margin-bottom:6px; border:2px solid #fff; }
                        .tatico-card .no-foto { width:135px; height:135px; border-radius:50%; background:#333; font-size:60px; line-height:135px; margin-bottom:6px; border:2px solid #fff; text-align:center; color:white; }
                        
                        .tatico-card .nome { color:white; font-size:13px; font-weight:bold; line-height:1.2; margin-bottom: 2px; }
                        .tatico-card .vulgo { color:#F1C40F; font-size:12px; font-style:italic; margin-bottom: 2px; }
                        .tatico-card .funcao { color:#e0e0e0; font-size:11px; margin-bottom: 4px; }
                        .tatico-card .rg { color:#b0b4c4; font-size:11px; margin-top:auto; padding-top:4px; border-top: 1px dashed #7f8c8d; width: 100%; }

                        /* ----- MODO DE IMPRESSÃO (LIMPEZA ABSOLUTA) ----- */
                        @media print {
                            /* 1. BOMBA NUCLEAR NOS FUNDOS ESCUROS: Transforma TUDO em transparente e letras pretas */
                            * {
                                background: transparent !important;
                                background-color: transparent !important;
                                text-shadow: none !important;
                                box-shadow: none !important;
                                color: #000 !important;
                            }

                            /* 2. PAPEL BRANCO ABSOLUTO E EXPANDIDO */
                            html, body, .stApp, .main, .block-container {
                                background-color: #FFF !important;
                                background: #FFF !important;
                                padding: 0 !important;
                                margin: 0 !important;
                                max-width: 100% !important;
                            }

                            /* 3. ESCONDER LIXO DO STREAMLIT (Logos, Títulos, Buscas, Menus) */
                            [data-testid="stSidebar"],
                            [data-testid="stHeader"],
                            [data-testid="stToolbar"],
                            [data-testid="stHorizontalBlock"], /* Isso esconde os Logos do topo, o título e as barras de busca! */
                            div[data-testid="stTabs"] > div:first-child, /* Esconde o botão das abas */
                            hr, 
                            .stSelectbox,
                            .stButton,
                            iframe {
                                display: none !important;
                            }

                            /* Esconder títulos h1, h2, h3 padrão do Streamlit (como 'ÁREA 1 - ORCIM') para não duplicar com os nossos */
                            [data-testid="stMarkdownContainer"] h1,
                            [data-testid="stMarkdownContainer"] h2,
                            [data-testid="stMarkdownContainer"] h3 {
                                display: none !important;
                            }

                            /* 4. SALVAR E FORMATAR O NOSSO ORGANOGRAMA TÁTICO */
                            #zona-de-impressao { display: block !important; width: 100% !important; }
                            
                            /* Restauramos a visibilidade dos títulos APENAS dentro do nosso HTML */
                            #zona-de-impressao h2, .org-header h2 { display: block !important; font-size: 18px !important; font-weight: bold !important; border-bottom: 2px solid #000 !important; padding-bottom: 5px !important; margin-bottom: 10px !important; }
                            #zona-de-impressao h3, .orcrim-box h3 { display: block !important; font-size: 16px !important; margin-bottom: 5px !important; font-weight: bold !important; }

                            .orcrim-box { border: 2px solid #000 !important; padding: 10px !important; margin-bottom: 15px !important; page-break-inside: auto !important; }
                            
                            /* Forçar cor de fundo cinza clara do cabeçalho de hierarquia (Chefe, Integrante...) na impressão */
                            .nivel-header { background-color: #eeeeee !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; border: 1px solid #000 !important; padding: 4px !important; margin-top: 10px !important; margin-bottom: 10px !important; font-size: 12px !important; font-weight: bold !important; text-align: center !important; }
                            
                            .cards-container { gap: 8px !important; }
                            
                            .tatico-card { 
                                border: 2px solid #333333 !important; 
                                padding: 5px !important; 
                                min-width: 110px !important; 
                                max-width: 130px !important; 
                                page-break-inside: avoid !important; 
                                break-inside: avoid !important;
                            }
                            
                            /* Destacar o alvo com borda vermelha na impressão (O print-color-adjust força o navegador a imprimir cores de borda) */
                            .tatico-card.alvo { border: 3px solid #E74C3C !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } 
                            
                            .tatico-card img, .tatico-card .no-foto { width: 55px !important; height: 55px !important; border: 1px solid #000 !important; margin-bottom: 4px !important; line-height: 55px !important; font-size: 25px !important; }
                            
                            .tatico-card .nome { font-size: 10px !important; font-weight: bold !important; margin-bottom: 2px !important; }
                            .tatico-card .vulgo { font-size: 9px !important; font-style: italic !important; margin-bottom: 2px !important; }
                            .tatico-card .funcao { font-size: 9px !important; margin-bottom: 2px !important; }
                            .tatico-card .rg { font-size: 9px !important; border-top: 1px dashed #000 !important; padding-top: 3px !important; margin-top: 3px !important; }

                            @page { margin: 10mm; size: landscape; }
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        # ==========================================================
                        # 2. BOTÃO DE IMPRIMIR
                        # ==========================================================
                        components.html("""
                        <div style='display: flex; justify-content: flex-end; font-family: sans-serif; padding-right: 5px;'>
                            <button onclick='window.parent.print()' style='background-color: #ff4b4b; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: 0.2s;'>
                                🖨️ Imprimir Organograma Tático
                            </button>
                        </div>
                        """, height=55)
