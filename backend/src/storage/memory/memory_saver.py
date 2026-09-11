"""LangGraph checkpointer selection for standalone deployments."""

import logging
from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from src.storage.database.db import get_db_url


logger = logging.getLogger(__name__)


class MemoryManager:
    """Create one synchronous checkpointer shared by both language agents."""

    _instance: Optional["MemoryManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._checkpointer = None
            cls._instance._pool = None
        return cls._instance

    def get_checkpointer(self) -> BaseCheckpointSaver:
        if self._checkpointer is not None:
            return self._checkpointer

        db_url = get_db_url()
        if not db_url:
            logger.warning(
                "PGDATABASE_URL is not set; using in-memory conversation history."
            )
            self._checkpointer = InMemorySaver()
            return self._checkpointer

        try:
            self._pool = ConnectionPool(
                conninfo=db_url,
                min_size=1,
                max_size=10,
                timeout=15,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                },
            )
            self._checkpointer = PostgresSaver(self._pool)
            self._checkpointer.setup()
            logger.info("Persistent PostgreSQL conversation memory initialized.")
        except Exception:
            logger.exception(
                "PostgreSQL memory initialization failed; using in-memory history."
            )
            if self._pool is not None:
                self._pool.close()
                self._pool = None
            self._checkpointer = InMemorySaver()

        return self._checkpointer


_memory_manager: Optional[MemoryManager] = None


def get_memory_saver() -> BaseCheckpointSaver:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager.get_checkpointer()
