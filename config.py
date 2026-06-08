from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Bot
    bot_token: str
    admin_id: int
    support_username: str

    # Database
    database_url: str

    # Referral
    referral_percent: int

    # VPN Panel (Marzban)
    marzban_url: str
    marzban_username: str
    marzban_password: str

    # Fragment / iStar API
    fragment_api_key: str
    fragment_webhook_secret: str
    webhook_port: int

    # Lava.ru (СБП + карты)
    lava_api_key: str          # API ключ из личного кабинета lava.ru
    lava_secret_key: str       # Secret key для проверки подписи вебхука
    lava_shop_id: str          # ID магазина в lava.ru
    lava_verify_code: str      # lava-verify=xxx из верификации домена

    # CryptoBot (TON + крипта)
    cryptobot_token: str       # Токен от @CryptoBot → /pay

    # FreeKassa (карты, СБП, кошельки)
    freekassa_shop_id: str     # ID магазина (MERCHANT_ID)
    freekassa_secret1: str     # Секретное слово 1 (для формы оплаты)
    freekassa_secret2: str     # Секретное слово 2 (для проверки вебхука)
    freekassa_api_key: str     # API-ключ (для запросов к API)

    # Фото для разделов меню (file_id после загрузки через upload_photos.py)
    photo_id_main:     str
    photo_id_stars:    str
    photo_id_premium:  str
    photo_id_gifts:    str
    photo_id_profile:  str
    photo_id_referral: str
    photo_id_support:  str

    # Prices (RUB)
    stars_50_price: int
    stars_100_price: int
    stars_150_price: int
    stars_250_price: int
    stars_350_price: int
    stars_500_price: int
    stars_750_price: int
    stars_1000_price: int
    stars_1500_price: int
    stars_2500_price: int
    stars_5000_price: int
    stars_10000_price: int

    premium_3m_price: int
    premium_6m_price: int
    premium_12m_price: int

    vpn_1m_price: int
    vpn_3m_price: int
    vpn_6m_price: int


def load_config() -> Config:
    return Config(
        bot_token=getenv("BOT_TOKEN", ""),
        admin_id=int(getenv("ADMIN_ID", "0")),
        support_username=getenv("SUPPORT_USERNAME", "support"),
        database_url=getenv("DATABASE_URL", "sqlite+aiosqlite:///./shop.db"),
        referral_percent=int(getenv("REFERRAL_PERCENT", "10")),
        marzban_url=getenv("MARZBAN_URL", ""),
        marzban_username=getenv("MARZBAN_USERNAME", "admin"),
        marzban_password=getenv("MARZBAN_PASSWORD", ""),
        fragment_api_key=getenv("FRAGMENT_API_KEY", ""),
        fragment_webhook_secret=getenv("FRAGMENT_WEBHOOK_SECRET", ""),
        webhook_port=int(getenv("WEBHOOK_PORT", "8080")),
        lava_api_key=getenv("LAVA_API_KEY", ""),
        lava_secret_key=getenv("LAVA_SECRET_KEY", ""),
        lava_shop_id=getenv("LAVA_SHOP_ID", ""),
        lava_verify_code=getenv("LAVA_VERIFY_CODE", ""),
        cryptobot_token=getenv("CRYPTOBOT_TOKEN", ""),
        freekassa_shop_id=getenv("FREEKASSA_SHOP_ID", ""),
        freekassa_secret1=getenv("FREEKASSA_SECRET1", ""),
        freekassa_secret2=getenv("FREEKASSA_SECRET2", ""),
        freekassa_api_key=getenv("FREEKASSA_API_KEY", ""),
        photo_id_main=getenv("PHOTO_ID_MAIN", ""),
        photo_id_stars=getenv("PHOTO_ID_STARS", ""),
        photo_id_premium=getenv("PHOTO_ID_PREMIUM", ""),
        photo_id_gifts=getenv("PHOTO_ID_GIFTS", ""),
        photo_id_profile=getenv("PHOTO_ID_PROFILE", ""),
        photo_id_referral=getenv("PHOTO_ID_REFERRAL", ""),
        photo_id_support=getenv("PHOTO_ID_SUPPORT", ""),
        stars_50_price=int(getenv("STARS_50_PRICE", "80")),
        stars_100_price=int(getenv("STARS_100_PRICE", "160")),
        stars_150_price=int(getenv("STARS_150_PRICE", "220")),
        stars_250_price=int(getenv("STARS_250_PRICE", "360")),
        stars_350_price=int(getenv("STARS_350_PRICE", "499")),
        stars_500_price=int(getenv("STARS_500_PRICE", "710")),
        stars_750_price=int(getenv("STARS_750_PRICE", "1100")),
        stars_1000_price=int(getenv("STARS_1000_PRICE", "1600")),
        stars_1500_price=int(getenv("STARS_1500_PRICE", "2200")),
        stars_2500_price=int(getenv("STARS_2500_PRICE", "3600")),
        stars_5000_price=int(getenv("STARS_5000_PRICE", "7100")),
        stars_10000_price=int(getenv("STARS_10000_PRICE", "16000")),
        premium_3m_price=int(getenv("PREMIUM_3M_PRICE", "350")),
        premium_6m_price=int(getenv("PREMIUM_6M_PRICE", "620")),
        premium_12m_price=int(getenv("PREMIUM_12M_PRICE", "1100")),
        vpn_1m_price=int(getenv("VPN_1M_PRICE", "150")),
        vpn_3m_price=int(getenv("VPN_3M_PRICE", "400")),
        vpn_6m_price=int(getenv("VPN_6M_PRICE", "700")),
    )


config: Config = load_config()