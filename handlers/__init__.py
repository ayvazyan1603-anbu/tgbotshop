from aiogram import Router

from handlers.start import router as start_router
from handlers.stars import router as stars_router
from handlers.premium import router as premium_router
from handlers.gifts import router as gifts_router
from handlers.vpn import router as vpn_router
from handlers.profile import router as profile_router
from handlers.referral import router as referral_router
from handlers.support_admin import router as support_admin_router


def setup_routers() -> Router:
    """Создаёт главный роутер и подключает все дочерние."""
    main_router = Router()
    main_router.include_router(start_router)
    main_router.include_router(stars_router)
    main_router.include_router(premium_router)
    main_router.include_router(gifts_router)
    main_router.include_router(vpn_router)
    main_router.include_router(profile_router)
    main_router.include_router(referral_router)
    main_router.include_router(support_admin_router)
    return main_router


__all__ = ["setup_routers"]
