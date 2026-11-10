import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from database.schema import get_database_schema

from modules.sql_generator import generate_sql
from modules.sql_validator import validate_sql
from modules.query_executor import execute_query_with_metrics
from modules.sql_explainer import explain_sql
from modules.intent_detector import detect_intent
from modules.sql_corrector import correct_sql, MAX_CORRECTION_ATTEMPTS
from modules.sql_optimizer import optimize_sql
from modules.index_recommender import generate_index_recommendations
from modules.index_benchmark import run_all_benchmarks
from modules.database_health import get_database_health_report
from modules.query_monitor import log_query_execution, get_query_execution_history
from modules.database_security import run_database_security_audit
from modules.data_lineage import analyze_sql_lineage
from database.connection import get_connection
from database.multi_db import (get_active_engine, get_active_dialect, get_active_database_label, set_active_connection, reset_connection, test_connection, DEFAULT_SQLITE_URL)
from modules.rag_assistant import index_database, ask_database

from utils.history import (
    create_session,
    save_message,
    get_messages,
    get_sessions,
    delete_session,
)

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="QueryMind | AI SQL Assistant",
    page_icon="🧠",
    layout="wide",
)


# ==========================================
# SESSION STATE
# ==========================================

defaults = {
    "active_session_id": None,
    "latest_df": None,
    "latest_sql": "",
    "latest_session_id": None,
    "latest_question": "",
    "explanation": "",
    "latest_execution_time": None,
    "latest_query_plan": None,
    "optimization_report": "",
    "index_benchmark_results": None,
    "database_health_report": None,
    "dashboard_df": None,
    "dashboard_sql": "",
    "dashboard_question": "",
    "dashboard_error": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "sql_editor_message" not in st.session_state:
    st.session_state["sql_editor_message"] = ""


# ==========================================
# CSS
# ==========================================

st.markdown(
    """
    <style>
    :root {
        --qm-bg: #111318;
        --qm-panel: #191c23;
        --qm-panel-2: #20242d;
        --qm-border: #343945;
        --qm-muted: #929baa;
        --qm-text: #e6eaf0;
        --qm-accent: #8b7cff;
        --qm-green: #21a179;
        --qm-cyan: #38bdf8;
    }
    .stApp {
        background:
            linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
            var(--qm-bg);
        background-size: 48px 48px;
        color: var(--qm-text);
    }
    [data-testid="stHeader"] { background: rgba(17,19,24,.92); }
    [data-testid="stSidebar"] {
        background: #15171d;
        border-right: 1px solid var(--qm-border);
    }
    [data-testid="stSidebar"] > div { background: transparent; }
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1600px; }
    h1, h2, h3, h4 { color: #f1f3f7 !important; letter-spacing: -.02em; }
    h1 { font-size: 2rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.45rem !important; }
    h3 { font-size: 1.12rem !important; }
    p, label, .stMarkdown { color: var(--qm-text); }
    [data-testid="stCaptionContainer"] { color: var(--qm-muted); }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #20242d, #191c23);
        border: 1px solid var(--qm-border);
        border-radius: 12px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #aab2c0 !important; }
    [data-testid="stMetricValue"] { color: #f4f6fb !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--qm-border) !important;
        border-radius: 12px;
    }
    div.stButton > button, div.stDownloadButton > button {
        border: 1px solid #424958;
        border-radius: 8px;
        background: #222630;
        color: #e9edf5;
        transition: .15s ease;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        border-color: var(--qm-accent);
        color: white;
        background: #2a2e3a;
    }
    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
    div[data-baseweb="select"] > div {
        background: #1b1f27 !important;
        border-color: #3a404d !important;
        color: #edf0f6 !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] {
        background: rgba(26,29,37,.9);
        border: 1px solid var(--qm-border);
        border-radius: 10px;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid var(--qm-border);
        border-radius: 10px;
        overflow: hidden;
    }
    hr { border-color: #303540 !important; }
    code { color: #a9baff !important; }
    [data-testid="stAlert"] { border-radius: 10px; }
    .qm-eyebrow {
        color: #a99fff; text-transform: uppercase; letter-spacing: .12em;
        font-size: .72rem; font-weight: 700; margin-bottom: .35rem;
    }
    .qm-panel {
        background: linear-gradient(145deg, #1d212a, #171a21);
        border: 1px solid #343a47; border-radius: 12px;
        padding: 14px 16px; margin: 6px 0 12px 0;
    }
    
    .stRadio [role="radiogroup"] { gap: 5px; }
    .stRadio label {
        border-radius: 8px;
        padding: 7px 9px;
    }
    .stRadio label:hover { background: #242934; }
    [data-testid="stSidebar"] .stButton button {
        width: 100%;
        text-align: left;
    }
    .qm-panel { box-shadow: 0 8px 22px rgba(0,0,0,.12); }

    
    .qm-sidebar-section {
        color: #858fa0;
        font-size: .67rem;
        font-weight: 800;
        letter-spacing: .14em;
        margin: 13px 0 8px 2px;
    }
    .qm-connection, .qm-sidebar-footer {
        color: #aab3c1;
        font-size: .76rem;
        line-height: 1.7;
    }
    .qm-status-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        margin-right: 6px;
        border-radius: 50%;
        background: #27c28a;
        box-shadow: 0 0 8px rgba(39,194,138,.45);
    }
    .qm-sidebar-footer {
        padding: 8px 10px;
        border: 1px solid #303744;
        border-radius: 9px;
        background: #1a1e26;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: 8px 10px;
        border-radius: 8px;
        margin: 2px 0;
        transition: background .15s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #252a35;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] {
        background: #29263f;
        border: 1px solid #514b7b;
    }
    [data-testid="stSidebar"] div.stButton > button {
        min-height: 40px;
        text-align: left;
        font-weight: 650;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(button[key^="overview_open_"]) {
        background: linear-gradient(145deg, #20242d, #191c23);
    }
    .qm-panel { transition: transform .15s ease, border-color .15s ease; }

    
    .stTextArea textarea {
        font-family: "Cascadia Code", "Consolas", monospace !important;
        font-size: .88rem !important;
        line-height: 1.55 !important;
        background: #12151b !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# HELPER FUNCTIONS
# ==========================================


def reset_results():
    st.session_state.latest_df = None
    st.session_state.latest_sql = ""
    st.session_state.latest_session_id = None
    st.session_state.latest_question = ""
    st.session_state.explanation = ""
    st.session_state.latest_execution_time = None
    st.session_state.latest_query_plan = None
    st.session_state.optimization_report = ""


def get_previous_sql(messages):
    for message in reversed(messages):
        sql = message.get("sql_query")
        if sql:
            return sql
    return None


def is_explanation_request(question):
    question = question.lower().strip()

    explanation_phrases = [
        "explain sql",
        "explain the sql",
        "explain this query",
        "explain the query",
        "explain last query",
        "explain latest query",
        "explain previous query",
        "describe this query",
        "describe the query",
        "what does this query do",
        "what does the query do",
        "how does this query work",
        "how does the query work",
        "explain the last sql",
        "explain latest sql",
        "explain previous sql",
    ]

    return any(phrase in question for phrase in explanation_phrases)


def get_performance_insights(query_plan):
    """
    Convert SQLite EXPLAIN QUERY PLAN details into readable observations.
    These are heuristic observations, not a full database tuning diagnosis.
    """

    if query_plan is None or query_plan.empty:
        return ["SQLite query plan is unavailable for this query."]

    if "detail" not in query_plan.columns:
        return ["SQLite returned a query plan, but its detail column is unavailable."]

    details = query_plan["detail"].fillna("").astype(str).tolist()
    insights = []

    for detail in details:
        upper_detail = detail.upper()

        if "SCAN " in upper_detail:
            if "USING COVERING INDEX" in upper_detail:
                insights.append(
                    f"Index scan detected: {detail}. SQLite is scanning an index "
                    "that may cover the requested columns."
                )
            elif "USING INDEX" in upper_detail:
                insights.append(
                    f"Indexed scan detected: {detail}. SQLite is using an index."
                )
            else:
                insights.append(
                    f"Table scan detected: {detail}. For large tables, consider "
                    "whether an appropriate index could help."
                )

        elif "SEARCH " in upper_detail:
            if "USING INDEX" in upper_detail or "USING COVERING INDEX" in upper_detail:
                insights.append(f"Index-assisted search detected: {detail}.")
            else:
                insights.append(f"Search operation detected: {detail}.")

        if "USE TEMP B-TREE" in upper_detail:
            insights.append(
                "SQLite uses a temporary B-tree, often for ORDER BY, GROUP BY, "
                "or DISTINCT. Review whether indexes could reduce this work."
            )

    if not insights:
        insights.append(
            "No obvious table-scan or temporary B-tree warning was detected "
            "in the query plan."
        )

    # Remove duplicate observations while preserving their order.
    return list(dict.fromkeys(insights))


def execute_with_correction(
    initial_sql,
    user_question,
    conversation_history=None,
):
    """
    Validate and execute SQL. If validation or execution fails,
    ask the AI to correct it and retry a maximum of
    MAX_CORRECTION_ATTEMPTS times.

    Every corrected query is validated again before execution.
    Returns query results plus performance metrics for the successful query.
    """

    current_sql = initial_sql
    last_error = ""

    for attempt in range(MAX_CORRECTION_ATTEMPTS + 1):
        # Never execute SQL before it passes validation.
        is_valid, validation_message = validate_sql(current_sql)

        if not is_valid:
            last_error = f"SQL validation failed: {validation_message}"
        else:
            (
                df,
                execution_message,
                execution_time_ms,
                query_plan,
            ) = execute_query_with_metrics(current_sql)

            if df is not None:
                return (
                    df,
                    current_sql,
                    execution_message,
                    None,
                    attempt,
                    execution_time_ms,
                    query_plan,
                )

            last_error = execution_message or "SQL execution failed."

        # No more correction attempts remain.
        if attempt >= MAX_CORRECTION_ATTEMPTS:
            return (
                None,
                current_sql,
                last_error,
                last_error,
                attempt,
                None,
                None,
            )

        # Ask the AI to repair the SQL using the error and schema.
        corrected_sql = correct_sql(
            original_sql=current_sql,
            error_message=last_error,
            user_question=user_question,
            conversation_history=conversation_history,
        )

        if not corrected_sql or corrected_sql.startswith("ERROR:"):
            correction_error = corrected_sql or "The AI did not return corrected SQL."
            return (
                None,
                current_sql,
                f"{last_error}\n\nSQL correction could not continue: {correction_error}",
                last_error,
                attempt + 1,
                None,
                None,
            )

        current_sql = corrected_sql.strip()

    return (
        None,
        current_sql,
        last_error,
        last_error,
        MAX_CORRECTION_ATTEMPTS,
        None,
        None,
    )


def apply_recommended_index(table_name, column_name):
    """Create a recommended index after checking identifiers against the schema."""
    schema = get_database_schema()

    if table_name not in schema:
        return False, f"Table '{table_name}' does not exist."

    available_columns = {column["name"] for column in schema[table_name]["columns"]}
    if column_name not in available_columns:
        return False, f"Column '{column_name}' does not exist in '{table_name}'."

    # Quote identifiers only after validating them against the actual schema.
    index_name = f"idx_{table_name}_{column_name}"
    quoted_index = '"' + index_name.replace('"', '""') + '"'
    quoted_table = '"' + table_name.replace('"', '""') + '"'
    quoted_column = '"' + column_name.replace('"', '""') + '"'

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE INDEX IF NOT EXISTS {quoted_index} "
            f"ON {quoted_table} ({quoted_column})"
        )
        conn.commit()
        return True, f"Index '{index_name}' is now available."
    except Exception as exc:
        if conn:
            conn.rollback()
        return False, f"Could not create index: {exc}"
    finally:
        if conn:
            conn.close()


# ==========================================
# PROCESS USER QUESTION
# ==========================================


def process_question(user_question, session_id):

    # Get previous conversation BEFORE saving the current question.
    conversation_history = get_messages(session_id)

    # Save current question.
    save_message(session_id, "user", user_question)

    try:
        # ======================================
        # INTENT DETECTION
        # ======================================

        if is_explanation_request(user_question):
            intent = "EXPLAIN_SQL"
        else:
            intent = detect_intent(user_question)

        # ======================================
        # EXPLAIN PREVIOUS SQL
        # ======================================

        if intent == "EXPLAIN_SQL":
            previous_sql = get_previous_sql(conversation_history)

            if not previous_sql:
                response = (
                    "There is no previous SQL query available to explain. "
                    "Generate a query first."
                )
                save_message(session_id, "assistant", response)
                return

            # Find the original question associated with this SQL.
            original_question = "Explain the previous query."

            for index in range(len(conversation_history) - 1, -1, -1):
                message = conversation_history[index]

                if (
                    message["role"] == "assistant"
                    and message.get("sql_query") == previous_sql
                ):
                    if index > 0:
                        previous_user_message = conversation_history[index - 1]

                        if previous_user_message["role"] == "user":
                            original_question = previous_user_message["content"]
                    break

            # Use results only when they belong to this SQL and session.
            result_df = None

            if (
                st.session_state.latest_sql == previous_sql
                and st.session_state.latest_session_id == session_id
            ):
                result_df = st.session_state.latest_df

            with st.spinner("Analyzing SQL and query results..."):
                explanation = explain_sql(
                    previous_sql,
                    user_question=original_question,
                    query_result=result_df,
                    conversation_history=conversation_history,
                )

            if explanation.startswith("ERROR:"):
                response = explanation
            else:
                response = (
                    "### AI SQL Analysis\n\n"
                    + explanation
                    + "\n\n### SQL Query\n\n"
                    + "```sql\n"
                    + previous_sql
                    + "\n```"
                )

            save_message(session_id, "assistant", response)
            return

        # ======================================
        # GENERAL QUESTIONS
        # ======================================

        if intent == "GENERAL":
            response = (
                "I'm QueryMind, your AI SQL assistant. "
                "I can generate SQL queries, analyze database records, "
                "explain query results and answer follow-up database questions."
            )
            save_message(session_id, "assistant", response)
            return

        # ======================================
        # SQL GENERATION
        # ======================================

        with st.spinner("Generating SQL with AI..."):
            sql_query = generate_sql(
                user_question,
                conversation_history=conversation_history,
            )

        if not sql_query or sql_query.startswith("ERROR:"):
            response = sql_query or "AI did not return a SQL query."
            save_message(session_id, "assistant", response)
            return

        # ======================================
        # VALIDATE, EXECUTE AND AUTO-CORRECT
        # ======================================

        with st.spinner("Validating, executing and analyzing SQL performance..."):
            (
                df,
                final_sql,
                execution_message,
                final_error,
                correction_attempts,
                execution_time_ms,
                query_plan,
            ) = execute_with_correction(
                initial_sql=sql_query,
                user_question=user_question,
                conversation_history=conversation_history,
            )

        if df is None:
            response = (
                "I couldn't execute the query successfully after "
                f"{correction_attempts} correction attempt(s).\n\n"
                f"**Error:** {execution_message}\n\n"
                "**Last SQL attempted:**"
            )

            save_message(session_id, "assistant", response, final_sql)
            return

        # ======================================
        # SAVE SUCCESSFUL QUERY RESULTS
        # ======================================

        response = (
            "Query executed successfully! "
            f"Returned {len(df)} rows and {len(df.columns)} columns."
        )

        if correction_attempts > 0:
            response += (
                f"\n\n_QueryMind automatically corrected the SQL "
                f"and succeeded after {correction_attempts} "
                f"correction attempt(s)._"
            )

        save_message(session_id, "assistant", response, final_sql)

        # Record successful executions for the performance monitoring dashboard.
        try:
            log_query_execution(
                sql_query=final_sql,
                execution_time_ms=execution_time_ms,
                rows_returned=len(df),
                columns_returned=len(df.columns),
                question=user_question,
                session_id=session_id,
                source="Chat",
            )
        except Exception as monitor_error:
            st.warning(
                f"Query succeeded, but performance history could not be saved: {monitor_error}"
            )

        st.session_state.latest_df = df
        st.session_state.latest_sql = final_sql
        st.session_state.latest_question = user_question
        st.session_state.latest_session_id = session_id
        st.session_state.latest_execution_time = execution_time_ms
        st.session_state.latest_query_plan = query_plan
        st.session_state.explanation = ""

    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        save_message(session_id, "assistant", error_message)


# ==========================================
# INITIALIZE CHAT
# ==========================================

sessions = get_sessions()
session_ids = [session["session_id"] for session in sessions]

if st.session_state.active_session_id not in session_ids:
    st.session_state.active_session_id = create_session()
    reset_results()


def navigate_to_page(page_name):
    """Update the radio selection from a widget callback before the next rerun."""
    st.session_state["querymind_navigation"] = page_name


def start_new_conversation():
    """Create a new chat and navigate before the sidebar radio is instantiated."""
    st.session_state.active_session_id = create_session()
    reset_results()
    st.session_state["querymind_navigation"] = "SQL Assistant"


# ==========================================
# QUERYMIND NAVIGATION
# ==========================================

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 8px 4px 16px 4px;">
          <div style="font-size: 1.45rem; font-weight: 800; color: #f3f4f8;">
            🧠 QueryMind
          </div>
          <div style="font-size: .76rem; color: #9aa4b4; margin-top: 3px;">
            AI DATA WORKSPACE
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="qm-sidebar-section">NAVIGATION</div>',
        unsafe_allow_html=True,
    )
    selected_page = st.radio(
        "WORKSPACE",
        [
            "Overview",
            "SQL Assistant",
            "Schema Canvas",
            "AI Dashboard",
            "Performance",
            "Security Auditor",
            "Data Lineage",
            "Database Health",
            "Index Lab",
            "Database Connections",
            "Database RAG Assistant",
        ],
        key="querymind_navigation",
        label_visibility="visible",
    )
    st.markdown(
        '<div class="qm-sidebar-section">QUICK ACTIONS</div>',
        unsafe_allow_html=True,
    )
    st.button(
        "＋ New Conversation",
        use_container_width=True,
        on_click=start_new_conversation,
    )

    st.markdown(
        '<div class="qm-sidebar-section">CONNECTED DATABASE</div>',
        unsafe_allow_html=True,
    )
    try:
        sidebar_schema = get_database_schema()
        st.markdown(
            f'<div class="qm-connection"><span class="qm-status-dot"></span>'
            f" {get_active_database_label()} connected · {len(sidebar_schema)} tables</div>",
            unsafe_allow_html=True,
        )
        for sidebar_table, sidebar_details in sidebar_schema.items():
            with st.expander(f"▦ {sidebar_table}"):
                for sidebar_column in sidebar_details.get("columns", []):
                    st.caption(
                        f"{sidebar_column['name']}  ·  "
                        f"{sidebar_column.get('type') or 'UNKNOWN'}"
                    )
    except Exception as sidebar_schema_error:
        st.caption(f"Schema unavailable: {sidebar_schema_error}")

    st.divider()
    st.markdown(
        """
        <div class="qm-sidebar-footer">
          <div><span class="qm-status-dot"></span> Local AI · Ollama</div>
          <div style="padding-left:13px;">Llama 3.2 · Read-only SQL validation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# WORKSPACE PAGE HEADER
# ==========================================

page_descriptions = {
    "Overview": "A live snapshot of your database workspace and QueryMind activity.",
    "SQL Assistant": "Ask questions in natural language and inspect validated SQL results.",
    "Schema Canvas": "Explore tables, columns, keys and relationships.",
    "AI Dashboard": "Generate interactive dashboards from natural-language questions.",
    "Performance": "Track query execution times and identify slow queries.",
    "Security Auditor": "Review SQLite integrity, configuration and heuristic security findings.",
    "Data Lineage": "Trace source tables and columns through to query output fields.",
    "Database Health": "Profile table sizes and basic data-quality indicators.",
    "Index Lab": "Review index recommendations and benchmark candidate indexes.",
    "Database Connections": "Connect QueryMind to SQLite, PostgreSQL or MySQL.",
    "Database RAG Assistant": "Ask grounded questions using retrieved schema and optional sample records.",
}

st.markdown('<div class="qm-eyebrow">QueryMind workspace</div>', unsafe_allow_html=True)
st.title(selected_page)
st.caption(page_descriptions[selected_page])

# ==========================================
# OVERVIEW
# ==========================================

if selected_page == "Database Connections":
    st.subheader("Connect a database")
    st.info("SQLite remains the default. PostgreSQL and MySQL connections use SQLAlchemy drivers. Credentials are held only in this browser session and are not saved to project files.")
    db_type = st.selectbox("Database type", ["SQLite", "PostgreSQL", "MySQL"], key="db_connect_type")
    if db_type == "SQLite":
        sqlite_path = st.text_input("SQLite database path", value="data/querymind.db", help="Path relative to the QueryMind project folder, or an absolute path.")
        candidate_url = "sqlite:///" + sqlite_path.replace("\\", "/") if not sqlite_path.startswith("/") else "sqlite:////" + sqlite_path.lstrip("/")
        candidate_dialect, candidate_label = "sqlite", "SQLite · " + sqlite_path
    else:
        c1, c2 = st.columns(2)
        with c1:
            host = st.text_input("Host", value="localhost", key="db_host")
            port = st.number_input("Port", min_value=1, max_value=65535, value=5432 if db_type == "PostgreSQL" else 3306, key="db_port")
            username = st.text_input("Username", key="db_user")
        with c2:
            database_name = st.text_input("Database name", key="db_name")
            password = st.text_input("Password", type="password", key="db_password")
        if db_type == "PostgreSQL":
            candidate_url = f"postgresql+psycopg://{__import__('urllib.parse', fromlist=['quote_plus']).quote_plus(username)}:{__import__('urllib.parse', fromlist=['quote_plus']).quote_plus(password)}@{host}:{int(port)}/{database_name}"
            candidate_dialect, candidate_label = "postgresql", f"PostgreSQL · {database_name or host}"
        else:
            candidate_url = f"mysql+pymysql://{__import__('urllib.parse', fromlist=['quote_plus']).quote_plus(username)}:{__import__('urllib.parse', fromlist=['quote_plus']).quote_plus(password)}@{host}:{int(port)}/{database_name}"
            candidate_dialect, candidate_label = "mysql", f"MySQL · {database_name or host}"
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Test connection", type="primary", use_container_width=True):
            ok, message = test_connection(candidate_url)
            st.session_state["db_test_result"] = (ok, message)
            st.session_state["db_test_url"] = candidate_url
            st.session_state["db_test_dialect"] = candidate_dialect
            st.session_state["db_test_label"] = candidate_label
    with b2:
        if st.button("Use this database", use_container_width=True):
            if st.session_state.get("db_test_url") == candidate_url and st.session_state.get("db_test_result", (False,""))[0]:
                set_active_connection(candidate_url, candidate_dialect, candidate_label)
                st.success("Database connected. Reloading schema...")
                st.rerun()
            else:
                st.warning("Test this exact connection successfully before activating it.")
    if "db_test_result" in st.session_state:
        ok, msg = st.session_state["db_test_result"]
        (st.success if ok else st.error)(msg)
    st.caption(f"Active connection: {get_active_database_label()} ({get_active_dialect()})")
    if st.button("Switch back to default SQLite"):
        reset_connection(); st.rerun()
    try:
        active_schema = get_database_schema()
        st.write(f"Detected {len(active_schema)} tables.")
        st.dataframe(pd.DataFrame([{"table":t,"columns":len(d['columns'])} for t,d in active_schema.items()]), use_container_width=True, hide_index=True)
    except Exception as exc:
        st.error(f"Could not inspect active database: {exc}")

if selected_page == "Database RAG Assistant":
    st.subheader("Retrieval-Augmented Database Assistant")
    st.write("Index the active database schema and optionally a small sample of records. QueryMind retrieves relevant context and asks your local Ollama model to answer with table citations.")
    st.warning("If you include sample records, their contents are copied into the local ChromaDB index under data/querymind_chroma. Do not index sensitive or regulated data.")
    include_rows = st.checkbox("Include sample records (up to 3 rows per table)", value=False)
    embedding_model = st.text_input("Ollama embedding model", value="nomic-embed-text")
    chat_model = st.text_input("Ollama chat model", value="llama3.2")
    if st.button("Build / refresh database knowledge index", type="primary"):
        try:
            with st.spinner("Reading schema and creating local vector embeddings..."):
                count = index_database(include_sample_rows=include_rows, rows_per_table=3, embedding_model=embedding_model)
            st.success(f"Indexed {count} knowledge chunks in local ChromaDB.")
        except Exception as exc:
            st.error(f"Indexing failed: {exc}")
            st.info("Ensure Ollama is running and pull the embedding model with: ollama pull " + embedding_model)
    rag_question = st.text_area("Ask about your database", placeholder="Which tables contain customer and sales information?\nWhat relationships connect sales to products?", height=100)
    if st.button("Ask QueryMind", use_container_width=True) and rag_question.strip():
        try:
            with st.spinner("Retrieving relevant database context and generating an answer..."):
                answer, sources = ask_database(rag_question, embedding_model=embedding_model, chat_model=chat_model)
            st.markdown("### Answer")
            st.markdown(answer)
            st.caption("Retrieved sources: " + ", ".join(sorted({f"{x['table']} ({x['kind']})" for x in sources})))
        except Exception as exc:
            st.error(f"RAG assistant error: {exc}")
            st.info("Build the index first. Also run: ollama pull " + embedding_model)

if selected_page == "Overview":
    try:
        overview_schema = get_database_schema()
        overview_tables = len(overview_schema)
        overview_columns = sum(
            len(details.get("columns", [])) for details in overview_schema.values()
        )
        overview_relationships = sum(
            len(details.get("foreign_keys", [])) for details in overview_schema.values()
        )
        try:
            overview_history = get_query_execution_history(limit=5000)
        except Exception:
            overview_history = []

        overview_queries = len(overview_history)
        overview_avg = None
        if overview_history:
            overview_times = [
                float(item["execution_time_ms"])
                for item in overview_history
                if item.get("execution_time_ms") is not None
            ]
            if overview_times:
                overview_avg = sum(overview_times) / len(overview_times)

        st.markdown("### Workspace at a glance")
        overview_cols = st.columns(4)
        overview_cols[0].metric("Database Tables", overview_tables)
        overview_cols[1].metric("Schema Columns", overview_columns)
        overview_cols[2].metric("Tracked Queries", overview_queries)
        overview_cols[3].metric(
            "Average Query Time",
            f"{overview_avg:.2f} ms" if overview_avg is not None else "—",
        )

        st.markdown("### Explore QueryMind")
        tiles = [
            ("💬", "SQL Assistant", "Ask questions and generate safe SQL."),
            ("🧩", "Schema Canvas", "Explore your database structure."),
            ("📊", "AI Dashboard", "Turn questions into interactive charts."),
            ("⚡", "Performance", "Review query speed and execution history."),
            ("🛡️", "Security Auditor", "Inspect database security signals."),
            ("🔗", "Data Lineage", "Trace source columns to output fields."),
            ("🩺", "Database Health", "Profile data quality and table health."),
            ("🗂️", "Index Lab", "Review and benchmark index candidates."),
            ("🔌", "Database Connections", "Connect SQLite, PostgreSQL or MySQL."),
            ("🧠", "Database RAG Assistant", "Ask grounded questions about your data."),
        ]
        tile_cols = st.columns(3)
        for idx, (emoji, title, description) in enumerate(tiles):
            with tile_cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="min-height:88px;padding:2px 1px 0 1px;">
                          <div style="font-size:1.35rem;">{emoji}</div>
                          <div style="font-weight:750;color:#edf0f6;margin:5px 0;">{title}</div>
                          <div style="font-size:.82rem;color:#9aa4b4;">{description}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.button(
                        f"Open {title}  →",
                        key=f"overview_open_{idx}",
                        use_container_width=True,
                        on_click=navigate_to_page,
                        args=(title,),
                    )

        st.markdown("### Database tables")
        table_cols = st.columns(min(4, max(1, len(overview_schema))))
        for idx, (table_name, details) in enumerate(overview_schema.items()):
            with table_cols[idx % len(table_cols)]:
                st.markdown(
                    f"""
                    <div class="qm-panel">
                      <div style="color:#a99fff;font-size:.72rem;font-weight:700;">TABLE</div>
                      <div style="font-size:1rem;font-weight:700;color:#f1f3f7;">{table_name}</div>
                      <div style="color:#9aa4b4;font-size:.8rem;">
                        {len(details.get('columns', []))} columns
                        · {len(details.get('foreign_keys', []))} outgoing keys
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if overview_history:
            st.markdown("### Recent query activity")
            import pandas as pd

            recent_df = pd.DataFrame(overview_history[:8])
            keep_columns = [
                col
                for col in [
                    "created_at",
                    "source",
                    "question",
                    "execution_time_ms",
                    "rows_returned",
                ]
                if col in recent_df.columns
            ]
            if keep_columns:
                st.dataframe(
                    recent_df[keep_columns],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info(
                "Run your first SQL question to start building query activity history."
            )

        st.caption(
            f"Schema relationships declared in SQLite: {overview_relationships}. "
            "Overview metrics are read-only."
        )
    except Exception as overview_error:
        st.error(f"Overview could not load: {overview_error}")


if selected_page == "SQL Assistant":
    # ==========================================
    # HEADER
    # ==========================================

    st.markdown(
        '<div class="qm-eyebrow">Intelligent data workspace</div>',
        unsafe_allow_html=True,
    )
    st.title("🧠 QueryMind")
    st.subheader("AI-Powered SQL Assistant")
    st.caption("Ask questions about your database using natural language.")
    st.divider()

    # ==========================================
    # LOAD CONVERSATION
    # ==========================================

    messages = get_messages(st.session_state.active_session_id)

    # ==========================================
    # DISPLAY CHAT HISTORY
    # ==========================================

    for message in messages:
        role = message["role"]

        if role not in ["user", "assistant"]:
            continue

        with st.chat_message(role):
            st.markdown(message["content"])

            if message.get("sql_query"):
                with st.expander("View Generated SQL"):
                    st.code(message["sql_query"], language="sql")

    # ==========================================
    # CHAT INPUT
    # ==========================================

    user_question = st.chat_input("Ask something about your database...")

    if user_question:
        process_question(user_question, st.session_state.active_session_id)
        st.rerun()

    # ==========================================
    # SQL WORKSPACE EDITOR
    # ==========================================

    st.divider()
    st.markdown('<div class="qm-eyebrow">Query workspace</div>', unsafe_allow_html=True)
    st.subheader("SQL Editor")
    st.caption(
        "Write or review SQL, validate it, and execute it against your connected "
        "SQLite database. Only queries accepted by QueryMind's read-only validator can run."
    )

    # ==========================================
    # AI SQL SUGGESTIONS + SCHEMA-AWARE HELPERS
    # ==========================================
    with st.expander("✨ AI SQL Assistant & autocomplete", expanded=True):
        st.caption(
            "Describe the query you need to generate SQL with your local AI model, "
            "or insert schema-aware table/column suggestions and SQL templates."
        )
        ai_prompt_col, ai_button_col = st.columns([4, 1])
        with ai_prompt_col:
            ai_sql_prompt = st.text_input(
                "Describe the SQL query",
                key="ai_sql_suggestion_prompt",
                placeholder="e.g. Show total sales by product category",
            )
        with ai_button_col:
            st.write("")
            generate_suggestion = st.button(
                "Generate SQL",
                key="generate_sql_suggestion",
                type="primary",
                use_container_width=True,
            )

        if generate_suggestion:
            if not ai_sql_prompt.strip():
                st.warning("Describe the query you want to generate first.")
            else:
                try:
                    with st.spinner("Generating SQL with your local AI model..."):
                        suggested_sql = generate_sql(ai_sql_prompt.strip())
                    if not suggested_sql or suggested_sql.startswith("ERROR:"):
                        st.error(suggested_sql or "The AI model returned no SQL.")
                    else:
                        # Keep generated SQL in the editor; it is not executed automatically.
                        st.session_state["sql_editor_text"] = suggested_sql
                        st.session_state["sql_editor_message"] = (
                            "AI generated a draft. Validate it before running."
                        )
                        st.rerun()
                except Exception as suggestion_error:
                    st.error(f"SQL generation failed: {suggestion_error}")

        try:
            autocomplete_schema = get_database_schema()
            table_names = sorted(autocomplete_schema.keys())
            if table_names:
                schema_col, template_col = st.columns(2)
                with schema_col:
                    selected_table = st.selectbox(
                        "Table / column suggestions",
                        table_names,
                        key="sql_autocomplete_table",
                    )
                    selected_columns = [
                        column["name"]
                        for column in autocomplete_schema[selected_table].get(
                            "columns", []
                        )
                    ]
                    st.caption("Available columns: " + ", ".join(selected_columns))
                    chosen_column = (
                        st.selectbox(
                            "Choose a column to insert",
                            selected_columns,
                            key="sql_autocomplete_column",
                        )
                        if selected_columns
                        else None
                    )
                    if (
                        st.button("Insert selected column", key="insert_schema_column")
                        and chosen_column
                    ):
                        current_sql = st.session_state.get("sql_editor_text", "")
                        st.session_state["sql_editor_text"] = (
                            current_sql.rstrip()
                            + (" " if current_sql.strip() else "")
                            + f'"{selected_table}"."{chosen_column}"'
                        )
                        st.rerun()
                with template_col:
                    template_options = {
                        "SELECT all rows (preview)": f'SELECT *\nFROM "{table_names[0]}"\nLIMIT 100;',
                        "Count rows": f'SELECT COUNT(*) AS total_rows\nFROM "{table_names[0]}";',
                        "List distinct values": f'SELECT DISTINCT "{selected_columns[0] if selected_columns else "id"}"\nFROM "{table_names[0]}"\nLIMIT 100;',
                    }
                    chosen_template = st.selectbox(
                        "Quick SQL templates",
                        list(template_options.keys()),
                        key="sql_quick_template",
                    )
                    if st.button("Insert template", key="insert_sql_template"):
                        st.session_state["sql_editor_text"] = template_options[
                            chosen_template
                        ]
                        st.rerun()

                st.caption(
                    f"Schema loaded: {len(table_names)} tables. Suggestions are based on "
                    "the live SQLite schema; generated SQL must still pass validation."
                )
        except Exception as autocomplete_error:
            st.warning(f"Schema suggestions are unavailable: {autocomplete_error}")

    editor_left, editor_right = st.columns([3, 1])
    with editor_left:
        sql_editor_value = st.text_area(
            "SQL editor",
            key="sql_editor_text",
            height=220,
            label_visibility="collapsed",
            placeholder=(
                "SELECT p.product_name, SUM(s.quantity) AS total_quantity\n"
                "FROM sales s\n"
                "JOIN products p ON s.product_id = p.product_id\n"
                "GROUP BY p.product_name;"
            ),
        )
    with editor_right:
        st.markdown(
            """
            <div class="qm-panel" style="min-height:210px;">
              <div style="font-weight:700;color:#edf0f6;">Read-only mode</div>
              <div style="color:#9aa4b4;font-size:.82rem;margin:8px 0;">
                QueryMind validates SQL before execution and blocks write or schema
                modification statements.
              </div>
              <div style="color:#21a179;font-size:.8rem;">● SELECT queries only</div>
              <div style="color:#9aa4b4;font-size:.8rem;margin-top:5px;">SQLite database</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    run_col, validate_col, _ = st.columns([1, 1, 2])
    with run_col:
        run_manual_sql = st.button(
            "▶ Run Query",
            key="run_manual_sql",
            type="primary",
            use_container_width=True,
        )
    with validate_col:
        validate_manual_sql = st.button(
            "✓ Validate SQL",
            key="validate_manual_sql",
            use_container_width=True,
        )

    if validate_manual_sql or run_manual_sql:
        manual_sql = sql_editor_value.strip()
        if not manual_sql:
            st.session_state["sql_editor_message"] = "Enter a SQL query first."
            st.warning(st.session_state["sql_editor_message"])
        else:
            is_manual_valid, manual_validation_message = validate_sql(manual_sql)
            if not is_manual_valid:
                st.session_state["sql_editor_message"] = (
                    f"SQL validation failed: {manual_validation_message}"
                )
                st.error(st.session_state["sql_editor_message"])
            elif validate_manual_sql:
                st.session_state["sql_editor_message"] = (
                    "SQL validation passed. This query is accepted by the read-only validator."
                )
                st.success(st.session_state["sql_editor_message"])
            else:
                with st.spinner(
                    "Executing validated SQL and collecting query metrics..."
                ):
                    try:
                        manual_df, manual_message, manual_time, manual_plan = (
                            execute_query_with_metrics(manual_sql)
                        )
                        if manual_df is None:
                            st.session_state["sql_editor_message"] = (
                                manual_message or "Query execution failed."
                            )
                            st.error(st.session_state["sql_editor_message"])
                        else:
                            st.session_state.latest_df = manual_df
                            st.session_state.latest_sql = manual_sql
                            st.session_state.latest_question = "Manual SQL editor query"
                            st.session_state.latest_session_id = (
                                st.session_state.active_session_id
                            )
                            st.session_state.latest_execution_time = manual_time
                            st.session_state.latest_query_plan = manual_plan
                            st.session_state.explanation = ""
                            st.session_state.optimization_report = ""
                            try:
                                log_query_execution(
                                    sql_query=manual_sql,
                                    execution_time_ms=manual_time,
                                    rows_returned=len(manual_df),
                                    columns_returned=len(manual_df.columns),
                                    question="Manual SQL editor query",
                                    session_id=st.session_state.active_session_id,
                                    source="SQL Editor",
                                )
                            except Exception as monitor_error:
                                st.warning(
                                    "Query succeeded, but performance history could not "
                                    f"be saved: {monitor_error}"
                                )
                            st.session_state["sql_editor_message"] = (
                                f"Query executed successfully · {len(manual_df)} rows returned."
                            )
                            st.success(st.session_state["sql_editor_message"])
                    except Exception as manual_execution_error:
                        st.session_state["sql_editor_message"] = str(
                            manual_execution_error
                        )
                        st.error(
                            f"SQL execution failed: {st.session_state['sql_editor_message']}"
                        )

    if st.session_state.get("sql_editor_message") and not (
        validate_manual_sql or run_manual_sql
    ):
        st.caption(st.session_state["sql_editor_message"])

    if st.session_state.get("latest_sql"):
        st.download_button(
            "⬇ Download Latest SQL",
            data=st.session_state.latest_sql.encode("utf-8"),
            file_name="querymind_latest_query.sql",
            mime="text/sql",
            key="download_latest_sql",
        )

    # ==========================================
    # LATEST QUERY RESULTS
    # ==========================================

    if (
        st.session_state.latest_df is not None
        and st.session_state.latest_session_id == st.session_state.active_session_id
    ):
        df = st.session_state.latest_df

        st.divider()
        st.subheader("📊 Latest Query Results")

        # Query result summary
        col1, col2, col3 = st.columns(3)

        col1.metric("Total Rows", len(df))
        col2.metric("Total Columns", len(df.columns))

        execution_time = st.session_state.latest_execution_time

        if execution_time is not None:
            col3.metric("Execution Time", f"{execution_time:.3f} ms")
        else:
            col3.metric("Execution Time", "Unavailable")

        st.dataframe(df, use_container_width=True, hide_index=True)

        # ======================================
        # CSV EXPORT
        # ======================================

        st.download_button(
            "⬇ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="querymind_results.csv",
            mime="text/csv",
        )

        # ======================================
        # QUERY PERFORMANCE ANALYSIS
        # ======================================

        st.divider()
        st.subheader("⚡ Query Performance Analysis")

        query_plan = st.session_state.latest_query_plan

        if query_plan is not None and not query_plan.empty:
            with st.expander("View SQLite Query Execution Plan", expanded=True):
                st.dataframe(
                    query_plan,
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("**Performance Insights**")

            for insight in get_performance_insights(query_plan):
                st.write(f"• {insight}")
        else:
            st.info("SQLite query execution plan is not available for this query.")

        # ======================================
        # VISUALIZATION
        # ======================================

        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        categorical_columns = df.select_dtypes(exclude="number").columns.tolist()

        if numeric_columns:
            st.divider()
            st.subheader("Data Visualization")

            c1, c2 = st.columns(2)

            with c1:
                chart_type = st.selectbox(
                    "Chart Type",
                    ["Bar Chart", "Line Chart", "Scatter Plot"],
                )

            with c2:
                y_column = st.selectbox("Numeric Column", numeric_columns)

            x_options = categorical_columns or numeric_columns
            x_column = st.selectbox("X Axis", x_options)

            if chart_type == "Bar Chart":
                fig = px.bar(
                    df,
                    x=x_column,
                    y=y_column,
                    template="plotly_dark",
                )
            elif chart_type == "Line Chart":
                fig = px.line(
                    df,
                    x=x_column,
                    y=y_column,
                    markers=True,
                    template="plotly_dark",
                )
            else:
                fig = px.scatter(
                    df,
                    x=x_column,
                    y=y_column,
                    template="plotly_dark",
                )

            st.plotly_chart(fig, use_container_width=True)

        # ======================================
        # AI SQL EXPLANATION
        # ======================================

        st.divider()
        st.subheader("🤖 AI SQL Explanation")

        if st.button("Explain Latest SQL"):
            with st.spinner("Analyzing SQL and results..."):
                st.session_state.explanation = explain_sql(
                    st.session_state.latest_sql,
                    user_question=st.session_state.latest_question,
                    query_result=st.session_state.latest_df,
                )

        if st.session_state.explanation:
            st.markdown(st.session_state.explanation)

        # ======================================
        # AI SQL OPTIMIZATION
        # ======================================

        st.divider()
        st.subheader("🚀 AI SQL Optimization")

        st.caption(
            "Get recommendations to improve the latest SQL query. "
            "The suggested SQL is not executed automatically."
        )

        if st.button("Optimize Latest SQL"):
            with st.spinner("Analyzing SQL for optimization opportunities..."):
                try:
                    st.session_state.optimization_report = optimize_sql(
                        query=st.session_state.latest_sql,
                        user_question=st.session_state.latest_question,
                        query_plan=st.session_state.latest_query_plan,
                    )
                except Exception as e:
                    st.session_state.optimization_report = (
                        f"ERROR: SQL optimization failed: {str(e)}"
                    )

        if st.session_state.optimization_report:
            if st.session_state.optimization_report.startswith("ERROR:"):
                st.error(st.session_state.optimization_report)
            else:
                st.markdown(st.session_state.optimization_report)


if selected_page == "Schema Canvas":
    # ==========================================
    # INTERACTIVE DATABASE SCHEMA VISUALIZER
    # ==========================================

    st.divider()
    st.markdown('<div class="qm-eyebrow">Data model</div>', unsafe_allow_html=True)
    st.subheader("🕸️ Database Schema Canvas")
    st.caption(
        "Explore live tables as connected cards. Column types, primary keys, "
        "foreign keys and declared table relationships are shown on the canvas."
    )

    try:
        live_schema = get_database_schema()
        if not live_schema:
            st.info("No user tables were found in the connected database.")
        else:
            table_names = list(live_schema.keys())
            relationship_list = []
            for source_table, details in live_schema.items():
                for fk in details.get("foreign_keys", []):
                    if fk.get("references_table") in live_schema:
                        relationship_list.append(
                            {
                                "source": source_table,
                                "source_column": fk.get("column"),
                                "target": fk.get("references_table"),
                                "target_column": fk.get("references_column"),
                            }
                        )

            total_columns = sum(len(v.get("columns", [])) for v in live_schema.values())
            m1, m2, m3 = st.columns(3)
            m1.metric("Tables", len(table_names))
            m2.metric("Columns", total_columns)
            m3.metric("Relationships", len(relationship_list))

            # Arrange referenced tables on the left and referencing tables to the right.
            from collections import defaultdict

            parents = {name: set() for name in table_names}
            children = {name: set() for name in table_names}
            for rel in relationship_list:
                parents[rel["source"]].add(rel["target"])
                children[rel["target"]].add(rel["source"])

            layers_by_table = {}
            roots = [name for name in table_names if not children[name]]
            if not roots:
                roots = [table_names[0]]
            for name in roots:
                layers_by_table[name] = 0
            for _ in range(len(table_names) * 2):
                changed = False
                for name in table_names:
                    if name not in layers_by_table:
                        known = [
                            layers_by_table[p]
                            for p in parents[name]
                            if p in layers_by_table
                        ]
                        if known:
                            layers_by_table[name] = max(known) + 1
                            changed = True
                if not changed:
                    break
            for name in table_names:
                layers_by_table.setdefault(
                    name, max(layers_by_table.values(), default=0) + 1
                )

            layers = defaultdict(list)
            for name in table_names:
                layers[layers_by_table[name]].append(name)

            card_w, x_gap, y_gap = 3.1, 1.15, 0.42
            positions = {}
            max_y = 0
            for layer_no, names in layers.items():
                y_cursor = 0.0
                for name in names:
                    card_h = (
                        1.05 + max(1, len(live_schema[name].get("columns", []))) * 0.32
                    )
                    positions[name] = (layer_no * (card_w + x_gap), y_cursor, card_h)
                    y_cursor += card_h + y_gap
                max_y = max(max_y, y_cursor)

            fig = go.Figure()
            # Foreign-key connectors behind the cards.
            for rel in relationship_list:
                sx, sy, sh = positions[rel["source"]]
                tx, ty, th = positions[rel["target"]]
                x0, y0 = sx, sy + sh / 2
                x1, y1 = tx + card_w, ty + th / 2
                mid = (x0 + x1) / 2
                fig.add_shape(
                    type="path",
                    path=f"M {x0},{y0} C {mid},{y0} {mid},{y1} {x1},{y1}",
                    xref="x",
                    yref="y",
                    line=dict(color="#68748a", width=1.8),
                    layer="below",
                )
                fig.add_trace(
                    go.Scatter(
                        x=[x0, x1],
                        y=[y0, y1],
                        mode="markers",
                        marker=dict(size=5, color="#a99fff", opacity=0.01),
                        text=[
                            f"{rel['source']}.{rel['source_column']} → "
                            f"{rel['target']}.{rel['target_column']}"
                        ]
                        * 2,
                        hovertemplate="%{text}<extra>Foreign-key relationship</extra>",
                        showlegend=False,
                    )
                )

            accents = ["#8b7cff", "#20a77a", "#38bdf8", "#d28a4e", "#d45c72"]
            for idx, name in enumerate(table_names):
                x, y, h = positions[name]
                cols = live_schema[name].get("columns", [])
                accent = accents[idx % len(accents)]
                fig.add_shape(
                    type="rect",
                    x0=x,
                    y0=y,
                    x1=x + card_w,
                    y1=y + h,
                    line=dict(color="#414958", width=1),
                    fillcolor="#1b1f27",
                    layer="above",
                )
                fig.add_shape(
                    type="rect",
                    x0=x,
                    y0=y,
                    x1=x + card_w,
                    y1=y + 0.43,
                    line=dict(color="#303642", width=0.5),
                    fillcolor="#262b35",
                    layer="above",
                )
                fig.add_shape(
                    type="rect",
                    x0=x,
                    y0=y,
                    x1=x + 0.055,
                    y1=y + h,
                    line=dict(width=0),
                    fillcolor=accent,
                    layer="above",
                )
                fig.add_annotation(
                    x=x + 0.17,
                    y=y + 0.215,
                    xanchor="left",
                    yanchor="middle",
                    text=f"<b>▦  {name}</b>",
                    showarrow=False,
                    font=dict(size=12, color="#edf0f6"),
                )
                fig.add_annotation(
                    x=x + 0.16,
                    y=y + 0.62,
                    xanchor="left",
                    yanchor="middle",
                    text=f"<span style='color:#9aa4b4'>{len(cols)} columns</span>",
                    showarrow=False,
                    font=dict(size=9, color="#9aa4b4"),
                )
                row_y = y + 0.94
                for col in cols:
                    cname = col.get("name", "")
                    ctype = str(col.get("type") or "UNKNOWN").lower()
                    is_pk = bool(col.get("primary_key"))
                    is_fk = any(
                        fk.get("column") == cname
                        for fk in live_schema[name].get("foreign_keys", [])
                    )
                    tag = (
                        "  <span style='color:#e6b96c'>PK</span>"
                        if is_pk
                        else (
                            "  <span style='color:#a99fff'>FK</span>" if is_fk else ""
                        )
                    )
                    fig.add_shape(
                        type="line",
                        x0=x + 0.13,
                        y0=row_y - 0.145,
                        x1=x + card_w - 0.13,
                        y1=row_y - 0.145,
                        line=dict(color="#303641", width=0.55),
                        layer="above",
                    )
                    fig.add_annotation(
                        x=x + 0.16,
                        y=row_y,
                        xanchor="left",
                        yanchor="middle",
                        text=f"{cname}{tag}",
                        showarrow=False,
                        font=dict(size=9, color="#dce2eb"),
                    )
                    fig.add_annotation(
                        x=x + card_w - 0.15,
                        y=row_y,
                        xanchor="right",
                        yanchor="middle",
                        text=ctype[:15],
                        showarrow=False,
                        font=dict(size=8, color="#929dad"),
                    )
                    row_y += 0.32

            max_layer = max(layers) if layers else 0
            fig.update_layout(
                template="plotly_dark",
                height=max(440, min(950, int(max_y * 105 + 60))),
                margin=dict(l=24, r=24, t=20, b=20),
                paper_bgcolor="#15181f",
                plot_bgcolor="#15181f",
                showlegend=False,
                dragmode="pan",
                hoverlabel=dict(bgcolor="#252a34", bordercolor="#515a6b"),
                xaxis=dict(
                    visible=False,
                    range=[-0.2, max_layer * (card_w + x_gap) + card_w + 0.3],
                    showgrid=True,
                    gridcolor="rgba(255,255,255,.045)",
                    zeroline=False,
                ),
                yaxis=dict(
                    visible=False,
                    autorange="reversed",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,.045)",
                    zeroline=False,
                ),
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displaylogo": False,
                    "scrollZoom": True,
                    "modeBarButtonsToAdd": ["resetScale2d"],
                },
            )
            st.caption(
                "Drag to pan and scroll to zoom. PK = primary key; FK = foreign key. "
                "Only relationships declared in the SQLite schema are drawn."
            )

            st.markdown("### Inspect a table")
            selected_table = st.selectbox(
                "Select a table", table_names, key="schema_visualizer_selected_table"
            )
            selected_details = live_schema[selected_table]
            rows = []
            for col in selected_details.get("columns", []):
                fk_flag = any(
                    fk.get("column") == col["name"]
                    for fk in selected_details.get("foreign_keys", [])
                )
                rows.append(
                    {
                        "Column": col["name"],
                        "Data type": col.get("type") or "UNKNOWN",
                        "Key": (
                            "PK"
                            if col.get("primary_key")
                            else ("FK" if fk_flag else "—")
                        ),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            outgoing = selected_details.get("foreign_keys", [])
            if outgoing:
                st.markdown("**Foreign-key relationships**")
                for fk in outgoing:
                    st.write(
                        f"`{selected_table}.{fk['column']}` → `{fk['references_table']}.{fk['references_column']}`"
                    )
            incoming = [r for r in relationship_list if r["target"] == selected_table]
            if incoming:
                st.markdown("**Referenced by**")
                for rel in incoming:
                    st.write(
                        f"`{rel['source']}.{rel['source_column']}` → `{selected_table}.{rel['target_column']}`"
                    )

    except Exception as schema_visualizer_error:
        st.error(f"The schema visualizer could not load: {schema_visualizer_error}")


if selected_page == "AI Dashboard":
    # ==========================================
    # FEATURE 2: AI DASHBOARD GENERATOR
    # ==========================================

    st.divider()
    st.header("📊 AI Dashboard Generator")
    st.caption(
        "Describe the dashboard you want in natural language. QueryMind generates "
        "a read-only SQL query, validates it, executes it, and builds an interactive view."
    )

    dashboard_question = st.text_input(
        "What would you like to analyze?",
        placeholder="Example: Show total sales by product category",
        key="dashboard_question_input",
    )

    if st.button("✨ Generate Dashboard", key="generate_ai_dashboard"):
        st.session_state.dashboard_df = None
        st.session_state.dashboard_sql = ""
        st.session_state.dashboard_error = ""

        if not dashboard_question.strip():
            st.session_state.dashboard_error = "Enter a dashboard request first."
        else:
            with st.spinner("Generating and validating dashboard query..."):
                try:
                    generated_dashboard_sql = generate_sql(dashboard_question.strip())

                    if (
                        not generated_dashboard_sql
                        or generated_dashboard_sql.startswith("ERROR:")
                    ):
                        raise RuntimeError(
                            generated_dashboard_sql or "The AI did not return SQL."
                        )

                    is_dashboard_sql_valid, dashboard_validation_message = validate_sql(
                        generated_dashboard_sql
                    )
                    if not is_dashboard_sql_valid:
                        raise RuntimeError(
                            f"Generated SQL was rejected: {dashboard_validation_message}"
                        )

                    (
                        dashboard_df,
                        dashboard_execution_message,
                        dashboard_execution_time,
                        dashboard_query_plan,
                    ) = execute_query_with_metrics(generated_dashboard_sql)

                    if dashboard_df is None:
                        raise RuntimeError(
                            dashboard_execution_message or "The dashboard query failed."
                        )

                    st.session_state.dashboard_df = dashboard_df
                    st.session_state.dashboard_sql = generated_dashboard_sql
                    st.session_state.dashboard_question = dashboard_question.strip()
                    st.session_state.dashboard_execution_time = dashboard_execution_time
                    st.session_state.dashboard_query_plan = dashboard_query_plan

                    try:
                        log_query_execution(
                            sql_query=generated_dashboard_sql,
                            execution_time_ms=dashboard_execution_time,
                            rows_returned=len(dashboard_df),
                            columns_returned=len(dashboard_df.columns),
                            question=dashboard_question.strip(),
                            session_id=st.session_state.active_session_id,
                            source="AI Dashboard",
                        )
                    except Exception as monitor_error:
                        st.warning(
                            f"Dashboard generated, but performance history could not be saved: {monitor_error}"
                        )

                except Exception as dashboard_exception:
                    st.session_state.dashboard_error = str(dashboard_exception)

    if st.session_state.dashboard_error:
        st.error(st.session_state.dashboard_error)

    dashboard_result = st.session_state.dashboard_df

    if dashboard_result is not None:
        import pandas as pd

        st.markdown("### Generated Dashboard")
        dashboard_metric_1, dashboard_metric_2, dashboard_metric_3 = st.columns(3)
        dashboard_metric_1.metric("Result Rows", len(dashboard_result))
        dashboard_metric_2.metric("Result Columns", len(dashboard_result.columns))

        dashboard_runtime = st.session_state.get("dashboard_execution_time")
        dashboard_metric_3.metric(
            "Execution Time",
            (
                f"{dashboard_runtime:.3f} ms"
                if dashboard_runtime is not None
                else "Unavailable"
            ),
        )

        st.dataframe(dashboard_result, use_container_width=True, hide_index=True)

        numeric_dashboard_columns = dashboard_result.select_dtypes(
            include="number"
        ).columns.tolist()
        categorical_dashboard_columns = dashboard_result.select_dtypes(
            exclude="number"
        ).columns.tolist()

        if numeric_dashboard_columns:
            st.markdown("### Interactive Visualization")

            dashboard_chart_type = st.selectbox(
                "Visualization",
                ["Bar Chart", "Line Chart", "Area Chart", "Scatter Plot"],
                key="ai_dashboard_chart_type",
            )
            dashboard_y = st.selectbox(
                "Measure (Y-axis)", numeric_dashboard_columns, key="ai_dashboard_y"
            )

            dashboard_x_options = (
                categorical_dashboard_columns or numeric_dashboard_columns
            )
            dashboard_x = st.selectbox(
                "Category or X-axis", dashboard_x_options, key="ai_dashboard_x"
            )

            dashboard_figure = None
            if dashboard_chart_type == "Bar Chart":
                dashboard_figure = px.bar(
                    dashboard_result,
                    x=dashboard_x,
                    y=dashboard_y,
                    template="plotly_dark",
                    title=f"{dashboard_y} by {dashboard_x}",
                )
            elif dashboard_chart_type == "Line Chart":
                dashboard_figure = px.line(
                    dashboard_result,
                    x=dashboard_x,
                    y=dashboard_y,
                    markers=True,
                    template="plotly_dark",
                    title=f"{dashboard_y} over {dashboard_x}",
                )
            elif dashboard_chart_type == "Area Chart":
                dashboard_figure = px.area(
                    dashboard_result,
                    x=dashboard_x,
                    y=dashboard_y,
                    template="plotly_dark",
                    title=f"{dashboard_y} by {dashboard_x}",
                )
            else:
                dashboard_figure = px.scatter(
                    dashboard_result,
                    x=dashboard_x,
                    y=dashboard_y,
                    template="plotly_dark",
                    title=f"{dashboard_y} vs {dashboard_x}",
                )

            st.plotly_chart(
                dashboard_figure,
                use_container_width=True,
                config={"displaylogo": False},
            )

            st.markdown("### Key Metrics")
            metric_values = st.columns(min(4, len(numeric_dashboard_columns)))
            for metric_index, metric_column in enumerate(numeric_dashboard_columns[:4]):
                metric_series = pd.to_numeric(
                    dashboard_result[metric_column], errors="coerce"
                ).dropna()
                if not metric_series.empty:
                    metric_values[metric_index].metric(
                        f"Average {metric_column}", f"{metric_series.mean():,.2f}"
                    )
        else:
            st.info(
                "This query returned no numeric columns, so QueryMind displayed "
                "the result table without a numeric chart."
            )

        with st.expander("View Generated SQL"):
            st.code(st.session_state.dashboard_sql, language="sql")

        st.download_button(
            "⬇ Download Dashboard Data (CSV)",
            data=dashboard_result.to_csv(index=False).encode("utf-8"),
            file_name="querymind_dashboard_data.csv",
            mime="text/csv",
            key="download_ai_dashboard_csv",
        )

        st.caption(
            "Dashboard SQL is validated as a read-only query before execution. "
            "Review generated SQL before using results for business decisions."
        )


if selected_page == "Performance" and get_active_dialect() == "sqlite":
    # ==========================================
    # FEATURE 3: QUERY PERFORMANCE MONITORING
    # ==========================================

    st.divider()
    st.header("⚡ Query Performance Monitoring")
    st.caption(
        "Monitor successful SQL executions from chat and the AI Dashboard. "
        "Execution history is stored separately from your business database."
    )

    try:
        import pandas as pd
        from datetime import datetime

        monitor_records = get_query_execution_history(limit=5000)
        monitor_df = pd.DataFrame(monitor_records)

        if monitor_df.empty:
            st.info(
                "No monitored queries yet. Run SQL questions in QueryMind or generate "
                "an AI Dashboard, then return here to see performance metrics."
            )
        else:
            monitor_df["execution_time_ms"] = pd.to_numeric(
                monitor_df["execution_time_ms"], errors="coerce"
            )
            monitor_df["created_at"] = pd.to_datetime(
                monitor_df["created_at"], errors="coerce", utc=True
            )

            valid_times = monitor_df["execution_time_ms"].dropna()
            total_queries = len(monitor_df)
            average_time = float(valid_times.mean()) if not valid_times.empty else 0.0
            fastest_time = float(valid_times.min()) if not valid_times.empty else 0.0
            slowest_time = float(valid_times.max()) if not valid_times.empty else 0.0

            # A simple configurable starting threshold, not a universal definition of slow.
            slow_threshold_ms = st.number_input(
                "Slow query threshold (milliseconds)",
                min_value=0.0,
                value=100.0,
                step=10.0,
                help="Queries at or above this threshold are flagged for review.",
            )
            slow_count = (
                int((valid_times >= slow_threshold_ms).sum())
                if not valid_times.empty
                else 0
            )

            metric_a, metric_b, metric_c, metric_d = st.columns(4)
            metric_a.metric("Tracked Executions", f"{total_queries:,}")
            metric_b.metric("Average Time", f"{average_time:.3f} ms")
            metric_c.metric("Fastest Query", f"{fastest_time:.3f} ms")
            metric_d.metric("Slow Queries", f"{slow_count:,}")

            st.markdown("### Execution Time Trend")
            trend_df = monitor_df.dropna(
                subset=["created_at", "execution_time_ms"]
            ).copy()
            if not trend_df.empty:
                trend_df = trend_df.sort_values("created_at")
                trend_fig = px.line(
                    trend_df,
                    x="created_at",
                    y="execution_time_ms",
                    color="source",
                    markers=True,
                    template="plotly_dark",
                    title="Query execution time over time",
                )
                st.plotly_chart(trend_fig, use_container_width=True)
            else:
                st.info(
                    "There are no valid timestamps or execution-time values to chart."
                )

            st.markdown("### Query Activity")
            activity_df = (
                monitor_df.groupby("source", dropna=False)
                .size()
                .reset_index(name="executions")
            )
            activity_fig = px.bar(
                activity_df,
                x="source",
                y="executions",
                template="plotly_dark",
                title="Executions by QueryMind feature",
            )
            st.plotly_chart(activity_fig, use_container_width=True)

            st.markdown("### Slow Query Review")
            slow_df = monitor_df[
                monitor_df["execution_time_ms"].fillna(-1) >= slow_threshold_ms
            ].copy()
            if slow_df.empty:
                st.success("No executions meet the current slow-query threshold.")
            else:
                st.warning(
                    f"{len(slow_df)} execution(s) meet or exceed {slow_threshold_ms:.1f} ms."
                )
                st.dataframe(
                    slow_df[
                        [
                            "created_at",
                            "source",
                            "question",
                            "execution_time_ms",
                            "rows_returned",
                            "sql_query",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("### Search Query History")
            search_term = st.text_input(
                "Search by question or SQL text", key="monitor_history_search"
            )
            filtered_df = monitor_df.copy()
            if search_term.strip():
                needle = search_term.strip().lower()
                mask = filtered_df["question"].fillna("").str.lower().str.contains(
                    needle, regex=False
                ) | filtered_df["sql_query"].fillna("").str.lower().str.contains(
                    needle, regex=False
                )
                filtered_df = filtered_df[mask]

            st.dataframe(
                filtered_df[
                    [
                        "created_at",
                        "source",
                        "question",
                        "execution_time_ms",
                        "rows_returned",
                        "columns_returned",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Inspect SQL for an execution"):
                if not filtered_df.empty:
                    selected_execution = st.selectbox(
                        "Select execution ID",
                        filtered_df["id"].astype(int).tolist(),
                        key="monitor_selected_execution",
                    )
                    selected_row = filtered_df[
                        filtered_df["id"] == selected_execution
                    ].iloc[0]
                    st.code(str(selected_row["sql_query"]), language="sql")
                else:
                    st.caption("No executions match the current search.")

            csv_data = monitor_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Export Performance History (CSV)",
                data=csv_data,
                file_name="querymind_performance_history.csv",
                mime="text/csv",
                key="download_query_performance_history",
            )

            st.caption(
                "Performance history records successful executions only. "
                "Timings vary with cache state, data size and system load; use trends "
                "and query plans rather than treating one timing as definitive."
            )

    except Exception as monitor_ui_error:
        st.error(f"Query performance monitoring could not load: {monitor_ui_error}")


if selected_page == "Security Auditor" and get_active_dialect() == "sqlite":
    # ==========================================
    # FEATURE 4: DATABASE SECURITY AUDITOR
    # ==========================================

    st.divider()
    st.header("🛡️ Database Security Auditor")
    st.caption(
        "Run read-only SQLite integrity and configuration checks, identify potentially "
        "sensitive column names, and review monitored SQL patterns."
    )

    if "database_security_report" not in st.session_state:
        st.session_state.database_security_report = None

    if st.button("🔐 Run Security Audit", key="run_database_security_audit"):
        with st.spinner("Auditing database configuration, schema and monitored SQL..."):
            try:
                st.session_state.database_security_report = (
                    run_database_security_audit()
                )
            except Exception as security_error:
                st.session_state.database_security_report = {
                    "error": str(security_error)
                }

    security_report = st.session_state.database_security_report

    if security_report is None:
        st.info("Click **Run Security Audit** to inspect your database.")
    elif "error" in security_report:
        st.error(f"Security audit failed: {security_report['error']}")
    else:
        security_findings = security_report["findings"]
        high_findings = [
            item for item in security_findings if item["severity"] == "High"
        ]
        warning_findings = [
            item for item in security_findings if item["severity"] == "Warning"
        ]

        security_col1, security_col2, security_col3, security_col4 = st.columns(4)
        security_col1.metric("Tables Scanned", security_report["tables_scanned"])
        security_col2.metric("Queries Reviewed", security_report["history_scanned"])
        security_col3.metric("High Findings", len(high_findings))
        security_col4.metric("Warnings", len(warning_findings))

        if high_findings:
            st.error("The audit found high-priority items that need review.")
        elif warning_findings:
            st.warning("The audit found items worth reviewing.")
        else:
            st.success(
                "No high-priority or warning findings were detected by these checks."
            )

        st.markdown("### SQLite Configuration")
        config_a, config_b, config_c = st.columns(3)
        config_a.metric(
            "Foreign Keys",
            "Enabled" if security_report["foreign_keys_enabled"] else "Disabled",
        )
        config_b.metric("Journal Mode", security_report["journal_mode"].upper())
        config_c.metric(
            "Integrity Check", "Passed" if security_report["integrity_ok"] else "Review"
        )

        st.markdown("### Audit Findings")
        if security_findings:
            findings_df = pd.DataFrame(security_findings)
            st.dataframe(findings_df, use_container_width=True, hide_index=True)

        if security_report["sensitive_columns"]:
            st.markdown("### Potentially Sensitive Columns")
            st.dataframe(
                pd.DataFrame(security_report["sensitive_columns"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info(
                "No column names matched the built-in sensitive-name patterns. "
                "This does not prove that the database contains no sensitive data."
            )

        if security_report["risky_queries"]:
            st.markdown("### SQL Statements Requiring Review")
            st.dataframe(
                pd.DataFrame(security_report["risky_queries"]),
                use_container_width=True,
                hide_index=True,
            )

        if security_report["select_star_queries"]:
            with st.expander("Review SELECT * statements"):
                st.dataframe(
                    pd.DataFrame(security_report["select_star_queries"]),
                    use_container_width=True,
                    hide_index=True,
                )

        st.caption(
            "Scope limitation: this is a heuristic SQLite audit, not a penetration test, "
            "operating-system file-permission check, encryption verification, or full "
            "user/role access-control audit. Risky SQL matches are keyword-based and do "
            "not prove that a statement was executed."
        )


if selected_page == "Data Lineage":
    # ==========================================
    # FEATURE 5: DATA LINEAGE TRACKER
    # ==========================================

    st.divider()
    st.markdown(
        '<div class="qm-eyebrow">Data observability</div>', unsafe_allow_html=True
    )
    st.header("🔗 Data Lineage Tracker")
    st.caption(
        "Trace source tables and columns contributing to SQL output columns. "
        "This is static SQL analysis; it does not execute the selected query."
    )

    try:
        lineage_history = get_query_execution_history(limit=5000)
        lineage_history_options = {
            f"#{item['id']} · {item['source']} · {str(item.get('question') or item['sql_query'])[:90]}": item[
                "sql_query"
            ]
            for item in lineage_history
        }

        lineage_input_mode = st.radio(
            "Choose SQL source",
            ["Select from query history", "Enter SQL manually"],
            horizontal=True,
            key="lineage_input_mode",
        )

        lineage_sql = ""

        if lineage_input_mode == "Select from query history":
            if lineage_history_options:
                selected_lineage_label = st.selectbox(
                    "Select a previously executed query",
                    list(lineage_history_options.keys()),
                    key="lineage_history_selection",
                )
                lineage_sql = lineage_history_options[selected_lineage_label]
            else:
                st.info(
                    "No monitored query history is available yet. Run a query in "
                    "QueryMind or choose manual SQL analysis."
                )
        else:
            lineage_sql = st.text_area(
                "SQL query to analyze",
                height=160,
                placeholder=(
                    "SELECT p.product_name, SUM(s.quantity * p.price) AS revenue "
                    "FROM sales s JOIN products p ON s.product_id = p.product_id "
                    "GROUP BY p.product_name"
                ),
                key="manual_lineage_sql",
            )

        if st.button("🔍 Analyze Data Lineage", key="analyze_data_lineage"):
            st.session_state.data_lineage_report = None
            if not lineage_sql.strip():
                st.warning("Select a query or enter SQL before analyzing.")
            else:
                try:
                    is_lineage_sql_valid, lineage_validation_message = validate_sql(
                        lineage_sql
                    )
                    if not is_lineage_sql_valid:
                        raise ValueError(
                            f"Query validation failed: {lineage_validation_message}"
                        )

                    st.session_state.data_lineage_report = analyze_sql_lineage(
                        lineage_sql, dialect=get_active_dialect()
                    )
                except Exception as lineage_error:
                    st.session_state.data_lineage_report = {"error": str(lineage_error)}

        lineage_report = st.session_state.get("data_lineage_report")

        if lineage_report:
            if "error" in lineage_report:
                st.error(f"Lineage analysis failed: {lineage_report['error']}")
            else:
                lineage_metric_a, lineage_metric_b, lineage_metric_c = st.columns(3)
                lineage_metric_a.metric(
                    "Source Tables", len(lineage_report["source_tables"])
                )
                lineage_metric_b.metric(
                    "Source Columns", len(lineage_report["source_columns"])
                )
                lineage_metric_c.metric(
                    "Output Columns", len(lineage_report["projections"])
                )

                st.markdown("### Source Tables")
                st.write(
                    " · ".join(
                        f"`{table}`" for table in lineage_report["source_tables"]
                    )
                )

                st.markdown("### Column-Level Lineage")
                projection_rows = []
                for projection in lineage_report["projections"]:
                    projection_rows.append(
                        {
                            "Output Column": projection["output_column"],
                            "Source Columns": (
                                ", ".join(projection["source_columns"])
                                if projection["source_columns"]
                                else "No direct column reference detected"
                            ),
                            "SQL Expression": projection["expression"],
                        }
                    )

                st.dataframe(
                    pd.DataFrame(projection_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                st.markdown("### Lineage Canvas")
                st.caption(
                    "Source tables are shown as cards on the left and query outputs on the right. "
                    "Highlighted columns participate in the selected query; connector lines show "
                    "which source columns contribute to each output."
                )

                live_schema = get_database_schema()
                source_tables = [
                    table
                    for table in lineage_report["source_tables"]
                    if table in live_schema
                ]
                projections = lineage_report["projections"]

                # Resolve each reported source column to a live table/column.
                # SQL aliases may be used in the query, so fall back to matching the
                # column name against the selected source tables when the qualifier
                # is not the physical table name.
                source_column_refs = []
                for projection in projections:
                    for source_ref in projection.get("source_columns", []):
                        source_ref = str(source_ref).strip()
                        if "." in source_ref:
                            qualifier, column_name = source_ref.rsplit(".", 1)
                        else:
                            qualifier, column_name = "", source_ref

                        matching_tables = []
                        if qualifier in source_tables:
                            matching_tables = [qualifier]
                        else:
                            matching_tables = [
                                table
                                for table in source_tables
                                if any(
                                    str(col.get("name", "")).lower()
                                    == column_name.lower()
                                    for col in live_schema[table].get("columns", [])
                                )
                            ]

                        if len(matching_tables) == 1:
                            source_column_refs.append(
                                {
                                    "table": matching_tables[0],
                                    "column": column_name,
                                    "output": projection["output_column"],
                                    "source_label": source_ref,
                                }
                            )
                        elif qualifier and qualifier in live_schema:
                            source_column_refs.append(
                                {
                                    "table": qualifier,
                                    "column": column_name,
                                    "output": projection["output_column"],
                                    "source_label": source_ref,
                                }
                            )

                # A Plotly canvas is used for the connected-card layout so the
                # table cards and their relationship lines share one coordinate space.
                source_accent_palette = [
                    "#8b7cff",
                    "#21a179",
                    "#38bdf8",
                    "#d28a4e",
                    "#d45b72",
                ]
                card_width = 3.65
                source_x = 0.35
                output_x = 7.35
                top_padding = 0.25
                header_height = 0.58
                meta_height = 0.42
                row_height = 0.39
                card_gap = 0.48

                source_card_info = {}
                current_y = top_padding
                for table_index, table_name in enumerate(source_tables):
                    table_columns = live_schema[table_name].get("columns", [])
                    referenced_names = {
                        item["column"].lower()
                        for item in source_column_refs
                        if item["table"] == table_name
                    }
                    # Keep every table column visible, as in the reference design.
                    card_height = (
                        header_height
                        + meta_height
                        + max(1, len(table_columns)) * row_height
                        + 0.18
                    )
                    source_card_info[table_name] = {
                        "x": source_x,
                        "y": current_y,
                        "height": card_height,
                        "columns": table_columns,
                        "referenced": referenced_names,
                        "accent": source_accent_palette[
                            table_index % len(source_accent_palette)
                        ],
                    }
                    current_y += card_height + card_gap

                output_card_height = (
                    header_height
                    + meta_height
                    + max(1, len(projections)) * row_height
                    + 0.18
                )
                output_y = max(
                    top_padding, (current_y - card_gap - output_card_height) / 2
                )
                canvas_height = max(
                    current_y + 0.1, output_y + output_card_height + 0.25
                )

                # Calculate row centers before drawing connectors.
                source_row_centers = {}
                for table_name, info in source_card_info.items():
                    row_y = info["y"] + header_height + meta_height + row_height / 2
                    for column in info["columns"]:
                        source_row_centers[
                            (table_name, str(column.get("name", "")).lower())
                        ] = row_y
                        row_y += row_height

                output_row_centers = {}
                output_row_y = output_y + header_height + meta_height + row_height / 2
                for projection in projections:
                    output_row_centers[str(projection["output_column"])] = output_row_y
                    output_row_y += row_height

                lineage_canvas = go.Figure()

                # Draw links first so they sit behind the table cards.
                for edge in source_column_refs:
                    source_key = (edge["table"], edge["column"].lower())
                    if source_key not in source_row_centers:
                        continue
                    if edge["output"] not in output_row_centers:
                        continue

                    source_info = source_card_info[edge["table"]]
                    x0 = source_info["x"] + card_width
                    y0 = source_row_centers[source_key]
                    x1 = output_x
                    y1 = output_row_centers[edge["output"]]
                    curve_mid = (x0 + x1) / 2
                    edge_color = source_info["accent"]

                    lineage_canvas.add_shape(
                        type="path",
                        path=(
                            f"M {x0},{y0} C {curve_mid},{y0} "
                            f"{curve_mid},{y1} {x1},{y1}"
                        ),
                        xref="x",
                        yref="y",
                        line={"color": edge_color, "width": 2.0},
                        layer="below",
                    )
                    lineage_canvas.add_trace(
                        go.Scatter(
                            x=[x0, x1],
                            y=[y0, y1],
                            mode="markers",
                            marker={"size": 7, "color": edge_color, "opacity": 0.01},
                            text=[
                                f"{edge['source_label']} → Output: {edge['output']}",
                                f"{edge['source_label']} → Output: {edge['output']}",
                            ],
                            hovertemplate="%{text}<extra>Column lineage</extra>",
                            showlegend=False,
                        )
                    )

                # Source table cards.
                for table_name, info in source_card_info.items():
                    x, y = info["x"], info["y"]
                    card_height = info["height"]
                    accent = info["accent"]
                    columns = info["columns"]

                    lineage_canvas.add_shape(
                        type="rect",
                        x0=x,
                        y0=y,
                        x1=x + card_width,
                        y1=y + card_height,
                        line={"color": "#424958", "width": 1},
                        fillcolor="#1b1f27",
                        layer="above",
                    )
                    lineage_canvas.add_shape(
                        type="rect",
                        x0=x,
                        y0=y,
                        x1=x + card_width,
                        y1=y + header_height,
                        line={"color": "#303642", "width": 0.5},
                        fillcolor="#262b35",
                        layer="above",
                    )
                    lineage_canvas.add_shape(
                        type="rect",
                        x0=x,
                        y0=y,
                        x1=x + 0.065,
                        y1=y + card_height,
                        line={"width": 0},
                        fillcolor=accent,
                        layer="above",
                    )
                    lineage_canvas.add_annotation(
                        x=x + 0.19,
                        y=y + header_height / 2,
                        xanchor="left",
                        yanchor="middle",
                        text=f"<b>▦  {table_name}</b>",
                        showarrow=False,
                        font={"size": 12, "color": "#edf0f6"},
                    )
                    lineage_canvas.add_annotation(
                        x=x + card_width - 0.17,
                        y=y + header_height / 2,
                        xanchor="right",
                        yanchor="middle",
                        text="<span style='color:#21a179'>●</span>",
                        showarrow=False,
                        font={"size": 10},
                    )
                    lineage_canvas.add_annotation(
                        x=x + 0.18,
                        y=y + header_height + meta_height / 2,
                        xanchor="left",
                        yanchor="middle",
                        text=f"<span style='color:#9aa4b4'>{len(columns)} columns · SOURCE TABLE</span>",
                        showarrow=False,
                        font={"size": 8, "color": "#9aa4b4"},
                    )

                    row_y = y + header_height + meta_height + row_height / 2
                    for column in columns:
                        column_name = str(column.get("name", ""))
                        column_type = str(column.get("type") or "UNKNOWN").lower()
                        is_pk = bool(column.get("primary_key"))
                        is_fk = any(
                            fk.get("column") == column_name
                            for fk in live_schema[table_name].get("foreign_keys", [])
                        )
                        is_used = column_name.lower() in info["referenced"]
                        key_tag = (
                            "  <span style='color:#e7bd72'>PK</span>"
                            if is_pk
                            else (
                                "  <span style='color:#a99fff'>FK</span>"
                                if is_fk
                                else ""
                            )
                        )
                        used_tag = (
                            "  <span style='color:#54c9a0'>● USED</span>"
                            if is_used
                            else ""
                        )

                        lineage_canvas.add_shape(
                            type="line",
                            x0=x + 0.14,
                            y0=row_y - row_height / 2 + 0.015,
                            x1=x + card_width - 0.14,
                            y1=row_y - row_height / 2 + 0.015,
                            line={"color": "#303641", "width": 0.55},
                            layer="above",
                        )
                        lineage_canvas.add_annotation(
                            x=x + 0.18,
                            y=row_y,
                            xanchor="left",
                            yanchor="middle",
                            text=f"{column_name}{key_tag}{used_tag}",
                            showarrow=False,
                            font={
                                "size": 8.5,
                                "color": "#f0f2f7" if is_used else "#b3bbc8",
                            },
                        )
                        lineage_canvas.add_annotation(
                            x=x + card_width - 0.17,
                            y=row_y,
                            xanchor="right",
                            yanchor="middle",
                            text=column_type[:13],
                            showarrow=False,
                            font={"size": 8, "color": "#929dad"},
                        )
                        row_y += row_height

                # Query output card on the right.
                output_accent = "#21a179"
                lineage_canvas.add_shape(
                    type="rect",
                    x0=output_x,
                    y0=output_y,
                    x1=output_x + card_width,
                    y1=output_y + output_card_height,
                    line={"color": "#4b5364", "width": 1},
                    fillcolor="#1b1f27",
                    layer="above",
                )
                lineage_canvas.add_shape(
                    type="rect",
                    x0=output_x,
                    y0=output_y,
                    x1=output_x + card_width,
                    y1=output_y + header_height,
                    line={"color": "#303642", "width": 0.5},
                    fillcolor="#262b35",
                    layer="above",
                )
                lineage_canvas.add_shape(
                    type="rect",
                    x0=output_x,
                    y0=output_y,
                    x1=output_x + 0.065,
                    y1=output_y + output_card_height,
                    line={"width": 0},
                    fillcolor=output_accent,
                    layer="above",
                )
                lineage_canvas.add_annotation(
                    x=output_x + 0.19,
                    y=output_y + header_height / 2,
                    xanchor="left",
                    yanchor="middle",
                    text="<b>▤  query_output</b>",
                    showarrow=False,
                    font={"size": 12, "color": "#edf0f6"},
                )
                lineage_canvas.add_annotation(
                    x=output_x + card_width - 0.17,
                    y=output_y + header_height / 2,
                    xanchor="right",
                    yanchor="middle",
                    text="<span style='color:#21a179'>●</span>",
                    showarrow=False,
                    font={"size": 10},
                )
                lineage_canvas.add_annotation(
                    x=output_x + 0.18,
                    y=output_y + header_height + meta_height / 2,
                    xanchor="left",
                    yanchor="middle",
                    text=f"<span style='color:#9aa4b4'>{len(projections)} output columns · RESULT</span>",
                    showarrow=False,
                    font={"size": 8, "color": "#9aa4b4"},
                )

                row_y = output_y + header_height + meta_height + row_height / 2
                for projection in projections:
                    output_name = str(projection["output_column"])
                    expression = str(projection.get("expression", ""))
                    lineage_canvas.add_shape(
                        type="line",
                        x0=output_x + 0.14,
                        y0=row_y - row_height / 2 + 0.015,
                        x1=output_x + card_width - 0.14,
                        y1=row_y - row_height / 2 + 0.015,
                        line={"color": "#303641", "width": 0.55},
                        layer="above",
                    )
                    lineage_canvas.add_annotation(
                        x=output_x + 0.18,
                        y=row_y,
                        xanchor="left",
                        yanchor="middle",
                        text=f"<b>{output_name}</b>",
                        showarrow=False,
                        font={"size": 9, "color": "#f0f2f7"},
                    )
                    lineage_canvas.add_annotation(
                        x=output_x + card_width - 0.17,
                        y=row_y,
                        xanchor="right",
                        yanchor="middle",
                        text="OUTPUT",
                        showarrow=False,
                        font={"size": 7, "color": "#21a179"},
                    )
                    row_y += row_height

                canvas_width = output_x + card_width + 0.35
                lineage_canvas.update_layout(
                    template="plotly_dark",
                    height=max(430, min(1100, int(canvas_height * 105 + 70))),
                    margin={"l": 12, "r": 12, "t": 15, "b": 15},
                    paper_bgcolor="#15181f",
                    plot_bgcolor="#15181f",
                    showlegend=False,
                    dragmode="pan",
                    hoverlabel={
                        "bgcolor": "#252a34",
                        "bordercolor": "#515a6b",
                        "font": {"color": "#edf0f6"},
                    },
                    xaxis={
                        "visible": False,
                        "range": [0, canvas_width],
                        "showgrid": True,
                        "gridcolor": "rgba(255,255,255,.045)",
                        "zeroline": False,
                    },
                    yaxis={
                        "visible": False,
                        "range": [canvas_height, 0],
                        "showgrid": True,
                        "gridcolor": "rgba(255,255,255,.045)",
                        "zeroline": False,
                    },
                )
                st.plotly_chart(
                    lineage_canvas,
                    use_container_width=True,
                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                        "modeBarButtonsToAdd": ["resetScale2d"],
                    },
                )
                st.caption(
                    "Drag to pan and scroll to zoom. Colored connectors map source columns "
                    "to output columns. Green USED labels identify source fields used by "
                    "the selected SQL; PK and FK tags identify declared database keys."
                )

                st.markdown("### Join Relationships")
                if lineage_report["join_relationships"]:
                    st.dataframe(
                        pd.DataFrame(lineage_report["join_relationships"]),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info(
                        "No explicit JOIN ... ON equality relationships were detected."
                    )

                with st.expander("View analyzed SQL"):
                    st.code(lineage_report["sql"], language="sql")

                with st.expander("Lineage interpretation notes"):
                    for note in lineage_report["notes"]:
                        st.write(f"• {note}")

    except Exception as lineage_ui_error:
        st.error(f"Data lineage tracker could not load: {lineage_ui_error}")


if selected_page == "Index Lab" and get_active_dialect() == "sqlite":
    # ==========================================
    # INDEX MANAGEMENT
    # ==========================================

    st.divider()
    st.subheader("🗂️ Index Management")
    st.caption(
        "Review potential database indexes. Nothing is created unless you "
        "select a recommendation, confirm it, and click Apply."
    )

    try:
        index_recommendations = generate_index_recommendations()

        if not index_recommendations:
            st.info("No new index recommendations are currently available.")
        else:
            st.write(
                f"QueryMind identified **{len(index_recommendations)}** "
                "potential index candidate(s)."
            )

            for number, recommendation in enumerate(index_recommendations, start=1):
                table_name = recommendation["table"]
                column_name = recommendation["column"]
                index_label = f"{table_name}.{column_name}"

                with st.expander(f"Recommendation {number}: {index_label}"):
                    st.markdown(f"**Table:** `{table_name}`")
                    st.markdown(f"**Column:** `{column_name}`")
                    st.write(f"**Reason:** {recommendation['reason']}")
                    st.write(f"**Potential benefit:** {recommendation['benefit']}")
                    st.code(recommendation["sql"], language="sql")

                    confirmation_key = f"confirm_index_{table_name}_{column_name}"
                    apply_key = f"apply_index_{table_name}_{column_name}"

                    confirmed = st.checkbox(
                        f"I understand this will create an index on {index_label}.",
                        key=confirmation_key,
                    )

                    if st.button(
                        f"Apply Index: {index_label}",
                        key=apply_key,
                        disabled=not confirmed,
                    ):
                        success, message = apply_recommended_index(
                            table_name,
                            column_name,
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            st.caption(
                "Note: Indexes can improve some filters and joins, but they also "
                "use storage and can slow writes. Benchmark your real workload "
                "before keeping an index, especially with this small sample database."
            )

    except Exception as e:
        st.error(f"Index management could not load: {e}")

    # ==========================================
    # INDEX PERFORMANCE BENCHMARK
    # ==========================================

    st.divider()
    st.subheader("📈 Index Performance Benchmark")
    st.caption(
        "Compare query performance with and without candidate indexes. "
        "Tests use temporary database copies; the original database is not modified."
    )

    if st.button("▶ Run All Index Benchmarks", key="run_all_index_benchmarks"):
        with st.spinner("Benchmarking index candidates..."):
            try:
                st.session_state.index_benchmark_results = run_all_benchmarks()
            except Exception as e:
                st.session_state.index_benchmark_results = []
                st.error(f"Benchmark failed: {e}")

    benchmark_results = st.session_state.index_benchmark_results

    if benchmark_results is None:
        st.info("Run the benchmark to compare all configured index candidates.")
    elif not benchmark_results:
        st.warning("No benchmark results are available.")
    else:
        import pandas as pd

        benchmark_df = pd.DataFrame(
            [
                {
                    "Index Candidate": f"{item['table']}.{item['column']}",
                    "Median Before (ms)": item["before_median"],
                    "Median After (ms)": item["after_median"],
                    "Performance Difference (%)": item["improvement_percent"],
                }
                for item in benchmark_results
            ]
        )

        st.dataframe(
            benchmark_df.style.format(
                {
                    "Median Before (ms)": "{:.6f}",
                    "Median After (ms)": "{:.6f}",
                    "Performance Difference (%)": "{:+.2f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        chart_df = benchmark_df.melt(
            id_vars=["Index Candidate"],
            value_vars=["Median Before (ms)", "Median After (ms)"],
            var_name="Benchmark",
            value_name="Median Execution Time (ms)",
        )

        benchmark_fig = px.bar(
            chart_df,
            x="Index Candidate",
            y="Median Execution Time (ms)",
            color="Benchmark",
            barmode="group",
            title="Median Query Time: Before vs After Index",
            template="plotly_dark",
        )
        st.plotly_chart(benchmark_fig, use_container_width=True)

        st.markdown("**Benchmark interpretation**")
        for item in benchmark_results:
            difference = item["improvement_percent"]
            label = f"{item['table']}.{item['column']}"
            if difference > 0:
                st.write(
                    f"• `{label}`: median time was {difference:.2f}% lower "
                    "in the indexed test."
                )
            elif difference < 0:
                st.write(
                    f"• `{label}`: median time was {abs(difference):.2f}% higher "
                    "in the indexed test."
                )
            else:
                st.write(f"• `{label}`: no median timing difference was measured.")

        with st.expander("View detailed query plans"):
            for item in benchmark_results:
                st.markdown(f"**{item['table']}.{item['column']}**")
                before_col, after_col = st.columns(2)
                with before_col:
                    st.caption("Before index")
                    for detail in item["before_plan"]:
                        st.code(detail)
                with after_col:
                    st.caption("After index")
                    for detail in item["after_plan"]:
                        st.code(detail)

        st.caption(
            "Timings can vary with cache state and system load. A faster result "
            "on a small sample does not guarantee production improvement."
        )


if selected_page == "Database Health" and get_active_dialect() == "sqlite":
    # ==========================================
    # DATABASE HEALTH ANALYSIS
    # ==========================================

    st.divider()
    st.subheader("🩺 Database Health Analysis")
    st.caption(
        "Profile table sizes, NULL values, blank text values, duplicate rows, "
        "and schema details. This analysis is read-only."
    )

    if st.button("🔍 Analyze Database Health", key="analyze_database_health"):
        with st.spinner("Profiling database tables and checking data quality..."):
            try:
                st.session_state.database_health_report = get_database_health_report()
            except Exception as e:
                st.session_state.database_health_report = {"error": str(e)}

    health_report = st.session_state.database_health_report

    if health_report is None:
        st.info("Click **Analyze Database Health** to generate a health report.")
    elif "error" in health_report:
        st.error(f"Database health analysis failed: {health_report['error']}")
    else:
        health_col1, health_col2, health_col3, health_col4 = st.columns(4)
        health_col1.metric(
            "Health Score",
            f"{health_report['health_score']}/100",
            help="Heuristic score based on empty tables, NULLs, blanks, and duplicate rows.",
        )
        health_col2.metric("Tables", health_report["total_tables"])
        health_col3.metric("Total Records", health_report["total_rows"])
        health_col4.metric("Duplicate Rows", health_report["total_duplicate_rows"])

        if health_report["health_status"] == "Healthy":
            st.success(f"Database status: {health_report['health_status']}")
        elif health_report["health_status"] == "Needs Review":
            st.warning(f"Database status: {health_report['health_status']}")
        else:
            st.error(f"Database status: {health_report['health_status']}")

        quality_col1, quality_col2, quality_col3 = st.columns(3)
        quality_col1.metric("NULL Cells", health_report["total_null_cells"])
        quality_col2.metric("Blank Text Cells", health_report["total_blank_cells"])
        quality_col3.metric("Empty Tables", health_report["empty_tables"])

        import pandas as pd

        table_summary = pd.DataFrame(
            [
                {
                    "Table": item["table"],
                    "Rows": item["row_count"],
                    "Columns": item["column_count"],
                    "Duplicate Rows": item["duplicate_rows"],
                    "NULL Cells": item["null_cells"],
                    "Blank Text Cells": item["blank_cells"],
                    "Status": "Empty" if item["empty"] else "Has Records",
                }
                for item in health_report["table_reports"]
            ]
        )

        st.markdown("**Table Overview**")
        if not table_summary.empty:
            st.dataframe(table_summary, use_container_width=True, hide_index=True)
            rows_chart = px.bar(
                table_summary,
                x="Table",
                y="Rows",
                title="Records per Table",
                template="plotly_dark",
            )
            st.plotly_chart(rows_chart, use_container_width=True)

        st.markdown("**Column-Level Data Quality**")
        for table in health_report["table_reports"]:
            with st.expander(
                f"{table['table']} — {table['row_count']} rows, "
                f"{table['column_count']} columns"
            ):
                column_df = pd.DataFrame(table["columns"])
                if not column_df.empty:
                    st.dataframe(
                        column_df,
                        use_container_width=True,
                        hide_index=True,
                    )

                if table["foreign_keys"]:
                    st.markdown("**Foreign Key Relationships**")
                    for fk in table["foreign_keys"]:
                        st.write(
                            f"• `{fk['column']}` → "
                            f"`{fk['references_table']}.{fk['references_column']}`"
                        )

        st.markdown("**Data Quality Observations**")
        if not health_report["observations"]:
            st.success("No basic data-quality issues were detected.")
        else:
            for observation in health_report["observations"]:
                if observation["severity"] == "High":
                    st.error(observation["message"])
                elif observation["severity"] == "Warning":
                    st.warning(observation["message"])
                else:
                    st.info(observation["message"])

        st.caption(
            "The score is a heuristic indicator, not a formal quality certification. "
            "Duplicate rows are identical across all columns and may be valid depending "
            "on business rules. This analyzer does not modify or delete data."
        )


# ==========================================
# FOOTER
# ==========================================

st.divider()
st.caption("QueryMind | Python • Ollama • Llama 3.2 • SQLite • Streamlit • SQLGlot")


# SQLite-only diagnostic tools are intentionally restricted for external connections.
if get_active_dialect() != "sqlite" and selected_page in {"Performance", "Security Auditor", "Database Health", "Index Lab"}:
    st.info("This diagnostic module currently uses SQLite-specific inspection commands. Switch to the default SQLite database to use this page. SQL Assistant, Schema Canvas, Database Connections and Database RAG Assistant support the active SQLAlchemy connection.")
