import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import format_database_url, get_engine_args
from app.config import Settings


def test_sqlite_url_formatting():
    """Verify SQLite URLs are normalized with aiosqlite driver."""
    # Standard sqlite
    url1 = "sqlite:///./tripmind.db"
    assert format_database_url(url1) == "sqlite+aiosqlite:///./tripmind.db"

    # Already formatted sqlite+aiosqlite
    url2 = "sqlite+aiosqlite:///./tripmind.db"
    assert format_database_url(url2) == "sqlite+aiosqlite:///./tripmind.db"


def test_postgres_url_formatting_and_ssl():
    """Verify PostgreSQL / Neon URLs normalize to asyncpg and map sslmode to ssl."""
    # Render postgres:// format
    url_render = "postgres://user:secret@dpg-xyz.oregon-postgres.render.com/tripmind"
    assert format_database_url(url_render) == "postgresql+asyncpg://user:secret@dpg-xyz.oregon-postgres.render.com/tripmind"

    # Neon postgresql:// with sslmode=require
    url_neon = "postgresql://user:pass@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    formatted = format_database_url(url_neon)
    assert formatted.startswith("postgresql+asyncpg://")
    assert "ssl=require" in formatted
    assert "sslmode" not in formatted

    # Neon with sslmode=verify-full
    url_neon_full = "postgresql://user:pass@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=verify-full"
    formatted_full = format_database_url(url_neon_full)
    assert "ssl=verify-full" in formatted_full


def test_sqlite_engine_args():
    """Verify SQLite gets check_same_thread=False and no incompatible pool kwargs."""
    url, kwargs = get_engine_args("sqlite+aiosqlite:///./test.db")
    assert kwargs.get("connect_args") == {"check_same_thread": False}
    assert "pool_size" not in kwargs
    assert "max_overflow" not in kwargs

    # Verify engine can be instantiated
    engine = create_async_engine(url, **kwargs)
    assert engine.dialect.name == "sqlite"


def test_postgres_engine_args():
    """Verify PostgreSQL gets connection pool arguments and no check_same_thread."""
    url, kwargs = get_engine_args("postgresql://user:pass@ep-neon.us-east-2.aws.neon.tech/neondb?sslmode=require")
    assert "connect_args" not in kwargs
    assert kwargs.get("pool_pre_ping") is True
    assert kwargs.get("pool_recycle") == 300
    assert kwargs.get("pool_size") == 10
    assert kwargs.get("max_overflow") == 20

    # Verify asyncpg engine can be compiled and configured without live network
    engine = create_async_engine(url, **kwargs)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"


def test_cors_origins_parsing():
    """Verify CORS origins parsing handles whitespace and trailing commas."""
    cfg = Settings(
        CORS_ORIGINS=" https://tripmind.vercel.app , http://localhost:5173 , , "
    )
    assert cfg.cors_origins_list == [
        "https://tripmind.vercel.app",
        "http://localhost:5173",
    ]

    # Empty fallback
    cfg_empty = Settings(CORS_ORIGINS="  ,  ")
    assert "http://localhost:5173" in cfg_empty.cors_origins_list
