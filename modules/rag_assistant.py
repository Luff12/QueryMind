"""Schema-and-sample-row RAG assistant using Ollama embeddings and ChromaDB."""
from __future__ import annotations
import requests
from sqlalchemy import text
from database.multi_db import get_active_engine, get_active_dialect, get_active_database_label
from database.schema import get_database_schema

OLLAMA_BASE = "http://localhost:11434"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_CHAT_MODEL = "llama3.2"

def _embed(texts, model=DEFAULT_EMBED_MODEL):
    try:
        response = requests.post(f"{OLLAMA_BASE}/api/embed", json={"model": model, "input": texts}, timeout=180)
        response.raise_for_status()
        vectors = response.json().get("embeddings")
        if vectors:
            return vectors
    except requests.RequestException:
        pass
    # Compatibility with older Ollama versions.
    vectors = []
    for item in texts:
        r = requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model": model, "prompt": item}, timeout=180)
        r.raise_for_status()
        vectors.append(r.json()["embedding"])
    return vectors

def build_database_documents(include_sample_rows=False, rows_per_table=3):
    schema = get_database_schema()
    engine = get_active_engine()
    docs, metas, ids = [], [], []
    for table, details in schema.items():
        col_text = ", ".join(f"{c['name']} ({c.get('type','UNKNOWN')})" for c in details["columns"])
        fk_text = "; ".join(f"{fk['column']} -> {fk['references_table']}.{fk['references_column']}" for fk in details["foreign_keys"]) or "No declared foreign keys"
        docs.append(f"Database: {get_active_database_label()}\nTable: {table}\nColumns: {col_text}\nRelationships: {fk_text}")
        metas.append({"table": table, "kind": "schema"}); ids.append(f"schema::{table}")
        if include_sample_rows:
            try:
                with engine.connect() as conn:
                    frame = __import__('pandas').read_sql_query(text(f"SELECT * FROM {engine.dialect.identifier_preparer.quote(table)} LIMIT {int(rows_per_table)}"), conn)
                if not frame.empty:
                    docs.append(f"Sample records from {table}:\n{frame.to_csv(index=False)}")
                    metas.append({"table": table, "kind": "sample_rows"}); ids.append(f"rows::{table}")
            except Exception as exc:
                docs.append(f"Could not read sample rows from {table}: {exc}")
                metas.append({"table": table, "kind": "sample_rows_error"}); ids.append(f"rows_error::{table}")
    return docs, metas, ids

def index_database(include_sample_rows=False, rows_per_table=3, embedding_model=DEFAULT_EMBED_MODEL):
    import chromadb
    from pathlib import Path
    docs, metas, ids = build_database_documents(include_sample_rows, rows_per_table)
    if not docs: raise RuntimeError("No database schema documents were found.")
    vectors = _embed(docs, embedding_model)
    client = chromadb.PersistentClient(path="data/querymind_chroma")
    collection = client.get_or_create_collection("querymind_database_context")
    # Replace the collection contents to avoid stale schema chunks.
    existing = collection.get()
    if existing.get("ids"): collection.delete(ids=existing["ids"])
    collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=vectors)
    collection.modify(metadata={"database_label": get_active_database_label()})
    return len(docs)

def ask_database(question, embedding_model=DEFAULT_EMBED_MODEL, chat_model=DEFAULT_CHAT_MODEL, top_k=5):
    import chromadb
    client = chromadb.PersistentClient(path="data/querymind_chroma")
    collection = client.get_or_create_collection("querymind_database_context")
    if collection.count() == 0: raise RuntimeError("Database knowledge is not indexed yet. Build the RAG index first.")
    indexed_label = (collection.metadata or {}).get("database_label")
    if indexed_label and indexed_label != get_active_database_label():
        raise RuntimeError("The RAG index belongs to a different active database. Rebuild the index for this connection before asking questions.")
    query_vector = _embed([question], embedding_model)[0]
    results = collection.query(query_embeddings=[query_vector], n_results=min(int(top_k), collection.count()))
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    context = "\n\n".join(f"[Source table: {m.get('table','unknown')} | {m.get('kind','context')}]\n{d}" for d,m in zip(documents,metadatas))
    prompt = f"""You are QueryMind's database knowledge assistant. Answer ONLY using the supplied retrieved database context. If the context does not contain the answer, say that the indexed context does not provide enough information. Do not invent tables, columns, relationships, or values. Cite each factual statement with [table: TABLE_NAME]. Never execute SQL or claim to have queried live data.\n\nRETRIEVED CONTEXT:\n{context}\n\nQUESTION:\n{question}\n\nANSWER:"""
    response = requests.post(f"{OLLAMA_BASE}/api/generate", json={"model": chat_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1}}, timeout=180)
    response.raise_for_status()
    return response.json().get("response", "").strip(), [{"table":m.get("table"),"kind":m.get("kind")} for m in metadatas]
