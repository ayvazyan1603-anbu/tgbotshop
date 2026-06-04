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
    """Заполняет таблицу подарками при первом запуске."""
    from database.models import Gift
    from sqlalchemy import select

    # name, gift_type, stars_cost, price_rub
    GIFTS = [
        # ── Обычные (regular) ──────────────────────────────
        ("💝 Сердце",      "regular",  15,   25.0),
        ("🧸 Мишка",       "regular",  15,   25.0),
        ("🎁 Подарок",   "regular",  25,   40.0),
        ("🌹 Роза",         "regular",  25,   40.0),
        ("🎂 Торт",      "regular",  50,   80.0),
        ("💐 Букет",      "regular",  50,   80.0),
        ("🚀 Ракета",               "regular",  50,   80.0),
        ("🏆 Кубок",        "regular", 100,  160.0),
        ("💍 Кольцо", "regular", 100,  160.0),
        ("💎 Бриллиант",      "regular", 100,  160.0),
        ("🍾 Шампанское",           "regular",  50,   80.0),
    ]

    async with async_session_factory() as session:
        existing = (await session.execute(select(Gift))).scalars().first()
        if existing:
            return
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