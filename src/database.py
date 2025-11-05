import os
import sqlite3
import threading
from datetime import datetime
from typing import Optional

from src.logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "housing.db")


class DatabaseManager:
    _instance = None
    _local = threading.local()

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        if not self._initialized:
            self.db_path = db_path or DB_PATH
            logger.info(f"Initializing DatabaseManager with path: {self.db_path}")
            self._initialized = True

    def __del__(self):
        self.close_connection()
        DatabaseManager._instance = None

    def close_connection(self):
        if hasattr(self._local, "connection") and self._local.connection:
            logger.debug("Closing database connection")
            self._local.connection.close()
            self._local.connection = None

    def get_connection(self) -> sqlite3.Connection:
        """Get a thread-local connection"""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            logger.debug(f"Creating new database connection to {self.db_path}")
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            # Initialize schema on first connection (idempotent operation)
            self._init_schema()
        return self._local.connection

    @property
    def _connection(self) -> sqlite3.Connection:
        """Property to access thread-local connection"""
        return self.get_connection()

    def _init_schema(self):
        logger.debug("Initializing database schema")
        cursor = self._connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token)")

        self._connection.commit()
        logger.debug("Database schema initialized")

    def create_api_token(self, token: str, expires_at: Optional[datetime] = None):
        cursor = self._connection.cursor()
        try:
            logger.debug(f"Creating API token (expires_at: {expires_at})")
            cursor.execute(
                "INSERT INTO api_tokens (token, expires_at) VALUES (?, ?)",
                (token, expires_at),
            )
            self._connection.commit()
            logger.debug(f"API token created successfully with ID: {cursor.lastrowid}")
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating API token: {e}", exc_info=True)
            self._connection.rollback()
            raise

    def get_api_tokens(self) -> list[dict]:
        cursor = self._connection.cursor()
        logger.debug("Retrieving all active API tokens")
        cursor.execute("SELECT * FROM api_tokens WHERE is_active = 1")
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        logger.debug(f"Retrieved {len(result)} active tokens")
        return result

    def deactivate_api_token(self, token: str) -> bool:
        cursor = self._connection.cursor()
        try:
            logger.debug(f"Deactivating API token: {token[:8]}...")
            cursor.execute("UPDATE api_tokens SET is_active = 0 WHERE token = ?", (token,))
            self._connection.commit()
            success = cursor.rowcount > 0
            if success:
                logger.debug("Token deactivated successfully")
            else:
                logger.warning("Token not found for deactivation")
            return success
        except Exception as e:
            logger.error(f"Error deactivating API token: {e}", exc_info=True)
            self._connection.rollback()
            raise

    def validate_api_token(self, token: str) -> bool:
        """Check if token exists and is active"""
        cursor = self._connection.cursor()
        logger.debug(f"Validating API token: {token[:8]}...")
        cursor.execute(
            """
            SELECT id FROM api_tokens
            WHERE token = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        """,
            (token,),
        )
        result = cursor.fetchone()
        is_valid = result is not None
        if not is_valid:
            logger.warning(f"Token validation failed: {token[:8]}...")
        return is_valid
