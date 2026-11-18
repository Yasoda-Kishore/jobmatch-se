"""One place for the database connection."""
import psycopg
from pgvector.psycopg import register_vector

DB_URL = "postgresql://jobmatch:jobmatch@localhost:5432/jobmatch"


def connect() -> psycopg.Connection:
    """Open a connection that understands pgvector's vector type."""
    conn = psycopg.connect(DB_URL)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn