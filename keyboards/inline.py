
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TARIFFS

_db_instance = None

def get_db():
    global _db_instance
    if _db_instance is None:
        from supabase_client import db
        _db_instance = db
    return _db_instance



def main_menu(user_id=None, admin=False):

    used_free_vpn = False
    if user_id:
        try:
            db = get_db()
            orders = db.get_user_orders(user_id)
            free_orders = [o for o in orders if o.get('price', 0) == 0]
            used_free_vpn = len(free_orders) > 0
        except:
            used_free_vpn = False
    
    buttons = []
    

    if not used_free_vpn:
        buttons.append([
            InlineKeyboardButton(
                text="🎁 Получить 3 дня бесплатно",
                callback_data="get_free_vpn"
            )
        ])
    
    # Основные кнопки
    buttons.extend([
        [
            InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn"),
            InlineKeyboardButton(text="💳 Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="🎫 Промокод", callback_data="use_promo"),
            InlineKeyboardButton(text="🤝 Партнерка", callback_data="referral")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="📞 Поддержка", url="https://t.me/mr_flive")
        ],
        [
            InlineKeyboardButton(text="📢 Канал", url="https://t.me/FlashvpnNews"),
            InlineKeyboardButton(text="🔒 Политика", url="https://telegra.ph/Pravila-soglasheniya-i-politika-01-05")
        ]
    ])
    
    if admin:
        buttons.append([
            InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_menu")
        ])
    

    buttons = [row for row in buttons if row]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users_0")],
        [InlineKeyboardButton(text="📦 Все заказы", callback_data="admin_orders_0")],
        [InlineKeyboardButton(text="🎫 Управление промокодами", callback_data="admin_promo_menu")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="💰 Выдать баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_manage_admins")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])



def admin_users_list_menu(users_data, page=0, total_users=0, per_page=10):

    buttons = []
    

    total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
    

    for user in users_data:
        user_id = user.get('user_id', 'N/A')
        username = user.get('username', 'без имени') or 'без имени'
        balance = user.get('balance', 0)
        admin_status = "👑" if user.get('is_admin') else "👤"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{admin_status} @{username} | {balance}₽",
                callback_data=f"admin_user_{user_id}"
            )
        ])
    

    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_users_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data=f"admin_users_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    

    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_users_{page}"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_user_detail_menu(user_id, user_info):
    """Детальное меню пользователя"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Изменить баланс", callback_data=f"admin_user_balance_{user_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ К списку пользователей", callback_data="admin_users_0"),
            InlineKeyboardButton(text="🏠 Админ-панель", callback_data="admin_menu")
        ]
    ])



def admin_orders_list_menu(orders_data, page=0, total_orders=0, per_page=10):

    buttons = []

    total_pages = (total_orders + per_page - 1) // per_page if total_orders > 0 else 1

    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_orders_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data=f"admin_orders_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_orders_{page}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def admin_promo_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promos_0")],
        [InlineKeyboardButton(text="📊 Статистика промокодов", callback_data="admin_promo_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

def admin_promocodes_list_menu(promos_data, page=0, total_promos=0, per_page=10):

    buttons = []
    

    for promo in promos_data:
        promo_code = promo.get('code', 'N/A')
        value = promo.get('value', 0)
        used = promo.get('used_count', 0)
        max_uses = promo.get('max_uses', 0)
        
        status = "🟢" if promo.get('is_active', True) else "🔴"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"💰 {promo_code} | {value}₽ | {used}/{max_uses} {status}",
                callback_data=f"admin_promo_detail_{promo_code}"
            )
        ])
    

    total_pages = (total_promos + per_page - 1) // per_page if total_promos > 0 else 1
    nav_buttons = []
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_list_promos_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="no_action"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️ Вперед", callback_data=f"admin_list_promos_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin_list_promos_{page}"),
        InlineKeyboardButton(text="➕ Новый", callback_data="admin_create_promo")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_promo_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_promo_detail_menu(promo_code: str, promo_info: dict):

    buttons = []
    

    if promo_info.get('is_active', True):
        buttons.append([
            InlineKeyboardButton(text="❌ Деактивировать", callback_data=f"admin_promo_deactivate_{promo_code}")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="📋 К списку", callback_data="admin_list_promos_0"),
        InlineKeyboardButton(text="🏠 В админку", callback_data="admin_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_deactivate_promo_menu(promo_code: str):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"❌ Да, деактивировать", callback_data=f"admin_confirm_deactivate_{promo_code}")
        ],
        [
            InlineKeyboardButton(text="✅ Нет, отмена", callback_data=f"admin_promo_detail_{promo_code}")
        ]
    ])



def admin_broadcast_confirmation_menu(message_text: str, estimated_users: int):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Да, отправить ({estimated_users} пользователей)", callback_data="admin_broadcast_confirm")
        ],
        [
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data="admin_broadcast_edit")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")
        ]
    ])

def admin_broadcast_progress_menu(progress: int, total: int):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"📤 Отправлено: {progress}/{total}", callback_data="no_action")
        ],
    ])

def admin_broadcast_completed_menu(success: int, failed: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Успешно: {success} | ❌ Ошибок: {failed}", callback_data="no_action")
        ],
        [
            InlineKeyboardButton(text="🏠 В админку", callback_data="admin_menu")
        ]
    ])



def cancel_admin_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]
    ])



def admin_manage_admins_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin")],
        [InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_remove_admin")],
        [InlineKeyboardButton(text="👥 Список админов", callback_data="admin_list_admins")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])

def confirm_add_admin_menu(user_id, username):

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Да, добавить @{username}", callback_data=f"admin_confirm_add_{user_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data="admin_manage_admins")]
    ])

def confirm_remove_admin_menu(user_id, username):

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"❌ Да, удалить @{username}", callback_data=f"admin_confirm_remove_{user_id}")],
        [InlineKeyboardButton(text="✅ Нет, отмена", callback_data="admin_list_admins")]
    ])



def tariff_menu(user_id=None):

    used_free_vpn = False
    if user_id:
        try:
            db = get_db()
            orders = db.get_user_orders(user_id)
            free_orders = [o for o in orders if o.get('price', 0) == 0]
            used_free_vpn = len(free_orders) > 0
        except:
            used_free_vpn = False
    
    buttons = []
    

    free_tariff = TARIFFS.get("free")
    if free_tariff and not used_free_vpn:
        buttons.append([
            InlineKeyboardButton(
                text=f"🎁 {free_tariff['days']} дня | {free_tariff['traffic_gb']}GB | БЕСПЛАТНО",
                callback_data="select_free_tariff"
            )
        ])
    
    # Платные тарифы
    paid_tariffs = ["14", "30", "90"]
    for tariff_id in paid_tariffs:
        tariff = TARIFFS.get(tariff_id)
        if tariff and tariff.get('is_active', True):
            days = tariff['days']
            traffic = tariff['traffic_gb']
            price = tariff['price']
            name = tariff.get('name', f'{days} дней')
            
            # Эмодзи для разных тарифов
            if tariff_id == "14":
                emoji = "🟢"
            elif tariff_id == "30":
                emoji = "🔵"
            else:  # 90
                emoji = "🟣"
            
            # Текст трафика
            if traffic == 0:
                traffic_text = "♾️"
            else:
                traffic_text = f"{traffic}GB"
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {name} | {traffic_text} | {price}₽",
                    callback_data=f"select_tariff_{tariff_id}"
                )
            ])
    

    buttons.append([
        InlineKeyboardButton(text="💳 Баланс", callback_data="balance"),
        InlineKeyboardButton(text="🏠 На главную", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_purchase_menu(tariff_id, price, tariff_info=None):

    buttons = []
    
    if tariff_info:
        days = tariff_info.get('days', 0)
        traffic = tariff_info.get('traffic_gb', 0)
        
        if traffic == 0:
            traffic_text = "♾️ Безлимит"
        else:
            traffic_text = f"{traffic}GB"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"📅 {days} дней | 📊 {traffic_text}",
                callback_data="no_action"
            )
        ])
    

    callback_data = f"buy_tariff_{tariff_id}"
    
    buttons.append([
        InlineKeyboardButton(
            text=f"✅ Купить за {price:.0f}₽",
            callback_data=callback_data
        )
    ])
    

    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="buy_vpn"),
        InlineKeyboardButton(text="💳 Баланс", callback_data="balance")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def my_vpn_menu(vpn_list=None, page=0, total_vpns=0, per_page=5, has_vpns=True):
    buttons = []
    
    if has_vpns and vpn_list:
        for vpn in vpn_list:
            vpn_id = vpn.get('id', 0)
            days_left = vpn.get('remaining_days', 0)
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"🔑 VPN #{vpn_id} | {days_left} дней",
                    callback_data=f"vpn_detail_{vpn_id}"
                )
            ])
    
    # Пагинация
    if has_vpns and total_vpns > per_page:
        total_pages = (total_vpns + per_page - 1) // per_page
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"my_vpn_{page-1}")
            )
        
        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="no_action")
        )
        
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️ Вперед", callback_data=f"my_vpn_{page+1}")
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)
    

    action_buttons = []
    if has_vpns:
        action_buttons.append(
            InlineKeyboardButton(text="🔄 Обновить", callback_data=f"my_vpn_{page}")
        )
    
    action_buttons.append(
        InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")
    )
    
    if action_buttons:
        buttons.append(action_buttons)
    

    buttons.append([
        InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_menu(user_id=None, is_admin=False):

    buttons = [
        [
            InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="🎫 Мои промокоды", callback_data="promo_history_0")
        ],
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
        ]
    ]
    
    if is_admin:
        buttons.append([
            InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_menu")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=[row for row in buttons if row])



def balance_menu(balance=0):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💳 Пополнить баланс", callback_data="deposit")
        ],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])



def cancel_menu(target="main_menu"):
    """Кнопка отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=target)]
    ])

