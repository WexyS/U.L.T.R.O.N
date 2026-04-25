"""Unified Database Access for Ultron AGI.

Provides a standardized way to connect to SQLite with WAL mode and other
optimizations to prevent 'database is locked' errors and improve performance.
"""

import aiosqlite
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger("ultron.memory.base_db")

@asynccontextmanager
async def get_db(db_path: str | Path) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Asynchronous context manager for SQLite connections."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(path) as db:
        await _apply_pragmas_async(db)
        yield db
        await db.commit()

async def _apply_pragmas_async(db: aiosqlite.Connection):
    """Performance and concurrency optimizations (async)."""
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA cache_size=-32000")
    await db.execute("PRAGMA temp_store=MEMORY")
    await db.execute("PRAGMA busy_timeout=10000")

import sqlite3
from contextlib import contextmanager
from typing import Generator

@contextmanager
def get_db_sync(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """Synchronous context manager for SQLite connections."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(path, timeout=10)
    _apply_pragmas_sync(conn)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def _apply_pragmas_sync(conn: sqlite3.Connection):
    """Performance and concurrency optimizations (sync)."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.execute("PRAGMA busy_timeout=10000")

