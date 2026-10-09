from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database.models import Base, User
from core.config import settings

DB_URL = "sqlite+aiosqlite:///bot.db"

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(user_id: int, username: str | None, first_name: str | None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        today = datetime.utcnow().date()

        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                daily_requests=0,
                total_requests=0,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Якщо дата останньої активності була не сьогодні — скидаємо денний лічильник
            if user.last_active and user.last_active.date() != today:
                user.daily_requests = 0

            user.username = username
            user.first_name = first_name
            user.last_active = datetime.utcnow()
            await session.commit()
            await session.refresh(user)
            
        return user


async def check_user_limit(user_id: int) -> tuple[bool, int]:
    """
    Повертає (can_download: bool, remaining_requests: int)
    """
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return True, settings.daily_free_limit

        # Преміум юзери мають безліміт
        if user.is_premium:
            return True, 999999

        today = datetime.utcnow().date()
        # Якщо новий день — лічильник уже обнулений
        if user.last_active and user.last_active.date() != today:
            user.daily_requests = 0
            await session.commit()

        if user.daily_requests >= settings.daily_free_limit:
            return False, 0

        remaining = settings.daily_free_limit - user.daily_requests
        return True, remaining


async def increment_requests(user_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            today = datetime.utcnow().date()
            if user.last_active and user.last_active.date() != today:
                user.daily_requests = 1
            else:
                user.daily_requests += 1

            user.total_requests += 1
            user.last_active = datetime.utcnow()
            await session.commit()


async def get_stats() -> dict:
    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        total_downloads = await session.scalar(select(func.sum(User.total_requests))) or 0
        premium_users = await session.scalar(select(func.count(User.id)).where(User.is_premium == True))

        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "premium_users": premium_users,
        }