def back_to_main():
    """Кнопка назад в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])

def back_to_vpns():
    """Кнопка возврата к списку VPN"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔙 К списку VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ])


def get_renew_vpn_keyboard(vpn_id: int = 0):
    """Клавиатура для уведомлений о продлении VPN"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить новый VPN", callback_data="buy_vpn"),
            InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="💳 Баланс", callback_data="balance"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def cancel_deposit_menu():
    """Кнопка отмены пополнения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="deposit")]
    ])

def back_to_profile():
    """Кнопка возврата в профиль"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
    ])

def refresh_menu(target):
    """Кнопка обновления"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=target)]
    ])





def vpn_detail_menu(vpn_id: int, vpn_info=None):

    buttons = []
    
    buttons.append([
        InlineKeyboardButton(text="🔗 Показать ключ", callback_data=f"show_key_{vpn_id}")
    ])
    
    
    buttons.append([
        InlineKeyboardButton(text="🔙 К списку VPN", callback_data="my_vpn_0")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def confirm_free_vpn_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Получить бесплатный VPN",
                callback_data="confirm_free_purchase"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="buy_vpn"
            )
        ]
    ])

def after_purchase_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="🛒 Купить ещё", callback_data="buy_vpn")
        ],
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
        ]
    ])

def payment_methods():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Банковская карта", callback_data="payment_yookassa"),
            InlineKeyboardButton(text="🤖 CryptoBot (USDT)", callback_data="payment_crypto_bot")
        ],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def yookassa_payment_menu(payment_url, amount, payment_id=None):
    """Меню оплаты ЮKassa"""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"💳 Оплатить {amount}₽",
                url=payment_url
            )
        ]
    ]
    
    if payment_id:
        buttons.append([
            InlineKeyboardButton(
                text="🔄 Проверить оплату",
                callback_data=f"check_payment_{payment_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="deposit"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def crypto_payment_menu(pay_url, amount, invoice_id):
    """Меню оплаты CryptoBot"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🤖 Оплатить {amount}₽",
                url=pay_url
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Проверить статус",
                callback_data=f"check_crypto_{invoice_id}"
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="deposit"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def help_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📖 FAQ и вопросы", callback_data="faq")
        ],
        [
            InlineKeyboardButton(text="📚 Инструкция по установке", url="http://f1173334.xsph.ru/")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]
    ])

def support_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Чат поддержки", url="https://t.me/mr_flive")
        ],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def referral_menu(ref_stats=None, ref_link=None):

    buttons = []
    
    if ref_link:
        buttons.append([
            InlineKeyboardButton(text="🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def promo_history_menu(history_list=None, page=0, total_pages=1):

    buttons = []
    
    # Пагинация
    if total_pages > 1:
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"promo_history_{page-1}")
            )
        
        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {page+1}/{total_pages}", callback_data="no_action")
        )
        
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️ Вперед", callback_data=f"promo_history_{page+1}")
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)
    
    buttons.append([
        InlineKeyboardButton(text="🎫 Новый промокод", callback_data="use_promo"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="promo_history_0")
    ])
    
    buttons.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def after_free_vpn_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")
        ],
        
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ])

def after_payment_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn"),
            InlineKeyboardButton(text="💳 Пополнить ещё", callback_data="deposit")
        ],
        
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")
        ]
    ])

def check_payment_again_menu(payment_id: str):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Проверить ещё раз", callback_data=f"check_payment_{payment_id}"),
            InlineKeyboardButton(text="💳 Новый платёж", callback_data="deposit")
        ],
        [
            InlineKeyboardButton(text="📞 Поддержка", callback_data="support"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def crypto_check_again_menu(invoice_id: str):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Проверить статус", callback_data=f"check_crypto_{invoice_id}"),
            InlineKeyboardButton(text="🤖 Новый счёт", callback_data="deposit")
        ],
        [
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def contact_support_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Написать в чат", url="https://t.me/mr_flive")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]
    ])

def get_renew_vpn_keyboard(vpn_id: int = 0):

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить новый VPN", callback_data="buy_vpn"),
            InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")
        ],
        [
            InlineKeyboardButton(text="💳 Баланс", callback_data="balance"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

def cancel_deposit_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="deposit")]
    ])

def back_to_profile():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 В профиль", callback_data="profile")]
    ])

def refresh_menu(target):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data=target)]
    ])

def after_free_vpn_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить VPN", callback_data="buy_vpn")
        ],
        [
            InlineKeyboardButton(text="👤 В профиль", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ])




def cancel_admin_operation_menu():

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]
    ])