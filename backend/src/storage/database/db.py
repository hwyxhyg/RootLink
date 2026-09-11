"""Database configuration for the optional persistent checkpointer."""

import os


def get_db_url() -> str:
    """Return the PostgreSQL URL supplied by the deployment environment."""
    return os.getenv("PGDATABASE_URL", "").strip()


__all__ = ["get_db_url"]
