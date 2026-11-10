# QueryMind — AI-Powered SQL Assistant

QueryMind is a local-first Streamlit SQL workspace powered by Ollama. It combines natural-language SQL generation, read-only validation, query execution, schema exploration, performance monitoring, lineage analysis and AI-assisted database knowledge retrieval.

## New in this update

### Multi-database connectivity
- SQLite (default), PostgreSQL and MySQL connection support through SQLAlchemy.
- Test a connection before activating it.
- Schema inspection and read-only SQL execution use the selected connection.
- Credentials are held in the current Streamlit session; they are not written into project files.
- Existing SQLite-specific diagnostics (Security Auditor, Database Health and Index Lab) remain SQLite-only. Performance history is stored in QueryMind's local monitoring database.

### Database RAG Assistant
- Builds local context chunks from the active database schema and declared foreign-key relationships.
- Optionally indexes up to three sample rows per table. Sample-row indexing is off by default.
- Uses Ollama embeddings and a persistent local ChromaDB collection.
- Answers from retrieved context only and displays retrieved source tables. It does not run SQL or claim to have queried live records.
- Rebuild the index after schema/data changes.

## Requirements

- Python 3.10+ (use a Python version supported by the installed Streamlit, ChromaDB and database drivers).
- Ollama running locally.
- Chat model: `llama3.2`.
- Embedding model: `nomic-embed-text`.
- PostgreSQL server/credentials when using PostgreSQL; MySQL server/credentials when using MySQL.

## Setup (Windows PowerShell)

```powershell
# From the QueryMind project folder
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull llama3.2
ollama pull nomic-embed-text
python -m streamlit run app.py
```

If your existing virtual environment is already configured, activate it and run `pip install -r requirements.txt` rather than recreating it.

## Using multiple databases

1. Open **Database Connections** in the sidebar.
2. Select SQLite, PostgreSQL or MySQL.
3. Enter the connection details and click **Test connection**.
4. After a successful test, click **Use this database**.
5. Open **SQL Assistant** or **Schema Canvas**.
6. To return to the sample SQLite database, use **Switch back to default SQLite**.

PostgreSQL uses the `psycopg` driver; MySQL uses `PyMySQL`. Install dependencies from `requirements.txt`.

## Using Database RAG Assistant

1. Confirm the active database in **Database Connections**.
2. Open **Database RAG Assistant**.
3. Keep sample-record indexing disabled unless you have permission to store those records in the local vector index.
4. Click **Build / refresh database knowledge index**.
5. Ask a question and review the retrieved source tables.

The local vector store is created at `data/querymind_chroma/`. It is not intended for committing to GitHub.

## Important limitations

- External database support applies to schema inspection and read-only SQL generation/execution. Some legacy diagnostics and index tools still use SQLite-specific commands and are disabled for PostgreSQL/MySQL.
- RAG answers are grounded in the indexed schema and optional sample rows; they are not a substitute for executing a live analytical query.
- RAG context can become stale. Rebuild the index after relevant database changes.
- Do not index secrets, personal data, regulated data or records you are not authorized to process.
- Keep database passwords out of source code, screenshots, logs and Git commits.

## Git hygiene

The `.gitignore` file excludes virtual environments, local databases, ChromaDB data, caches and secret files. Review it before pushing.
