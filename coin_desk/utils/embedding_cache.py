"""
SQLite-based cache for text embeddings.

Stores embeddings locally to reduce API calls and improve performance.
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from django.conf import settings

logger = logging.getLogger('coin_desk')

# Use Django's BASE_DIR for proper path resolution
DB_PATH = settings.BASE_DIR / "coin_desk" / "utils" / "embedding_cache.sqlite3"


def get_db_connection() -> sqlite3.Connection:
    """
    Get database connection and ensure table exists.

    Returns:
        SQLite connection object.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text TEXT PRIMARY KEY,
                embedding TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create index for potential cache cleanup by date
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON embedding_cache(created_at)
        """)
        conn.commit()
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to embedding cache database: {e}")
        raise


def get_cached_embedding(text: str) -> Optional[List[float]]:
    """
    Retrieve embedding from cache.

    Args:
        text: Text to look up.

    Returns:
        Cached embedding vector or None if not found.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT embedding FROM embedding_cache WHERE text = ?", (text,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached embedding: {e}")
        return None


def save_embedding(text: str, embedding: List[float]) -> None:
    """
    Save embedding to cache.

    Args:
        text: Text that was embedded.
        embedding: Embedding vector to cache.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO embedding_cache (text, embedding) VALUES (?, ?)",
            (text, json.dumps(embedding))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving embedding to cache: {e}")
