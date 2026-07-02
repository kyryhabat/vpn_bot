# promo.py - Обработчики для промокодов (РАБОЧАЯ ВЕРСИЯ)
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from supabase_client import db
from datetime import datetime, timezone
from config import TARIFFS
from keyboards import inline
from aiogram.exceptions import TelegramBadRequest

router = Router()

class PromoStates(StatesGroup):
    waiting_promo_code = State()

# Утилиты
async def safe_edit_message(callback: types.CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения"""
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Уже обновлено")
        else:
            raise e

# Локальные функции клавиатуры
def get_cancel_promo_menu():
    """Клавиатура для отмены ввода промокода"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_promo")]
        ]
    )

def get_use_promo_menu():
    """Клавиатура для использования промокода"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎫 Использовать промокод", callback_data="use_promo")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )

def get_main_menu_keyboard(user_id: int = None):
    """Клавиатура главного меню"""
    return inline.main_menu(user_id)


# Callback для использования промокода
@router.callback_query(F.data == "use_promo")
async def use_promo_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало использования промокода"""
    await state.set_state(PromoStates.waiting_promo_code)
    await callback.message.edit_text(
        "🎫 Введите промокод:\n\n"
        "Введите код промокода, который у вас есть.\n"
        "Или нажмите 'Отмена' для возврата.",
        reply_markup=get_cancel_promo_menu()
    )

# Обработка введенного промокода
@router.message(PromoStates.waiting_promo_code)
async def process_promo_code(message: types.Message, state: FSMContext):
    """Обработка введенного промокода"""
    promo_code = message.text.strip().upper()
    user_id = message.from_user.id
    
    # Получаем промокод из базы
    promo = db.get_promocode(promo_code)
    
    if not promo:
        await message.answer(
            f"❌ Промокод не найден\n\n"
            f"Промокод <code>{promo_code}</code> не существует.",
            reply_markup=get_use_promo_menu(),
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Проверяем активен ли промокод
    if not promo.get('is_active', True):
        await message.answer(
            f"❌ Промокод неактивен\n\n"
            f"Промокод <code>{promo_code}</code> больше не действителен.",
            reply_markup=get_use_promo_menu(),
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Проверяем истек ли срок
    expires_at = promo.get('expires_at')
    if expires_at:
        try:
            expiry_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if expiry_date < datetime.now():
                await message.answer(
                    f"❌ Промокод истек\n\n"
                    f"Промокод <code>{promo_code}</code> истек {expiry_date.strftime('%d.%m.%Y')}.",
                    reply_markup=get_use_promo_menu(),
                    parse_mode='HTML'
                )
                await state.clear()
                return
        except:
            pass
    
    # Проверяем лимит использований
    max_uses = promo.get('max_uses', 0)
    used_count = promo.get('used_count', 0)
    if max_uses > 0 and used_count >= max_uses:
        await message.answer(
            f"❌ Промокод уже использован\n\n"
            f"Промокод <code>{promo_code}</code> был использован максимальное количество раз ({max_uses}).",
            reply_markup=get_use_promo_menu(),
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Проверяем, использовал ли уже пользователь этот промокод
    if db.has_user_used_promocode(user_id, promo_code):
        await message.answer(
            f"ℹ️ Вы уже использовали этот промокод\n\n"
            f"Промокод <code>{promo_code}</code> можно использовать только один раз.",
            reply_markup=get_use_promo_menu(),
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Применяем промокод
    promo_type = promo.get('type')
    value = promo.get('value', 0)
    
    if promo_type == 'balance':
        # Промокод на баланс
        success = db.apply_promocode_to_balance(user_id, promo_code, value)
        if success:
            # Получаем обновленный баланс
            user = db.get_user(user_id)
            new_balance = user.get('balance', 0)
            
            await message.answer(
                f"✅ Промокод успешно применен!\n\n"
                f"🎫 Код: <code>{promo_code}</code>\n"
                f"💰 Тип: На баланс\n"
                f"💸 Начислено: {value}₽\n"
                f"💳 Новый баланс: {new_balance}₽\n\n"
                f"Спасибо, что используете нашего бота! 🎉",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode='HTML'
            )
        else:
            await message.answer(
                f"❌ Ошибка применения промокода\n\n"
                f"Не удалось применить промокод. Попробуйте позже.",
                reply_markup=get_use_promo_menu()
            )
    else:
        # Обрабатываем другие типы промокодов как невалидные
        await message.answer(
            f"❌ Неподдерживаемый тип промокода\n\n"
            f"Промокод <code>{promo_code}</code> имеет неподдерживаемый тип.",
            reply_markup=get_use_promo_menu(),
            parse_mode='HTML'
        )
        await state.clear()
        return

# Отмена ввода промокода
@router.callback_query(F.data == "cancel_promo")
async def cancel_promo(callback: types.CallbackQuery, state: FSMContext):
    """Отмена ввода промокода"""
    await state.clear()
    await safe_edit_message(
        callback,
        "🎫 Использование промокода отменено",
        reply_markup=get_main_menu_keyboard(callback.from_user.id)
    )

# История промокодов
@router.callback_query(F.data.startswith("promo_history_"))
async def promo_history_handler(callback: types.CallbackQuery):
    """История использованных промокодов"""
    try:
        # Получаем номер страницы
        page_str = callback.data.replace("promo_history_", "")
        page = int(page_str) if page_str.isdigit() else 0
        
        user_id = callback.from_user.id
        
        # Получаем историю промокодов пользователя
        history = db.get_promo_usage_history(user_id=user_id)
        
        if not history:
            await safe_edit_message(
                callback,
                "📭 У вас нет использованных промокодов\n\n"
                "Вы еще не использовали ни одного промокода.",
                reply_markup=inline.promo_history_menu(page=page, total_pages=1)
            )
            return
        
        # Пагинация
        per_page = 5
        total_items = len(history)
        total_pages = (total_items + per_page - 1) // per_page
        
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, total_items)
        page_history = history[start_idx:end_idx]
        
        text = "📊 История ваших промокодов\n\n"
        
        for i, usage in enumerate(page_history, start=start_idx+1):
            promo_code = usage.get('promo_code', 'N/A')
            value_given = usage.get('value_given', 0)
            used_at = usage.get('used_at', '')
            
            # Форматируем дату
            try:
                dt = datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                date_str = dt.strftime('%d.%m.%Y %H:%M')
            except:
                date_str = used_at[:10]
            
            text += f"{i}. 🎫 {promo_code}\n"
            text += f"   💰 Начислено: {value_given}₽\n"
            text += f"   📅 Использован: {date_str}\n\n"
        
        await safe_edit_message(
            callback,
            text,
            reply_markup=inline.promo_history_menu(
                history_list=page_history,
                page=page,
                total_pages=total_pages
            )
        )
        
    except Exception as e:
        print(f"❌ Ошибка истории промокодов: {e}")
        await callback.answer("❌ Ошибка")
        await safe_edit_message(
            callback,
            "❌ Ошибка загрузки истории промокодов",
            reply_markup=inline.back_to_main()
        )

# Перенаправление на профиль
@router.callback_query(F.data == "profile")
async def profile_from_promo(callback: types.CallbackQuery):
    """Перенаправление на профиль"""
    from handlers.buy_vpn import profile_handler
    await profile_handler(callback)

# Перенаправление на баланс
@router.callback_query(F.data == "balance")
async def balance_from_promo(callback: types.CallbackQuery):
    """Перенаправление на баланс"""
    from handlers.buy_vpn import balance_handler
    await balance_handler(callback)