# handlers/buy_vpn.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from keyboards import inline
from supabase_client import db
from xui_client import xui  # Импортируем готовый экземпляр
from config import TARIFFS, DOMAIN, BOT_TOKEN, ADMIN_IDS, INBOUND_ID, INBOUND_ID_FREE, REALITY_PUBLIC_KEY
from aiogram.exceptions import TelegramBadRequest
import json
import random
from datetime import datetime, timezone
import logging

# Настройка логгера
logger = logging.getLogger(__name__)

router = Router()
bot = Bot(token=BOT_TOKEN)

def is_admin(user_id: int):
    """Проверка является ли пользователь админом"""
    return user_id in ADMIN_IDS

async def safe_edit_message(callback: types.CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения"""
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        await callback.answer()  # Убираем часики
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Уже обновлено")
        elif "message can't be edited" in str(e):
            try:
                await callback.message.answer(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as send_error:
                logger.error(f"Ошибка отправки сообщения: {send_error}")
        else:
            logger.error(f"Ошибка редактирования сообщения: {e}")
            await callback.answer("❌ Ошибка")

async def create_vpn_connection(user_id: int, tariff_id: str, tariff: dict, promo_code: str = ""):
    """Создать VPN подключение"""
    try:
        logger.info(f"🔄 Создание VPN для user_id={user_id}, tariff={tariff_id}")
        
        # Определяем, бесплатный ли тариф
        is_free = (tariff_id == "free")
        
        logger.info(f"  Тариф: {'бесплатный' if is_free else 'платный'}")
        logger.info(f"  Параметры: days={tariff['days']}, traffic_gb={tariff['traffic_gb']}, is_free={is_free}")
        
        # Создаем пользователя в X-UI
        result = xui.create_user(
            days=tariff['days'],
            traffic_gb=tariff['traffic_gb'],
            is_free=is_free
        )
        
        if not result.get("success"):
            error_msg = result.get("error", "Неизвестная ошибка X-UI")
            logger.error(f"❌ Ошибка X-UI: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        
        logger.info(f"✅ VPN создан в X-UI: {result.get('email', 'N/A')}")
        
        # Используем готовую ссылку из результата
        uuid = result.get("uuid", "")
        link = result.get("link", "")
        
        if not link:
            logger.warning("⚠️ Ссылка не сгенерирована в X-UI, генерируем локально")
            # Генерируем ссылку локально
            port = 31537 if is_free else 25895
            
            if is_free:
                short_ids = ["d679c126", "cc7f29fe46bc017c", "2c96", "17c6272c8256",
                           "ae", "5eeeb914ab", "5177e9", "ebed3a78b7496b"]
            else:
                short_ids = ["11c2af", "1a6d", "6fd6db39fd9878b5", "fc69325c9542", 
                           "f1237936", "6f38d01765", "23f0c408237661", "06"]
            
            short_id = random.choice(short_ids)
            
            link = (
                f"vless://{uuid}@{DOMAIN}:{port}"
                f"?type=tcp&security=reality"
                f"&sni=google.com&pbk={REALITY_PUBLIC_KEY}"
                f"&fp=chrome&sid={short_id}"
                f"&flow=xtls-rprx-vision"
                f"#VPN_{tariff_id}_days"
            )
        
        return {
            "success": True,
            "uuid": uuid,
            "link": link,
            "email": result.get("email", f"user{user_id}"),
            "is_free": is_free
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания VPN: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Исключение: {str(e)}"
        }
# ========== ПРОФИЛЬ И VPN ==========

@router.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    active_vpns = db.get_active_vpns(user_id)
    admin_status = is_admin(user_id)
    
    text = (
        f"👤 Ваш профиль\n\n"
        f"👤 Имя: {user.get('full_name', 'Не указано')}\n"
        f"💰 Баланс: {user.get('balance', 0)} руб\n"
        f"🔑 Активных VPN: {len(active_vpns)} шт\n"
        f"👑 Статус: {'👑 Администратор' if admin_status else '👤 Пользователь'}"
    )
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=inline.profile_menu(user_id=user_id, is_admin=admin_status)
    )

@router.callback_query(F.data.startswith("my_vpn_"))
async def my_vpn_pagination_handler(callback: types.CallbackQuery):
    """Обработчик пагинации для списка VPN"""
    try:
        page_str = callback.data.replace("my_vpn_", "")
        page = int(page_str) if page_str.isdigit() else 0
        
        user_id = callback.from_user.id
        
        # Сначала очищаем истекшие VPN
        db.cleanup_expired_vpns()
        
        # Получаем активные VPN
        active_vpns = db.get_active_vpns(user_id)
        
        if not active_vpns:
            await safe_edit_message(
                callback,
                "📭 У вас нет активных VPN",
                reply_markup=inline.my_vpn_menu(has_vpns=False)
            )
            return
        
        # Пагинация
        per_page = 5
        total_vpns = len(active_vpns)
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total_vpns)
        vpn_page = active_vpns[start_idx:end_idx]
        
        # Простой заголовок
        await safe_edit_message(
            callback,
            "🔑 Ваши VPN подключения\n",
            reply_markup=inline.my_vpn_menu(
                has_vpns=True, 
                vpn_list=vpn_page,
                page=page,
                total_vpns=total_vpns,
                per_page=per_page
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка пагинации VPN: {e}", exc_info=True)
        await callback.answer("❌ Ошибка")
        await safe_edit_message(
            callback,
            "❌ Ошибка загрузки VPN",
            reply_markup=inline.back_to_main()
        )


@router.callback_query(F.data.startswith("vpn_detail_"))
async def vpn_detail_handler(callback: types.CallbackQuery):
    vpn_id = int(callback.data.replace("vpn_detail_", ""))
    
    try:
        user_id = callback.from_user.id
        active_vpns = db.get_active_vpns(user_id)
        
        vpn_info = None
        for vpn in active_vpns:
            if vpn['id'] == vpn_id:
                vpn_info = vpn
                break
        
        if not vpn_info:
            await callback.answer("❌ VPN не найден")
            return
        
        # Получаем корректные данные
        days_total = vpn_info.get('days', 0)
        days_left = vpn_info.get('remaining_days', 0)
        
        # Исправляем баг: если осталось дней больше, чем общий срок
        if days_left > days_total:
            days_left = days_total
        
        status = vpn_info.get('status', 'active')
        
        text = (
            f"🔑 VPN подключение #{vpn_id}\n\n"
            f"📍 Сервер: Амстердам\n"
            f"📅 Срок действия: {days_total} дней\n"
            f"📅 Осталось дней: {days_left}\n"
            f"🟢 Статус: {'Активен' if status == 'active' else 'Неактивен'}"
        )
        
        await safe_edit_message(
            callback,
            text,
            reply_markup=inline.vpn_detail_menu(vpn_id, vpn_info)
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка деталей VPN: {e}", exc_info=True)
        await callback.answer("❌ Ошибка")
        await safe_edit_message(
            callback,
            "❌ Ошибка загрузки данных VPN",
            reply_markup=inline.back_to_main()
        )
@router.callback_query(F.data.startswith("show_key_"))
async def show_key_handler(callback: types.CallbackQuery):
    vpn_id = int(callback.data.replace("show_key_", ""))
    
    try:
        user_id = callback.from_user.id
        
        # Проверяем, не истек ли VPN
        db.cleanup_expired_vpns()
        
        active_vpns = db.get_active_vpns(user_id)
        
        vpn_info = None
        for vpn in active_vpns:
            if vpn['id'] == vpn_id:
                vpn_info = vpn
                break
        
        if not vpn_info:
            await callback.answer("❌ VPN не найден или срок действия истёк")
            
            await safe_edit_message(
                callback,
                "❌ Этот VPN истёк или не найден\n\n"
                "Срок действия VPN подключения истёк или оно было удалено.\n"
                "Купите новый VPN для продолжения использования.",
                reply_markup=inline.my_vpn_menu(has_vpns=False)
            )
            return
        
        days_left = vpn_info.get('remaining_days', 0)
        link = vpn_info.get('link', '')
        
        # Если ссылки нет в базе, генерируем заново
        if not link:
            tariff_id = "free" if vpn_info.get('price', 0) == 0 else vpn_info.get('tariff_id', '14')
            tariff = TARIFFS.get(tariff_id)
            
            result = await create_vpn_connection(user_id, tariff_id, tariff)
            if result.get("success"):
                link = result["link"]
                # Обновляем ссылку в базе
                db.client.table('vpn_orders').update({'link': link}).eq('id', vpn_id).execute()
        
        # Если VPN скоро истекает, показываем предупреждение
        warning = ""
        if days_left <= 2:
            warning = f"\n\n⚠️ *Внимание!* VPN истекает через {days_left} дней!"
        
        text = (
            f"🔑 Данные VPN #{vpn_id}\n"
            f"📍 Сервер: Амстердам\n"
            f"📅 Осталось дней: {days_left}{warning}\n\n"
            f"🔗 Готовая ссылка (скопируйте):\n"
            f"<code>{link}</code>\n\n"
            f"📱 Как подключить:\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. Вставьте в приложение (V2RayNG, Nekoray)\n"
            f"3. Включите VPN"
        )
        
        await safe_edit_message(
            callback,
            text,
            reply_markup=inline.after_free_vpn_menu(),
            parse_mode='HTML'
        )
            
    except Exception as e:
        logger.error(f"❌ Ошибка показа ключа: {e}", exc_info=True)
        await callback.answer("❌ Ошибка")
        await safe_edit_message(
            callback,
            "❌ Ошибка загрузки ключа",
            reply_markup=inline.back_to_main()
        )

@router.callback_query(F.data.startswith("refresh_vpn_"))
async def refresh_vpn_handler(callback: types.CallbackQuery):
    await callback.answer("🔄 Данные обновлены")
    vpn_id = int(callback.data.replace("refresh_vpn_", ""))
    await vpn_detail_handler(callback)

# ========== БАЛАНС И ПОПОЛНЕНИЕ ==========

@router.callback_query(F.data == "balance")
async def balance_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    
    await safe_edit_message(
        callback,
        f"💰 Ваш баланс: {balance} руб\n\nВыберите способ пополнения:",
        reply_markup=inline.payment_methods()
    )

# ========== ПОКУПКА VPN ==========

@router.callback_query(F.data == "buy_vpn")
async def buy_vpn_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    balance = user.get('balance', 0) if user else 0
    
    await safe_edit_message(
        callback,
        f"🛒 Выберите тариф VPN:\n\n💳 Ваш баланс: {balance} руб",
        reply_markup=inline.tariff_menu(user_id=user_id)
    )

@router.callback_query(F.data == "get_free_vpn")
async def get_free_vpn_handler(callback: types.CallbackQuery):
    """Обработчик кнопки 'Получить 3 дня бесплатно' из главного меню"""
    user_id = callback.from_user.id
    
    # Проверяем, не получал ли уже бесплатный тариф
    orders = db.get_user_orders(user_id)
    free_orders = [o for o in orders if o.get('price', 0) == 0]
    
    if free_orders:
        await callback.answer("❌ Вы уже получали бесплатный VPN")
        await safe_edit_message(
            callback,
            "❌ Вы уже использовали бесплатный VPN\n\n"
            "Бесплатный тариф (3 дня / 15GB) доступен только один раз.\n\n"
            "Выберите платный тариф для продолжения:",
            reply_markup=inline.tariff_menu(user_id=user_id)
        )
        return
    
    tariff = TARIFFS.get("free")
    
    await safe_edit_message(
        callback,
        f"🎁 Бесплатный VPN\n\n"
        f"📅 Срок: {tariff['days']} дней\n"
        f"📊 Трафик: {tariff['traffic_gb']}GB\n"
        f"💰 Цена: Бесплатно\n\n"
        f"Получить бесплатный VPN?",
        reply_markup=inline.confirm_free_vpn_menu()
    )

@router.callback_query(F.data == "select_free_tariff")
async def select_free_tariff_handler(callback: types.CallbackQuery):
    """Обработчик выбора бесплатного тарифа из меню тарифов"""
    await get_free_vpn_handler(callback)

@router.callback_query(F.data.startswith("select_tariff_"))
async def select_tariff_handler(callback: types.CallbackQuery):
    """Обработчик выбора платного тарифа"""
    tariff_id = callback.data.replace("select_tariff_", "")
    
    logger.info(f"🔍 Выбран тариф: {tariff_id}")
    
    tariff = TARIFFS.get(tariff_id)
    
    if not tariff:
        logger.error(f"❌ Тариф '{tariff_id}' не найден")
        await callback.answer(f"❌ Тариф не найден")
        return
    
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await safe_edit_message(callback, "❌ Пользователь не найден", reply_markup=inline.back_to_main())
        return
    
    balance = user.get('balance', 0)
    
    await safe_edit_message(
        callback,
        f"🛒 Подтверждение покупки\n\n"
        f"📍 Сервер: Амстердам\n"
        f"📅 Срок: {tariff['days']} дней\n"
        f"📊 Трафик: {'Безлимит' if tariff['traffic_gb'] == 0 else f'{tariff['traffic_gb']}GB'}\n"
        f"💰 Стоимость: {tariff['price']} руб\n\n"
        f"💳 Ваш баланс: {balance} руб",
        reply_markup=inline.confirm_purchase_menu(tariff_id, tariff['price'], tariff)
    )

@router.callback_query(F.data.startswith("buy_tariff_"))
async def buy_tariff_handler(callback: types.CallbackQuery):
    """Обработчик покупки платного тарифа"""
    try:
        data = callback.data
        logger.info(f"💰 Покупка тарифа. Callback: {data}")
        
        # Парсим callback_data: buy_tariff_14  или buy_tariff_14_promocode
        parts = data.split('_')
        
        if len(parts) < 3:
            await callback.answer("❌ Ошибка формата данных")
            return
        
        tariff_id = parts[2]  # "14", "30", "90"
        promo_code = parts[3] if len(parts) > 3 else ""
        
        logger.info(f"💰 tariff_id='{tariff_id}', promo_code='{promo_code}'")
        
        # Получаем тариф
        tariff = TARIFFS.get(tariff_id)
        if not tariff:
            logger.error(f"❌ Тариф '{tariff_id}' не найден")
            await callback.answer(f"❌ Тариф не найден")
            return
        
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        balance = user.get('balance', 0)
        original_price = tariff['price']
        final_price = original_price
        discount_percent = 0
        discount_amount = 0
        
        # Проверяем промокод
        if promo_code:
            promo_info = db.get_promocode(promo_code)
            if promo_info and promo_info.get('type') == 'discount':
                if db.has_user_used_promocode(user_id, promo_code):
                    await safe_edit_message(
                        callback,
                        f"❌ Вы уже использовали промокод {promo_code}",
                        reply_markup=inline.confirm_purchase_menu(
                            tariff_id, original_price, tariff
                        )
                    )
                    return
                
                discount_percent = promo_info.get('value', 0)
                discount_amount = original_price * (discount_percent / 100)
                final_price = original_price - discount_amount
                final_price = max(final_price, 0)
        
        # Проверяем баланс
        if balance < final_price:
            await safe_edit_message(
                callback,
                f"❌ Недостаточно средств!\n\n"
                f"💳 Ваш баланс: {balance}₽\n"
                f"💰 Нужно: {final_price:.0f}₽",
                reply_markup=inline.payment_methods()
            )
            return
        
        await safe_edit_message(
            callback,
            "🔐 Создаю VPN подключение...\n\n⏳ Пожалуйста, подождите 10-15 секунд",
            reply_markup=None
        )
        
        # Создаем VPN подключение
        result = await create_vpn_connection(user_id, tariff_id, tariff, promo_code)
        
        if not result.get("success"):
            await safe_edit_message(
                callback,
                f"❌ Ошибка создания VPN: {result.get('error', 'Неизвестная ошибка')}",
                reply_markup=inline.back_to_main()
            )
            return
        
        uuid = result["uuid"]
        link = result["link"]
        
        # Списание денег
        success = db.update_balance(user_id, -final_price)
        if not success:
            await safe_edit_message(
                callback,
                "❌ Ошибка списания средств",
                reply_markup=inline.back_to_main()
            )
            return
        
        # Отмечаем промокод как использованный
        if promo_code and discount_percent > 0:
            promo = db.get_promocode(promo_code)
            if promo:
                new_used_count = promo.get('used_count', 0) + 1
                db.client.table('promocodes') \
                    .update({'used_count': new_used_count}) \
                    .eq('code', promo_code.upper()) \
                    .execute()
            
            usage_data = {
                'user_id': user_id,
                'promo_code': promo_code.upper(),
                'value_given': discount_amount,
                'used_at': datetime.now(timezone.utc).isoformat(),
                'purchase_amount': final_price,
                'tariff_id': tariff_id
            }
            db.client.table('promo_usages').insert(usage_data).execute()
            
            used_promocodes = user.get('used_promocodes', [])
            if promo_code.upper() not in used_promocodes:
                used_promocodes.append(promo_code.upper())
                db.client.table('users') \
                    .update({'used_promocodes': used_promocodes}) \
                    .eq('user_id', user_id) \
                    .execute()
        
        # Сохраняем заказ
        order = db.create_vpn_order(user_id, tariff_id, uuid, link)
        
        if not order:
            db.update_balance(user_id, final_price)
            await safe_edit_message(
                callback,
                "❌ Ошибка сохранения заказа",
                reply_markup=inline.back_to_main()
            )
            return
        
        # Обновляем баланс
        user = db.get_user(user_id)
        new_balance = user.get('balance', 0) if user else 0
        
        # Показываем результат
        discount_text = f"\n🎫 Скидка: {discount_percent}%\n💰 Экономия: {discount_amount:.0f}₽" if discount_percent > 0 else ""
        traffic_text = "Безлимит" if tariff['traffic_gb'] == 0 else f"{tariff['traffic_gb']}GB"
        
        text = (
            f"✅ VPN успешно создан!{discount_text}\n\n"
            f"📅 Срок: {tariff['days']} дней\n"
            f"📊 Трафик: {traffic_text}\n"
            f"💰 Списано: {final_price:.0f}₽\n"
            f"💳 Баланс: {new_balance}₽\n\n"
            f"🔗 Готовая ссылка:\n"
            f"<code>{link}</code>\n\n"
            f"📱 Как подключиться:\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. Вставьте в приложение\n"
            f"3. Нажмите Подключить"
        )
        
        await safe_edit_message(
            callback,
            text,
            reply_markup=inline.after_purchase_menu(),
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка покупки тарифа: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка")
        await safe_edit_message(
            callback,
            "❌ Произошла ошибка при покупке\n\nПожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=inline.main_menu(user_id=callback.from_user.id)
        )

@router.callback_query(F.data == "confirm_free_purchase")
async def confirm_free_purchase_handler(callback: types.CallbackQuery):
    """Обработчик подтверждения покупки бесплатного VPN"""
    user_id = callback.from_user.id
    
    try:
        # Проверяем еще раз
        orders = db.get_user_orders(user_id)
        free_orders = [o for o in orders if o.get('price', 0) == 0]
        
        if free_orders:
            await callback.answer("❌ Вы уже получали бесплатный VPN")
            await safe_edit_message(
                callback,
                "❌ Вы уже использовали бесплатный VPN",
                reply_markup=inline.tariff_menu(user_id=user_id)
            )
            return
        
        tariff = TARIFFS.get("free")
        
        await safe_edit_message(
            callback,
            "🔄 Создаю бесплатный VPN...\n\n⏳ Пожалуйста, подождите 10-15 секунд",
            reply_markup=None
        )
        
        # Создаем VPN подключение
        result = await create_vpn_connection(user_id, "free", tariff)
        
        if result.get("success"):
            # Сохраняем в базу данных
            vpn_order = db.create_vpn_order(
                user_id=user_id,
                tariff_id="free",
                uuid=result["uuid"],
                link=result["link"]
            )
            
            if vpn_order:
                balance = db.get_balance(user_id)
                
                text = (
                    f"✅ Бесплатный VPN создан!\n\n"
                    f"📅 Срок: {tariff['days']} дней\n"
                    f"📊 Трафик: {tariff['traffic_gb']}GB\n"
                    f"💰 Цена: Бесплатно\n"
                    f"💳 Баланс: {balance}₽\n\n"
                    f"🔗 Готовая ссылка:\n"
                    f"<code>{result['link']}</code>\n\n"
                    f"📱 Как подключиться:\n"
                    f"1. Скопируйте ссылку выше\n"
                    f"2. Вставьте в приложение (v2rayNG, Nekoray)\n"
                    f"3. Включите VPN"
                )
                
                await safe_edit_message(
                    callback,
                    text,
                    reply_markup=inline.after_free_vpn_menu(),
                    parse_mode='HTML'
                )
            else:
                await safe_edit_message(
                    callback,
                    "❌ Ошибка сохранения VPN в базе данных",
                    reply_markup=inline.main_menu(user_id=user_id)
                )
        else:
            await safe_edit_message(
                callback,
                f"❌ Ошибка создания VPN: {result.get('error', 'Неизвестная ошибка')}",
                reply_markup=inline.main_menu(user_id=user_id)
            )
                
    except Exception as e:
        logger.error(f"❌ Ошибка создания бесплатного VPN: {e}", exc_info=True)
        await safe_edit_message(
            callback,
            f"❌ Ошибка при создании VPN:\n\n{str(e)[:200]}",
            reply_markup=inline.main_menu(user_id=user_id)
        )

# ========== ПАРТНЕРКА ==========

@router.callback_query(F.data == "referral")
async def referral_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    # Получаем или генерируем реферальный код
    referral_code = user.get('referral_code')
    if not referral_code:
        import hashlib
        referral_code = f"REF{hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()}"
        db.client.table('users').update({'referral_code': referral_code}).eq('user_id', user_id).execute()
    
    # Получаем статистику
    stats = db.get_referral_stats(user_id)
    
    # Получаем username бота для ссылки
    bot_username = (await callback.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    text = (
        f"👥 Партнерская программа\n\n"
        f"🔗 Ваша ссылка:\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 Статистика:\n"
        f"• Приглашено: {stats['total_referrals']} чел\n"
        f"• Заработано: {stats['total_bonus']} руб\n\n"
        f"🎁 Бонусы:\n"
        f"• За каждого друга: +35 руб\n"
        f"• Начисляется мгновенно"
    )
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=inline.referral_menu(),
        parse_mode='HTML'
    )

# ========== ПОМОЩЬ И ПОДДЕРЖКА ==========

@router.callback_query(F.data == "help")
async def help_handler(callback: types.CallbackQuery):
    await safe_edit_message(
        callback,
        "❓ Помощь и часто задаваемые вопросы\n\n"
        "Выберите раздел помощи:",
        reply_markup=inline.help_menu()
    )

@router.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await safe_edit_message(
        callback,
        "📞 Поддержка\n\n"
        "Если у вас возникли проблемы с VPN подключением, оплатой или другими вопросами, "
        "свяжитесь с нашей поддержкой:",
        reply_markup=inline.support_menu()
    )

@router.callback_query(F.data == "faq")
async def faq_handler(callback: types.CallbackQuery):
    await safe_edit_message(
        callback,
        "📖 FAQ и вопросы\n\n"
        "1. Как подключить VPN?\n"
        "   - Скачайте приложение V2RayNG или Nekoray\n"
        "   - Скопируйте ссылку из бота\n"
        "   - Вставьте в приложение и подключитесь\n\n"
        "2. VPN не работает?\n"
        "   - Проверьте баланс\n"
        "   - Убедитесь, что VPN активен\n"
        "   - Попробуйте переподключиться\n\n"
        "3. Как пополнить баланс?\n"
        "   - Нажмите 'Баланс' в меню\n"
        "   - Выберите способ оплаты\n\n"
        "4. Проблемы с оплатой?\n"
        "   - Обратитесь в поддержку",
        reply_markup=inline.help_menu()
    )

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@router.callback_query(F.data == "main_menu")
async def main_menu_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    admin = is_admin(user_id)
    
    await safe_edit_message(
        callback,
        "🏠 Главное меню\n\n"
        "Выберите нужный раздел:",
        reply_markup=inline.main_menu(user_id=user_id, admin=admin)
    )

@router.callback_query(F.data == "use_promo")
async def use_promo_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик ввода промокода"""
    await state.set_state("waiting_promo_for_balance")
    
    await safe_edit_message(
        callback,
        "🎫 Введите промокод для получения бонуса на баланс:",
        reply_markup=inline.cancel_menu(target="main_menu")
    )

@router.callback_query(F.data.startswith("promo_history_"))
async def promo_history_handler(callback: types.CallbackQuery):
    """История использованных промокодов"""
    page_str = callback.data.replace("promo_history_", "")
    page = int(page_str) if page_str.isdigit() else 0
    
    user_id = callback.from_user.id
    used_promos = db.get_user_promo_history(user_id)
    
    if not used_promos:
        await safe_edit_message(
            callback,
            "📭 Вы еще не использовали промокоды\n\n"
            "Промокоды можно получить:\n"
            "• В акциях и розыгрышах\n"
            "• От партнеров\n"
            "• В группах бота",
            reply_markup=inline.promo_history_menu(page=page, total_pages=1)
        )
        return
    
    # Пагинация
    per_page = 5
    total_promos = len(used_promos)
    total_pages = (total_promos + per_page - 1) // per_page
    
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_promos)
    promos_page = used_promos[start_idx:end_idx]
    
    text = f"🎫 История промокодов (стр. {page+1}/{total_pages})\n\n"
    
    for i, promo in enumerate(promos_page, start=start_idx+1):
        promo_code = promo.get('promo_code', 'N/A')
        value = promo.get('value_given', 0)
        used_at = promo.get('used_at', 'N/A')[:10]
        
        text += f"{i}. Код: {promo_code}\n"
        text += f"   Получено: {value}₽\n"
        text += f"   Дата: {used_at}\n\n"
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=inline.promo_history_menu(
            history_list=promos_page,
            page=page,
            total_pages=total_pages
        )
    )

@router.callback_query(F.data == "no_action")
async def no_action_handler(callback: types.CallbackQuery):
    """Обработчик для неактивных кнопок"""
    await callback.answer()