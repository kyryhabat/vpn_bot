# handlers/__init__.py
from .start_menu import router as start_router
from .buy_vpn import router as buy_vpn_router
from .payment_handlers import router as payment_router
from .admin import router as admin_router
from .support import router as support_router
from .errors import router as errors_router

# ДОБАВЬТЕ ЭТУ СТРОКУ ↓↓↓
from .promo import router as promo_router

# ДОБАВЬТЕ promo_router в список ↓↓↓
routers = [
    start_router,
    promo_router,  # <-- ДОБАВЬТЕ ЗДЕСЬ
    buy_vpn_router,
    payment_router,
    admin_router,
    support_router,
    errors_router,  # errors_router должен быть ПОСЛЕДНИМ
]