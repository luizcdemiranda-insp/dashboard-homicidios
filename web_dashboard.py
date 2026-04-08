# --- (Lá no topo, no seu Menu Lateral, adicione a 5ª opção) ---
# menu = st.sidebar.radio("", ["1. VISÃO GERAL", "2. CASOS POR ÁREA", "3. MOTIVAÇÃO / DELITO", "4. MODO ANALÍTICO", "5. ASSISTENTE IA"])

# =====================================================================
# 6. PÁGINA: ASSISTENTE IA (NOVA)
# =====================================================================
elif menu == "5. ASSISTENTE IA":
    st.header("🤖 Assistente Virtual de Análise")
    st.markdown("Converse com a Inteligência Artificial sobre os dados do monitoramento.")
    st.write("---")

    # 1. Cria uma memória para o chat não apagar quando a tela recarregar
    if "mensagens_chat" not in st.session_state:
        # Mensagem inicial de boas vindas da IA
        st.session_state.mensagens_chat = [
            {"role": "assistant", "content": "Olá! Eu sou o seu Analista Virtual. Como posso ajudar com os dados de homicídios hoje?"}
        ]

    # 2. Exibe todo o histórico de mensagens na tela
    for msg in st.session_state.mensagens_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3. A caixinha de texto onde o usuário digita
    pergunta_usuario = st.chat_input("Pergunte algo sobre os dados...")

    # 4. O que acontece quando o usuário aperta Enter:
    if pergunta_usuario:
        # Salva e mostra a mensagem do usuário
        st.session_state.mensagens_chat.append({"role": "user", "content": pergunta_usuario})
        with st.chat_message("user"):
            st.markdown(pergunta_usuario)
            
        # --- AQUI ENTRARÁ O CÉREBRO DA IA NO FUTURO ---
        # Por enquanto, uma resposta automática simulada
        resposta_simulada = f"Você perguntou: '{pergunta_usuario}'. Em breve, minha IA estará conectada aos seus dados para responder isso com precisão!"
        
        # Salva e mostra a resposta da IA
        st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_simulada})
        with st.chat_message("assistant"):
            st.markdown(resposta_simulada)
