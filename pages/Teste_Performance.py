from datetime import datetime

import google.auth
import pandas as pd
import streamlit as st
from google.cloud import secretmanager

from functions.function_app import evaluate_response
from src.llm_handler import LLMHandler
from src.qa_database_handler import QADatabaseHandler
from src.secret_manager import SecretManager

# Configuração do Secret Manager e API Gemini
credentials, project = google.auth.default()
client = secretmanager.SecretManagerServiceClient(credentials=credentials)
secret_manager = SecretManager(project=project, client=client)
api_key = secret_manager.access_secret_version("GEMINI_API_KEY")

if api_key is None:
    print("Chave API não encontrada no Secret Manager. Tentando carregar do .env...")
    api_key = secret_manager.load_from_env("GEMINI_API_KEY")

if api_key is None:
    raise ValueError(
        "Não foi possível obter a chave API do Gemini. Verifique o Secret Manager ou o arquivo .env."
    )

db_handler = QADatabaseHandler()

llm_handler = LLMHandler(api_key=api_key)
vectorstore = llm_handler.create_vectorstore()


st.set_page_config(layout="wide", page_title="Teste de performance - BlueShift")

st.sidebar.image(
    "https://blueshift.com.br/assets/Logo-Blueshift-8KLAJS3K.svg", use_column_width=True
)
st.title("Gemini - Teste de performance")

if "data" not in st.session_state:
    st.session_state.data = db_handler.load_data()
if "page" not in st.session_state:
    st.session_state.page = "main"
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None


def main_page():
    if st.button("Ir para Edição de Perguntas e Respostas"):
        st.session_state.page = "edit"
        st.rerun()
    st.write("---")
    st.header("Teste de performance do modelo")

    selected_questions = st.multiselect(
        "Selecione as perguntas para teste",
        options=st.session_state.data["Pergunta"].tolist(),
    )

    if st.button("Iniciar Teste de Performance"):
        st.write("")
        st.write("")
        if selected_questions:
            with st.spinner("Testando o modelo..."):
                results = llm_handler.test_performance(selected_questions)

            pergunta_resposta_dict = dict(zip(st.session_state.data["Pergunta"], st.session_state.data["Resposta"]))

            results_df = pd.DataFrame(
                {
                    "Iteração": range(1, len(selected_questions) + 1),
                    "Pergunta": selected_questions,
                    "Resposta de Referência": [pergunta_resposta_dict[q] for q in selected_questions],
                    "Resposta": results,
                }
            )

            results_df["Resposta"] = results_df["Resposta"].apply(str)

            results_df[["Validação", "Motivo"]] = results_df.apply(
                lambda row: evaluate_response(
                    row["Resposta de Referência"], row["Resposta"]
                ),
                axis=1,
                result_type="expand",
            )

            st.subheader("Detalhamento dos Resultados")
            st.dataframe(results_df, use_container_width=True)

            csv = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Baixar Resultados como CSV",
                data=csv,
                file_name="resultados_teste_performance.csv",
                mime="text/csv",
            )

        else:
            st.warning("Por favor, selecione pelo menos uma pergunta para testar.")
    st.warning(
        "ATENÇÃO: Você está prestes a iniciar o teste massivo de validação das respostas. O processo pode demorar alguns minutos. Tem certeza que deseja prosseguir?"
    )


def edit_page():
    col1, col2, col3 = st.columns(3)
    with col1:

        if st.button("Voltar à Página Principal"):
            st.session_state.page = "main"
            st.rerun()

    with col2:
        if st.button("Adicionar nova Pergunta e Resposta"):
            st.session_state.edit_index = -1
    st.write("---")
    st.header("Editar Perguntas e Respostas")

    if st.session_state.edit_index is not None:
        with st.form("edit_form"):
            if st.session_state.edit_index == -1:
                st.subheader("Nova Pergunta e Resposta")
                edited_question = st.text_input("Pergunta")
                edited_answer = st.text_area("Resposta")
                edited_status = st.selectbox("Status", options=["Ativo", "Inativo"])
                edited_version = 1
            else:
                row = st.session_state.data.iloc[st.session_state.edit_index]
                st.subheader(f"Editar: {row['Pergunta']}")
                edited_question = st.text_input("Pergunta", value=row["Pergunta"])
                edited_answer = st.text_area("Resposta", value=row["Resposta"])
                edited_status = st.selectbox(
                    "Status",
                    options=["Ativo", "Inativo"],
                    index=["Ativo", "Inativo"].index(row["Status"]),
                )
                edited_version = row["Versão"] + 1

            if st.form_submit_button("Salvar"):
                if st.session_state.edit_index == -1:
                    new_row = pd.DataFrame(
                        {
                            "Pergunta": [edited_question],
                            "Resposta": [edited_answer],
                            "Versão": [edited_version],
                            "Status": [edited_status],
                            "Data de criação": [datetime.now().strftime("%d/%m/%Y")],
                        }
                    )
                    st.session_state.data = pd.concat(
                        [st.session_state.data, new_row], ignore_index=True
                    )
                    st.success("Nova pergunta e resposta adicionadas com sucesso!")
                else:
                    st.session_state.data.loc[
                        st.session_state.edit_index, "Pergunta"
                    ] = edited_question
                    st.session_state.data.loc[
                        st.session_state.edit_index, "Resposta"
                    ] = edited_answer
                    st.session_state.data.loc[st.session_state.edit_index, "Status"] = (
                        edited_status
                    )
                    st.session_state.data.loc[st.session_state.edit_index, "Versão"] = (
                        edited_version
                    )
                    st.session_state.data.loc[
                        st.session_state.edit_index, "Data de criação"
                    ] = datetime.now().strftime("%d/%m/%Y")
                    st.success("Alterações salvas com sucesso!")

                db_handler.save_data(st.session_state.data)
                st.session_state.edit_index = None
                st.rerun()

    for index, row in st.session_state.data.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 3, 1, 1, 1])
        with col1:
            st.write(f"**Pergunta:** {row['Pergunta']}")
        with col2:
            st.write(f"**Resposta:** {row['Resposta']}")
        with col3:
            st.write(f"**Versão:** {row['Versão']}")
        with col4:
            st.write(f"**Status:** {row['Status']}")
        with col5:
            if st.button("Editar", key=f"edit_{index}"):
                st.session_state.edit_index = index
                st.rerun()


# Controle de fluxo principal
if st.session_state.page == "main":
    main_page()
elif st.session_state.page == "edit":
    edit_page()