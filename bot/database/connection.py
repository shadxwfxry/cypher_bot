from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from bot.config import settings
from bot.database.models import Base

db_url = settings.database_url
if settings.debug:
    db_url = "sqlite+aiosqlite:///cypher_local.db"

if "sqlite" in db_url:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True
    )
else:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True
    )

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
        
        # Enable WAL (Write-Ahead Logging) and normal sync settings for SQLite to prevent lock issues
        if "sqlite" in db_url:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))

