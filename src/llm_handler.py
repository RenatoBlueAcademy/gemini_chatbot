import streamlit as st
from chromadb.config import Settings
from langchain.chains import ConversationChain, RetrievalQA
from langchain_chroma import Chroma
from langchain_google_genai import (ChatGoogleGenerativeAI,
                                    GoogleGenerativeAIEmbeddings,
                                    HarmBlockThreshold, HarmCategory)


class LLMHandler():
    def __init__(self, api_key, model_name="gemini-1.5-pro"):
        self.api_key = api_key
        self.model_name = model_name
        self.llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, safety_settings={
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        })
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
        self.vectorstore = self.create_vectorstore()

    def create_vectorstore(self, directory="chroma_db", collection_name="chatbot-rh"):
        return Chroma(persist_directory=directory, embedding_function=self.embeddings, collection_name=collection_name, client_settings=Settings(
            persist_directory=directory, is_persistent=True
        ))

    def create_conversation_chain(self, memory):
        return ConversationChain(llm=self.llm, verbose=True, memory=memory)

    def create_retrieval_chain(self, retriever):
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
        )

    def generate_response(self, prompt):
        retriever = self.vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 3, "fetch_k": 5})
        qa_response = self.create_retrieval_chain(retriever).invoke({"query": prompt})
        retrieved_info = qa_response['result']
        source_docs = qa_response['source_documents']

        enhanced_prompt = f"""Você é um assistente especializado em responder perguntas. Utilize o contexto fornecido para responder com precisão. Se a resposta não estiver clara ou faltar informação, responda com 'Eu não sei'. Limite sua resposta a no máximo três frases, garantindo que seja clara e concisa.
                            Perguntas básicas como Oi! Tudo bem?, bom dia, boa tarde, boa noite e etc devem ser respondidas normalmente!

                            Pergunta: {prompt}

                            Contexto: {retrieved_info}

                            Resposta:
                            """

        response = self.create_conversation_chain(st.session_state.memory).predict(input=enhanced_prompt)
        return response, source_docs

    def generate_response_performance(self, prompt):
        retriever = self.vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": 3, "fetch_k": 5})
        qa_chain = self.create_retrieval_chain(retriever)

        qa_response = qa_chain({"query": prompt})
        retrieved_info = qa_response['result']

        enhanced_prompt = f"""Based on the following information and the conversation history, please respond to the user's query:

                            Retrieved Information: {retrieved_info}

                            User Query: {prompt}

                            Please provide a comprehensive answer, incorporating the retrieved information if relevant.
                            """

        response = self.llm.invoke(input=enhanced_prompt)
        return response.content

    def test_performance(self, questions):
        results = []
        for question in questions:
            response = self.generate_response_performance(question)
            results.append(response)
        return results
