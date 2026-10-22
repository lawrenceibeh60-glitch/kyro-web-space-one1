"""PostgreSQL-backed durable project storage for deployed KAE instances.

Set DATABASE_URL to a managed PostgreSQL connection string in production.
Filesystem storage remains available for local/offline development.
"""
import json
import os
import threading
from pathlib import Path

import config

_lock = threading.RLock()
_ready_url = None


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
    # The service may reconnect to a different DATABASE_URL during tests,
    # previews, or runtime reconfiguration. Cache schema readiness per URL,
    # never as one process-wide boolean.
    global _ready_url
    database_url = _url()
    if _ready_url == database_url:
        return
    with _lock:
        if _ready_url == database_url:
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kae_storage_migrations (
                name TEXT PRIMARY KEY,
                completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()
        # Import legacy JSON projects once, without overwriting anything already in
        # PostgreSQL. This keeps existing work when DATABASE_URL is first enabled.
        marker = conn.execute(
            "SELECT 1 FROM kae_storage_migrations WHERE name = %s",
            ("filesystem-projects-v1",),
        ).fetchone()
        if not marker:
            root = Path(config.PROJECTS_DIR)
            if root.exists():
                for project_file in root.glob("*/project.json"):
                    try:
                        with project_file.open("r", encoding="utf-8") as handle:
                            document = json.load(handle)
                        project_id = document.get("id")
                        if not isinstance(project_id, str) or not project_id:
                            continue
                        from psycopg.types.json import Jsonb
                        conn.execute(
                            "INSERT INTO kae_projects (id, document) VALUES (%s, %s) "
                            "ON CONFLICT (id) DO NOTHING",
                            (project_id, Jsonb(document)),
                        )
                    except (OSError, ValueError, TypeError):
                        # Leave unreadable legacy files untouched for manual recovery.
                        continue
            conn.execute(
                "INSERT INTO kae_storage_migrations (name) VALUES (%s) "
                "ON CONFLICT (name) DO NOTHING",
                ("filesystem-projects-v1",),
            )
            conn.commit()
        _ready_url = database_url


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
