import io
from datetime import datetime

import pandas as pd
import streamlit as st

from functions.db_functions import initialize_db
from src.qa_database_handler import QADatabaseHandler

db_handler = QADatabaseHandler()


def get_next_id(df):
    """Retorna o próximo ID com base nos dados existentes."""
    if df.empty:
        return 1
    try:
        df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
        return int(df["ID"].max() + 1)
    except ValueError:
        return 1


def apply_filters(data, status_filter, pergunta_filter, start_date, end_date):
    """Aplica os filtros de status, pergunta e intervalo de data aos dados."""
    return data[
        (data["Status"].isin(status_filter))
        & (data["Pergunta"].str.contains(pergunta_filter, case=False, na=False))
        & (
            pd.to_datetime(data["Data de criação"], dayfirst=True).dt.date.between(
                start_date, end_date
            )
        )
    ]


def export_data_to_excel(filtered_data):
    """Exporta os dados filtrados para um arquivo Excel."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        filtered_data.to_excel(writer, index=False, sheet_name="Sheet1")
    output.seek(0)
    return output


def display_main_table(filtered_df):
    """Exibe a tabela principal de Perguntas e Respostas."""
    for index, row in filtered_df.iterrows():
        st.write("---")
        cols = st.columns([1, 2, 3, 1, 1, 1, 1, 1])

        with cols[0]:
            st.write(f"**ID:** {row['ID']}")
        with cols[1]:
            st.write(f"**Pergunta:** {row['Pergunta']}")
        with cols[2]:
            st.write(f"**Resposta:** {row['Resposta']}")
        with cols[3]:
            st.write(f"**Versão:** {row['Versão']}")
        with cols[4]:
            st.write(f"**Status:** {row['Status']}")
        with cols[5]:
            st.write(f"**Data de criação:** {row['Data de criação']}")
        with cols[6]:
            if st.button("Editar", key=f"edit_{index}"):
                st.session_state.edit_doc = index
        with cols[7]:
            if st.button("Excluir", key=f"excluir_{index}"):
                delete_document(row["ID"], index)

        if st.session_state.get("edit_doc") == index:
            edit_document_form(index, row)


def delete_document(doc_id_to_delete, index):
    """Exclui o documento do banco de dados e do estado da sessão."""
    db = initialize_db()
    docs = db.get()
    for doc_id, metadata in zip(docs["ids"], docs["metadatas"]):
        if metadata["ID"] == doc_id_to_delete:
            db.delete(ids=[doc_id])
            break
    st.session_state.data = st.session_state.data[
        st.session_state.data["ID"] != doc_id_to_delete
    ]
    db_handler.save_data(st.session_state.data)
    st.success("Documento excluído com sucesso!")
    st.rerun()


def edit_document_form(index, row):
    """Formulário para edição de um documento existente."""
    with st.form(f"edit_form_{index}"):
        st.subheader("Editar Pergunta e Resposta")
        edited_question = st.text_input("Pergunta", value=row["Pergunta"])
        edited_answer = st.text_input("Resposta", value=row["Resposta"])
        current_version = row["Versão"]
        edited_status = st.selectbox(
            "Status",
            options=["Ativo", "Inativo"],
            index=["Ativo", "Inativo"].index(row["Status"]),
        )
        edited_date = st.date_input(
            "Data de criação",
            value=datetime.strptime(row["Data de criação"], "%d/%m/%Y").date(),
        )

        if st.form_submit_button("Salvar"):
            new_version = (
                current_version + 1
                if (
                    edited_question != row["Pergunta"]
                    or edited_answer != row["Resposta"]
                )
                else current_version
            )
            st.session_state.data.loc[index, "Pergunta"] = edited_question
            st.session_state.data.loc[index, "Resposta"] = edited_answer
            st.session_state.data.loc[index, "Versão"] = new_version
            st.session_state.data.loc[index, "Status"] = edited_status
            st.session_state.data.loc[index, "Data de criação"] = edited_date.strftime(
                "%d/%m/%Y"
            )
            db_handler.save_data(st.session_state.data)
            st.success("Documento atualizado com sucesso!")
            st.session_state.edit_doc = None
            st.rerun()


def add_new_document_form():
    """Formulário para adicionar um novo documento."""
    if st.session_state.new_doc:
        st.write("")
        with st.form("new_document"):
            st.subheader("Nova Pergunta e Resposta")
            new_question = st.text_input("Pergunta")
            new_answer = st.text_input("Resposta")
            new_version = st.number_input("Versão", min_value=1, value=1, step=1)
            new_status = st.selectbox("Status", options=["Ativo", "Inativo"])
            new_date = st.date_input("Data de criação")

            if st.form_submit_button("Salvar"):
                new_id = get_next_id(st.session_state.data)
                new_row = pd.DataFrame(
                    {
                        "ID": [new_id],
                        "Pergunta": [new_question],
                        "Resposta": [new_answer],
                        "Versão": [new_version],
                        "Status": [new_status],
                        "Data de criação": [new_date.strftime("%d/%m/%Y")],
                    }
                )
                st.session_state.data = pd.concat(
                    [st.session_state.data, new_row], ignore_index=True
                )
                db_handler.save_data(st.session_state.data)
                st.success("Pergunta e Resposta adicionadas com sucesso!")
                st.session_state.new_doc = False
                st.rerun()


def evaluate_response(reference, generated):
    if isinstance(reference, str) and isinstance(generated, str):
        similarity = len(
            set(generated.lower().split()) & set(reference.lower().split())
        ) / len(set(reference.lower().split()))
        if similarity > 0.8:
            return "Correto", "A resposta segue a ideia central da resposta referência."
        elif similarity > 0.5:
            return (
                "Parcialmente Correto",
                "A resposta contém alguns elementos da resposta referência, mas não está completa.",
            )
        else:
            return (
                "Incorreto",
                "A resposta não segue a ideia central da resposta referência.",
            )
    else:
        return ("Erro", "Entrada inválida: referência e resposta gerada devem ser strings.")