
from datetime import datetime, timedelta

import streamlit as st

from functions.function_app import (add_new_document_form, apply_filters,
                                    display_main_table, export_data_to_excel)
from src.qa_database_handler import QADatabaseHandler

# Inicialize o manipulador de banco de dados
db_handler = QADatabaseHandler()


# Configuração da página
st.set_page_config(layout="wide", page_title="Gerenciador de Arquivos - BlueShift")
st.sidebar.image(
    "https://blueshift.com.br/assets/Logo-Blueshift-8KLAJS3K.svg", use_column_width=True
)
st.title("Gemini - Gerenciador de arquivos")

# Carrega os dados
if "data" not in st.session_state:
    st.session_state.data = db_handler.load_data()

# Sidebar
st.sidebar.header("Filtros")
status_filter = st.sidebar.multiselect(
    "Status dos documentos", options=["Ativo", "Inativo"], default=["Ativo", "Inativo"]
)
pergunta_filter = st.sidebar.text_input("Filtrar por pergunta")

# Definir um intervalo de datas padrão (por exemplo, último ano até hoje)
default_start_date = datetime.now().date() - timedelta(days=365)
default_end_date = datetime.now().date()

date_range = st.sidebar.date_input(
    "Data de criação",
    value=(default_start_date, default_end_date),
    min_value=datetime(2000, 1, 1).date(),
    max_value=datetime.now().date(),
    format="DD/MM/YYYY",
)

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0]

# Aplicar filtros
filtered_df = apply_filters(
    st.session_state.data, status_filter, pergunta_filter, start_date, end_date
)

# Botões principais
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Nova P & R"):
        st.session_state.new_doc = True

with col2:
    if st.button("Exportar dados"):
        output = export_data_to_excel(filtered_df)
        st.download_button(
            label="Download Excel",
            data=output,
            file_name="qa_database.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# Modal para novo documento
if "new_doc" not in st.session_state:
    st.session_state.new_doc = False

add_new_document_form()

# Tabela principal com botões de edição e exclusão
display_main_table(filtered_df)

# Botão para limpar filtros
if st.sidebar.button("Limpar Filtros"):
    st.rerun()
