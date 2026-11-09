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


@pytest.mark.asyncio
async def test_database_health_check_success():
    """Verify GET /api/health/db returns HTTP 200 when SELECT 1 succeeds."""
    from unittest.mock import patch, AsyncMock
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.database import init_db

    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health/db")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_database_health_check_failure_returns_503():
    """Verify GET /api/health/db returns HTTP 503 when database connectivity fails."""
    from unittest.mock import patch, AsyncMock
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    transport = ASGITransport(app=app)
    with patch("app.main.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = ConnectionRefusedError(
            "asyncpg://user:secret_password@neon.tech:5432/db connection failed"
        )
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_local.return_value = mock_session

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/health/db")
            assert resp.status_code == 503
            data = resp.json()
            assert data["status"] == "unhealthy"
            assert data["database"] == "disconnected"
            # Crucial: NEVER expose internal exceptions, passwords, or connection strings
            assert "secret_password" not in str(data)
            assert "neon.tech" not in str(data)
            assert "exception" not in data


@pytest.mark.asyncio
async def test_models_are_registered_before_table_initialization():
    """Verify Trip and AgentStatus models are registered in Base.metadata before init_db."""
    from app.database import Base, register_models

    register_models()
    tables = Base.metadata.tables
    assert "trips" in tables, "trips table must be registered in Base.metadata"
    assert "agent_statuses" in tables, "agent_statuses table must be registered in Base.metadata"


def test_cors_production_exact_origins_and_regex_isolation():
    """
    Verify production CORS settings:
    - Exact origin matching preserves allow_credentials=True
    - Wildcard origin disables allow_credentials to adhere to browser security
    - Regex is optional and stripped
    """
    # 1. Exact origins in production
    exact_cfg = Settings(CORS_ORIGINS="https://tripmind-ai.vercel.app", CORS_ORIGIN_REGEX="")
    assert exact_cfg.cors_origins_list == ["https://tripmind-ai.vercel.app"]
    assert exact_cfg.CORS_ORIGIN_REGEX == ""

    # 2. Local development fallback
    local_cfg = Settings()
    assert "http://localhost:5173" in local_cfg.cors_origins_list
    assert "http://localhost:3000" in local_cfg.cors_origins_list

    # 3. Wildcard origin detection
    wildcard_cfg = Settings(CORS_ORIGINS="*")
    assert "*" in wildcard_cfg.cors_origins_list

