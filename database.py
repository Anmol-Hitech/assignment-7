from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from sqlalchemy.orm import sessionmaker,declarative_base
from config import settings
engine=create_engine(settings.DATABASE_URL)
async_engine=create_async_engine(settings.ASYNC_DATABASE_URL)

AsyncSessionLocal=async_sessionmaker(bind=async_engine,autoflush=False,autocommit=False)
Sessionlocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
Base=declarative_base()

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db