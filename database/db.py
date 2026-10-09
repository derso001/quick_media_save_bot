from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database.models import Base, User

DB_URL = "sqlite+aiosqlite:///bot.db"

engine = create_async_engine(DB_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    """Створення таблиць при запуску бота."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(user_id: int, username: str | None, first_name: str | None) -> User:
    """Отримати або зареєструвати користувача в БД."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Оновлюємо ім'я/юзернейм, якщо користувач змінив їх у TG
            user.username = username
            user.first_name = first_name
            user.last_active = datetime.utcnow()
            await session.commit()
        return user


async def increment_requests(user_id: int):
    """Збільшення лічильника завантажень."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.daily_requests += 1
            user.total_requests += 1
            user.last_active = datetime.utcnow()
            await session.commit()


async def get_stats() -> dict:
    """Аналітика для адміністратора."""
    async with async_session() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        total_downloads = await session.scalar(select(func.sum(User.total_requests))) or 0
        premium_users = await session.scalar(select(func.count(User.id)).where(User.is_premium == True))

        return {
            "total_users": total_users,
            "total_downloads": total_downloads,
            "premium_users": premium_users,
        }