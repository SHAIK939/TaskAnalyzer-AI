import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "task_analyzer.db"


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database():
    """Idempotent schema initialization. Safe on every Streamlit rerun."""
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT,
            password TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New conversation',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
            ON conversations(user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id, id);
        """)

        # Safe migrations for the user's existing database.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        if "password_hash" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if "updated_at" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")


def create_user(username, email, password_hash):
    username, email = username.strip(), email.strip().lower()
    if not username or not email:
        return False, "Username and email are required."
    try:
        with connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                return False, "An account with this email already exists."
            timestamp = now()
            conn.execute(
                """INSERT INTO users(username,email,password_hash,created_at,updated_at)
                   VALUES(?,?,?,?,?)""",
                (username, email, password_hash, timestamp, timestamp),
            )
        return True, "Account created successfully."
    except sqlite3.Error as exc:
        return False, f"Database error: {exc}"


def get_user_by_email(email):
    with connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()


def get_user_by_id(user_id):
    with connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_conversation(user_id, title="New conversation"):
    timestamp = now()
    with connection() as conn:
        cur = conn.execute(
            """INSERT INTO conversations(user_id,title,created_at,updated_at)
               VALUES(?,?,?,?)""",
            (user_id, title.strip() or "New conversation", timestamp, timestamp),
        )
        return cur.lastrowid


def get_conversations(user_id, query=""):
    sql = """SELECT * FROM conversations WHERE user_id = ?"""
    params = [user_id]
    if query.strip():
        sql += " AND title LIKE ?"
        params.append(f"%{query.strip()}%")
    sql += " ORDER BY updated_at DESC, id DESC"
    with connection() as conn:
        return conn.execute(sql, params).fetchall()


def conversation_belongs_to(conversation_id, user_id):
    with connection() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE id=? AND user_id=?",
            (conversation_id, user_id),
        ).fetchone()
        return bool(row)


def get_messages(conversation_id, user_id):
    with connection() as conn:
        return conn.execute(
            """SELECT m.* FROM messages m
               JOIN conversations c ON c.id=m.conversation_id
               WHERE m.conversation_id=? AND c.user_id=?
               ORDER BY m.id ASC""",
            (conversation_id, user_id),
        ).fetchall()


def save_message(conversation_id, role, content):
    timestamp = now()
    with connection() as conn:
        conn.execute(
            """INSERT INTO messages(conversation_id,role,content,created_at)
               VALUES(?,?,?,?)""",
            (conversation_id, role, content, timestamp),
        )
        conn.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (timestamp, conversation_id),
        )


def update_conversation_title(conversation_id, user_id, title):
    with connection() as conn:
        conn.execute(
            """UPDATE conversations SET title=?,updated_at=?
               WHERE id=? AND user_id=?""",
            (title.strip() or "New conversation", now(), conversation_id, user_id),
        )


def delete_conversation(conversation_id, user_id):
    with connection() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id=? AND user_id=?",
            (conversation_id, user_id),
        )
        return cur.rowcount > 0
