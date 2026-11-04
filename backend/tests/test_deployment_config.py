import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.engine.url import make_url
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


def test_neon_exact_url_with_channel_binding():
    """
    Verify exact Neon URL with sslmode=require&channel_binding=require.
    Ensures channel_binding is stripped and ssl=require is preserved so
    asyncpg doesn't fail with TypeError: unexpected keyword argument 'channel_binding'.
    """
    neon_url = "postgresql://alex:AbC123dEf@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    formatted = format_database_url(neon_url)

    # 1. Driver verification
    assert formatted.startswith("postgresql+asyncpg://")

    # 2. SSL security preserved
    assert "ssl=require" in formatted

    # 3. Unsupported parameters stripped
    assert "channel_binding" not in formatted
    assert "sslmode" not in formatted

    # 4. Dialect connect args verification
    dialect = PGDialect_asyncpg()
    cargs, cparams = dialect.create_connect_args(make_url(formatted))
    assert cparams.get("ssl") == "require"
    assert "channel_binding" not in cparams
    assert "sslmode" not in cparams

    # 5. Engine creation without live network
    url, kwargs = get_engine_args(neon_url)
    engine = create_async_engine(url, **kwargs)
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "asyncpg"


def test_neon_pooled_connection_statement_cache():
    """
    Verify Neon PgBouncer pooled connection (-pooler in hostname) sets
    statement_cache_size=0 to prevent transaction pooling prepared statement conflicts.
    """
    neon_pool_url = "postgresql://alex:AbC123dEf@ep-cool-fog-123456-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    url, kwargs = get_engine_args(neon_pool_url)

    assert "statement_cache_size" in kwargs.get("connect_args", {})
    assert kwargs["connect_args"]["statement_cache_size"] == 0
    assert kwargs.get("pool_pre_ping") is True

    # Engine can be compiled
    engine = create_async_engine(url, **kwargs)
    assert engine.dialect.name == "postgresql"


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
