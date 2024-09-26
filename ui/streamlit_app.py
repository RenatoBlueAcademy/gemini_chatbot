import json
from datetime import datetime

import google.auth
import streamlit as st
import tiktoken
from google.cloud import secretmanager
from langchain.memory import ConversationBufferMemory

from src.feedback_handler import FeedbackManager
from src.llm_handler import LLMHandler
from src.secret_manager import SecretManager

llm_handler = None
qa_chain = None


def initialize_app():
    global llm_handler, qa_chain

    credentials, project = google.auth.default()
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    secret_manager = SecretManager(project=project, client=client)
    api_key = secret_manager.access_secret_version("GEMINI_API_KEY")

    if api_key is None:
        print(
            "Chave API não encontrada no Secret Manager. Tentando carregar do .env..."
        )
        api_key = secret_manager.load_from_env("GEMINI_API_KEY")

    if api_key is None:
        raise ValueError(
            "Não foi possível obter a chave API do Gemini. Verifique o Secret Manager ou o arquivo .env."
        )

    llm_handler = LLMHandler(api_key=api_key)
    vectorstore = llm_handler.create_vectorstore()

    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(return_messages=True)

    conversation = llm_handler.create_conversation_chain(memory=st.session_state.memory)
    retriever = vectorstore.as_retriever(
        search_type="mmr", search_kwargs={"k": 3, "fetch_k": 5}
    )

    qa_chain = llm_handler.create_retrieval_chain(retriever)


def run_streamlit_app():
    # Configuração da página Streamlit
    st.set_page_config(page_title="Projeto Chatbot RH - Gemini e BlueShift")
    st.sidebar.image(
        "https://blueshift.com.br/assets/Logo-Blueshift-8KLAJS3K.svg",
        use_column_width=True,
    )
    st.title("Chatbot RH - Gemini e BlueShift")

    initialize_app()
    main()


def main():
    global llm_handler

    # Inicialização do estado da sessão
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Exibição das mensagens anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input do usuário e geração de resposta
    if prompt := st.chat_input("Como posso ajudar você?"):
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            full_response, source_docs = llm_handler.generate_response(prompt)
            st.markdown(full_response)

        st.session_state["messages"].append(
            {"role": "assistant", "content": full_response}
        )

        feedback_manager = FeedbackManager()
        feedback = feedback_manager.get_feedback()

        if feedback:
            st.success("Obrigado pelo seu feedback!")

    # Botões de ação
    if len(st.session_state["messages"]) > 0:
        if "conversation_id" not in st.session_state:
            st.session_state["conversation_id"] = "history_" + datetime.now().strftime(
                "%Y%m%d%H%M%S"
            )

        action_buttons_container = st.container()

        cols_dimensions = [8, 8, 8]
        cols_dimensions.append(100 - sum(cols_dimensions))

        col0, col1, col2, col3 = action_buttons_container.columns(cols_dimensions)

        with col1:
            json_messages = json.dumps(st.session_state["messages"]).encode(
                encoding="utf-8"
            )
            st.download_button(
                label="📥",
                data=json_messages,
                file_name="chat_conversation.json",
                mime="application/json",
            )

        with col2:
            if st.button("🧹"):
                st.session_state["messages"] = []
                del st.session_state["conversation_id"]
                st.rerun()

        with col3:
            enc = tiktoken.get_encoding("cl100k_base")
            tokenized_full_text = enc.encode(
                " ".join([item["content"] for item in st.session_state["messages"]])
            )
            label = f"💬 {len(tokenized_full_text)} tokens"
            st.link_button(label, "https://platform.openai.com/tokenizer")


if __name__ == "__main__":
    run_streamlit_app()