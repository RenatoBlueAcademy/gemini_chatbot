import json

import pandas as pd
import streamlit as st

from functions.db_functions import initialize_db, update_vector_database


class QADatabaseHandler:
    def __init__(self, db_path="qa_database.json"):
        self.db_path = db_path

    @st.cache_data
    def load_data(_self):
        try:
            with open(_self.db_path, "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        except FileNotFoundError:
            return "Arquivo não encontrado..."

    def save_data(self, df):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(df.to_dict("records"), f, ensure_ascii=False, indent=2)
        db = initialize_db()
        update_vector_database(db, df)
