FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY chroma_db/ /app/chroma_db
COPY functions/ /app/functions
COPY pages/ /app/pages
COPY src/ /app/src
COPY ui/ /app/ui
COPY qa_database.json .
COPY Main.py .

RUN chmod +x /app/Main.py

ENV PORT 8080

CMD streamlit run --server.port $PORT --server.address 0.0.0.0 Main.py