import urllib.parse
from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

# Unsupported libpq parameters that asyncpg does not accept in query strings
UNSUPPORTED_ASYNC_PARAMS = {
    "channel_binding",
    "gssencmode",
}


def format_database_url(raw_url: str) -> str:
    """
    Format and normalize the database URL for SQLAlchemy async engines.
    Converts:
      - sqlite:/// -> sqlite+aiosqlite:///
      - postgres:// -> postgresql+asyncpg://
      - postgresql:// -> postgresql+asyncpg://
      - postgresql+psycopg2:// -> postgresql+asyncpg://
    Translates query parameters:
      - Maps sslmode=require to ssl=require for asyncpg compatibility while preserving SSL.
      - Removes unsupported libpq parameters such as channel_binding.
    """
    if not raw_url:
        return raw_url

    url_str = raw_url.strip()

    # SQLite
    if url_str.startswith("sqlite://") and not url_str.startswith("sqlite+aiosqlite://"):
        return "sqlite+aiosqlite://" + url_str[len("sqlite://"):]
    if url_str.startswith("sqlite"):
        return url_str

    # PostgreSQL / Neon / Render
    if url_str.startswith("postgres://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgres://"):]
    elif url_str.startswith("postgresql://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgresql://"):]
    elif url_str.startswith("postgresql+psycopg2://"):
        url_str = "postgresql+asyncpg://" + url_str[len("postgresql+psycopg2://"):]

    # Parse query parameters to ensure compatibility with asyncpg
    parsed = urllib.parse.urlsplit(url_str)
    query_params = urllib.parse.parse_qs(parsed.query)

    # asyncpg expects 'ssl' parameter instead of 'sslmode'
    if "sslmode" in query_params:
        mode = query_params.pop("sslmode")[0]
        if mode in ("require", "prefer", "allow"):
            query_params["ssl"] = ["require"]
        elif mode in ("verify-ca", "verify-full"):
            query_params["ssl"] = ["verify-full"]
        elif mode == "disable":
            query_params["ssl"] = ["disable"]
        else:
            query_params["ssl"] = [mode]

    # Remove unsupported libpq parameters (e.g. channel_binding, gssencmode)
    for param in UNSUPPORTED_ASYNC_PARAMS:
        query_params.pop(param, None)

    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, parsed.fragment))


def get_engine_args(url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Determine appropriate create_async_engine arguments based on dialect.
    - SQLite: Uses connect_args={"check_same_thread": False} and default pooling.
    - PostgreSQL (Direct or Pooled):
      - Configures connection pooling (pool_pre_ping=True, pool_recycle=300).
      - For Neon PgBouncer pooled connections (containing 'pooler' in host),
        disables statement_cache_size to prevent transaction pooling collisions.
    """
    normalized_url = format_database_url(url)
    is_sqlite = normalized_url.startswith("sqlite")

    engine_kwargs: Dict[str, Any] = {
        "echo": False,
    }

    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Production PostgreSQL (Neon / Render)
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 300
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

        # Handle Neon connection pooler (PgBouncer)
        parsed = urllib.parse.urlsplit(normalized_url)
        connect_args: Dict[str, Any] = {}

        if "pooler" in parsed.netloc:
            # Disable asyncpg prepared statement caching for PgBouncer transaction mode
            connect_args["statement_cache_size"] = 0

        if connect_args:
            engine_kwargs["connect_args"] = connect_args

    return normalized_url, engine_kwargs


settings = get_settings()
_db_url, _engine_kwargs = get_engine_args(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
