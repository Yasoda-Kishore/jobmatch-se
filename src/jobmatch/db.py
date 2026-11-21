"""One place for the database connection."""
import os

import psycopg
from pgvector.psycopg import register_vector

# Read from the environment, so the same code works on your laptop and inside Docker
DB_URL = os.getenv("DATABASE_URL", "postgresql://jobmatch:jobmatch@localhost:5432/jobmatch")


def connect() -> psycopg.Connection:
    """Open a connection that understands pgvector's vector type."""
    conn = psycopg.connect(DB_URL)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn