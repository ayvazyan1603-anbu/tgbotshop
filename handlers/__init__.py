from aiogram import Router

from handlers.start import router as start_router
from handlers.stars import router as stars_router
from handlers.premium import router as premium_router
from handlers.gifts import router as gifts_router
from handlers.vpn import router as vpn_router
from handlers.profile import router as profile_router
from handlers.referral import router as referral_router
from handlers.support_admin import router as support_admin_router
from handlers.admin import router as admin_router
from handlers.stars_invoice import router as stars_invoice_router
# и в setup_routers():



def setup_routers() -> Router:
    main_router = Router()
    main_router.include_router(admin_router)        # первым — чтобы /testbalance не перехватывался
    main_router.include_router(start_router)
    main_router.include_router(stars_router)
    main_router.include_router(premium_router)
    main_router.include_router(gifts_router)
    main_router.include_router(vpn_router)
    main_router.include_router(profile_router)
    main_router.include_router(stars_invoice_router)
    main_router.include_router(referral_router)
    main_router.include_router(support_admin_router)
    return main_router


__all__ = ["setup_routers"]
