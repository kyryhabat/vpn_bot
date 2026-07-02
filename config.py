import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

XUI_URL = os.getenv("XUI_URL")
XUI_USER = os.getenv("XUI_USER")
XUI_PASS = os.getenv("XUI_PASS")
INBOUND_ID = int(os.getenv("INBOUND_ID", 2))
INBOUND_ID_FREE = int(os.getenv("INBOUND_ID_FREE", 4))  # отдельный инбаунд для бесплатных

REALITY_PUBLIC_KEY = os.getenv("REALITY_PUBLIC_KEY", "Ed0YJJ2JDmZxAXcTJ90lH6l2dvhu3pX38aq1RLYpKA4")
DOMAIN = os.getenv("DOMAIN")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]


YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://t.me/FlashVPN_AppBot")


TARIFFS = {
    "free": {
        "name": "Бесплатный 3 дня", 
        "days": 3, 
        "traffic_gb": 15, 
        "price": 0,
        "description": "Тестовый период",
        "is_active": True
    },
    "free_3days": {
        "name": "Бесплатный 3 дня", 
        "days": 3, 
        "traffic_gb": 15, 
        "price": 0,
        "description": "Тестовый период",
        "is_active": True
    },
    "14": {
        "name": "14 дней",
        "days": 14, 
        "traffic_gb": 150, 
        "price": 100,
        "is_active": True
    },
    "30": {
        "name": "30 дней (месяц)",
        "days": 30, 
        "traffic_gb": 0, 
        "price": 200,
        "is_active": True
    },
    "90": {
        "name": "90 дней",
        "days": 90, 
        "traffic_gb": 0, 
        "price": 500,
        "is_active": True
    },
}


REFERRAL_SETTINGS = {
    "bonus_for_referrer": 35,
}


PROMOCODE_SETTINGS = {
    "balance_min": 10,          # Минимальная сумма для промокода на баланс
    "balance_max": 10000,       # Максимальная сумма для промокода на баланс
    "discount_min": 1,          # Минимальный процент скидки
    "discount_max": 100,        # Максимальный процент скидки
    "max_uses_min": 1,          # Минимальное количество использований
    "max_uses_max": 1000,       # Максимальное количество использований
    "expiry_days_min": 1,       # Минимальный срок действия (дни)
    "expiry_days_max": 365,     # Максимальный срок действия (дни)
    "default_expiry_days": 30,  # Срок действия по умолчанию (дни)
}