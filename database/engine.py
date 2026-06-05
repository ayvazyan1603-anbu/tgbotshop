from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base
from config import config

engine = create_async_engine(config.database_url, echo=False, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def seed_gifts() -> None:
    """Синхронизирует каталог удалённых подарков при запуске."""
    from database.models import Gift
    from sqlalchemy import delete

    # name, gift_type, stars_cost, price_rub
    GIFTS = [
        ("🧸 Новогодний мишка",        "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка влюбленных",        "regular", 50, float(config.stars_50_price)),
        ("🎄 Елка",                    "regular", 50, float(config.stars_50_price)),
        ("💝 Сердце влюбленных",       "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка на 8 марта",        "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка на День Патрика",   "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка на 1 апреля",       "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка на Пасху",          "regular", 50, float(config.stars_50_price)),
        ("🧸 Мишка на 1 мая",          "regular", 50, float(config.stars_50_price)),
    ]

    async with async_session_factory() as session:
        await session.execute(delete(Gift).where(Gift.gift_type == "regular"))
        for name, gtype, stars, price in GIFTS:
            session.add(Gift(
                name=name,
                price=price,
                gift_type=gtype,
                is_available=True,
                stock=-1,
                description=f"{stars} ⭐ Stars",
            ))
        await session.commit()