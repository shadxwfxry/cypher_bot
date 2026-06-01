from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from bot.config import settings
from bot.database.models import Base

# Determine database connection URL.
# In DEBUG mode, local SQLite is used for lightweight testing without external dependencies.
db_url = settings.database_url
if settings.debug:
    db_url = "sqlite+aiosqlite:///cypher_local.db"

# Create async SQLAlchemy connection engine
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
        pool_pre_ping=True  # Verify connection health before usage to prevent socket drops
    )

# Establish async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initializes tables and optimizes DB configurations on application startup."""
    async with engine.begin() as conn:
        # Create all tables dynamically based on metadata mappings
        await conn.run_sync(Base.metadata.create_all)
        
        # SQLite-specific optimization flags to eliminate locking bottlenecks under concurrent disk writes
        if "sqlite" in db_url:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))      # Activate Write-Ahead Logging
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))    # Balance write speed and reliability


