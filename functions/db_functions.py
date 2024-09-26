import os

import google.auth
from dotenv import load_dotenv
from google.cloud import secretmanager
from langchain.schema import Document

from src.llm_handler import LLMHandler
from src.secret_manager import SecretManager


def get_api_key():
    credentials, project = google.auth.default()
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    secret_manager = SecretManager(project=project, client=client)

    api_key = secret_manager.access_secret_version("GEMINI_API_KEY")

    if api_key is None:
        print(
            "Chave API não encontrada no Secret Manager. Tentando carregar do .env..."
        )
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

    if api_key is None:
        raise ValueError(
            "Não foi possível obter a chave API do Gemini. Verifique o Secret Manager ou o arquivo .env."
        )

    return api_key


def initialize_db():
    api_key = get_api_key()
    llm_handler = LLMHandler(api_key=api_key)
    vectorstore = llm_handler.create_vectorstore()
    return vectorstore


def update_vector_database(db, df):
    existing_docs = db.get()
    existing_pairs = {}
    documents_to_remove = []

    # Mapear documentos existentes
    if existing_docs["documents"]:
        doc_metadatas = existing_docs.get("metadatas", [])
        doc_documents = existing_docs.get("documents", [])
        doc_ids = existing_docs.get("ids", [])
        for doc_id, metadata, doc in zip(doc_ids, doc_metadatas, doc_documents):
            unique_id = metadata.get("ID")
            existing_pairs[unique_id] = (doc_id, metadata, doc)

    new_data = []

    # Processar cada linha do DataFrame
    for _, item in df.iterrows():
        unique_id = item.get("ID")
        question = item.get("Pergunta")
        answer = item.get("Resposta")
        version = item.get("Versão")
        status = item.get("Status")
        creation_date = item.get("Data de criação")

        if unique_id and question and answer:
            if status == "Inativo":
                if unique_id in existing_pairs:
                    doc_id, _, _ = existing_pairs[unique_id]
                    documents_to_remove.append(doc_id)
                continue

            new_metadata = {
                "ID": unique_id,
                "Pergunta": question,
                "Versão": version,
                "Status": status,
                "Data de criação": creation_date,
            }

            if unique_id in existing_pairs:
                doc_id, existing_metadata, existing_answer = existing_pairs[unique_id]
                if (
                    existing_answer != answer
                    or existing_metadata["Versão"] != version
                    or existing_metadata["Status"] != status
                    or existing_metadata["Pergunta"] != question
                ):
                    # Atualiza o documento existente
                    updated_doc = Document(
                        page_content=answer,
                        metadata=new_metadata,
                    )
                    new_data.append(updated_doc)
                    documents_to_remove.append(doc_id)
            else:
                # Adiciona novo documento
                new_doc = Document(
                    page_content=answer,
                    metadata=new_metadata,
                )
                new_data.append(new_doc)

    # Remover documentos obsoletos
    if documents_to_remove:
        db.delete(documents_to_remove)

    # Adicionar novos documentos ou atualizações
    if new_data:
        db.add_documents(new_data)
