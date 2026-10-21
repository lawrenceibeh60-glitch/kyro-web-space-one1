"""PostgreSQL-backed durable project storage for deployed KAE instances.

Set DATABASE_URL to a managed PostgreSQL connection string in production.
Filesystem storage remains available for local/offline development.
"""
import os
import threading

_lock = threading.RLock()
_ready = False


def configured():
    return bool(os.environ.get("DATABASE_URL", "").strip())


def _url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return url


def _connect():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL storage is enabled but psycopg is missing. "
            "Install the project requirements."
        ) from exc
    return psycopg.connect(_url(), row_factory=dict_row, connect_timeout=10)


def _ensure_schema(conn):
    global _ready
    if _ready:
        return
    with _lock:
        if _ready:
            return
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kae_projects (
                id TEXT PRIMARY KEY,
                document JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS kae_projects_updated_at_idx "
            "ON kae_projects (updated_at DESC)"
        )
        conn.commit()
        _ready = True


def exists(project_id):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT 1 FROM kae_projects WHERE id = %s", (project_id,)
        ).fetchone()
        return row is not None


def list_ids():
    with _connect() as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id FROM kae_projects ORDER BY id"
        ).fetchall()
        return [row["id"] for row in rows]


def load(project_id):
    with _connect() as conn:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT document FROM kae_projects WHERE id = %s", (project_id,)
        ).fetchone()
        return row["document"] if row else None


def save(project_id, document):
    from psycopg.types.json import Jsonb

    with _connect() as conn:
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO kae_projects (id, document)
            VALUES (%s, %s)
            ON CONFLICT (id) DO UPDATE
              SET document = EXCLUDED.document, updated_at = NOW()
            """,
            (project_id, Jsonb(document)),
        )
        conn.commit()


def delete(project_id):
    with _connect() as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            "DELETE FROM kae_projects WHERE id = %s", (project_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
