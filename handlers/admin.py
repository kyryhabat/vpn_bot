# admin.py - АДМИНКА С ПАГИНАЦИЕЙ, УПРАВЛЕНИЕМ ПОЛЬЗОВАТЕЛЯМИ И ПРОМОКОДАМИ
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards import inline
from supabase_client import db
from config import BOT_TOKEN, ADMIN_IDS
from datetime import datetime
import asyncio

router = Router()
bot = Bot(token=BOT_TOKEN)

def is_admin(user_id: int):
    """Проверка является ли пользователь админом"""
    try:
        # Проверяем встроенных админов из config.py
        if user_id in ADMIN_IDS:
            return True
        
        # Проверяем в базе данных
        admin = db.get_admin_by_id(user_id)
        return admin is not None
    except Exception as e:
        print(f"⚠️ Ошибка проверки админа {user_id}: {e}")
        return user_id in ADMIN_IDS

class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    waiting_admin_username = State()
    waiting_admin_remove = State()
    waiting_broadcast_message = State()

class AdminPromoStates(StatesGroup):
    waiting_promo_value = State()
    waiting_promo_max_uses = State()
    waiting_promo_expiry = State()
    waiting_promo_custom_code = State()

# ========== АДМИН КОМАНДЫ ==========

@router.message(Command("admin"))
async def admin_command(message: types.Message):
    """Команда /admin"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👨‍💼 Админ-панель\n\nВыберите действие:",
        reply_markup=inline.admin_menu()
    )

@router.callback_query(F.data == "admin_menu")
async def admin_menu_handler(callback: types.CallbackQuery):
    """Главное меню админки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "👨‍💼 Админ-панель\n\nВыберите действие:",
        reply_markup=inline.admin_menu()
    )

# ========== ПОЛЬЗОВАТЕЛИ С ПАГИНАЦИЕЙ ==========

@router.callback_query(F.data.startswith("admin_users_"))
async def admin_users_paginated_handler(callback: types.CallbackQuery):
    """Показать пользователей с пагинацией"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    try:
        page = int(callback.data.split("_")[-1])
    except:
        page = 0
    
    per_page = 10
    all_users = db.get_all_users()
    
    if not all_users:
        await callback.message.edit_text(
            "📭 Пользователей нет",
            reply_markup=inline.admin_menu()
        )
        return
    
    total_users = len(all_users)
    
    # Ограничиваем страницу
    total_pages = (total_users + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    
    # Вычисляем начальный и конечный индексы
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_users)
    users_page = all_users[start_idx:end_idx]
    
    total_balance = sum(user.get('balance', 0) for user in all_users)
    
    text = f"👥 Все пользователи\n\n"
    text += f"📊 Всего: {total_users} чел\n"
    text += f"💰 Общий баланс: {total_balance} руб\n"
    text += f"📄 Страница {page+1} из {total_pages}\n\n"
    text += f"Нажмите на пользователя для управления:"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_users_list_menu(users_page, page, total_users, per_page)
    )

@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_detail_handler(callback: types.CallbackQuery):
    """Показать детальную информацию о пользователе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    try:
        user_id = int(callback.data.split("_")[-1])
    except:
        await callback.answer("❌ Ошибка: неверный ID пользователя")
        return
    
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    username = user.get('username', 'без имени') or 'без имени'
    full_name = user.get('full_name', '') or ''
    balance = user.get('balance', 0)
    
    # Получаем дополнительные данные
    orders = db.get_user_orders(user_id)
    active_vpns = db.get_active_vpns(user_id)
    
    text = f"👤 Детальная информация о пользователе\n\n"
    text += f"🆔 ID: {user_id}\n"
    text += f"👤 Username: @{username}\n"
    if full_name:
        text += f"👤 Имя: {full_name}\n"
    text += f"💳 Баланс: {balance} руб\n\n"
    
    text += f"📊 Статистика:\n"
    text += f"• 📦 Заказов: {len(orders)} шт\n"
    text += f"• 🔐 Активных VPN: {len(active_vpns)} шт\n"
    text += f"• 📅 Регистрация: {user.get('created_at', 'неизвестно')[:10] if user.get('created_at') else 'неизвестно'}\n\n"
    
    text += f"Выберите действие:"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_user_detail_menu(user_id, user)
    )

@router.callback_query(F.data.startswith("admin_user_balance_"))
async def admin_user_balance_handler(callback: types.CallbackQuery, state: FSMContext):
    """Изменить баланс пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    try:
        user_id = int(callback.data.split("_")[-1])
    except:
        await callback.answer("❌ Ошибка: неверный ID")
        return
    
    user = db.get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    username = user.get('username', 'user') or 'user'
    
    # Сохраняем данные в состоянии
    await state.update_data(
        target_user_id=user_id,
        target_username=username,
        current_balance=user.get('balance', 0)
    )
    await state.set_state(AdminStates.waiting_amount)
    
    await callback.message.edit_text(
        f"💰 Изменение баланса пользователя\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"💳 Текущий баланс: {user.get('balance', 0)} руб\n\n"
        f"Введите сумму для изменения:\n"
        f"• Положительное число - пополнение\n"
        f"• Отрицательное число - списание\n"
        f"Пример: 100, -50, 0 (обнулить)",
        reply_markup=inline.cancel_admin_menu()
    )

# ========== ЗАКАЗЫ VPN С ПАГИНАЦИЕЙ ==========

@router.callback_query(F.data.startswith("admin_orders_"))
async def admin_orders_paginated_handler(callback: types.CallbackQuery):
    """Показать все заказы с пагинацией"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    try:
        page = int(callback.data.split("_")[-1])
    except:
        page = 0
    
    per_page = 10
    orders = db.get_all_orders()
    
    if not orders:
        await callback.message.edit_text(
            "📭 Заказов нет",
            reply_markup=inline.admin_menu()
        )
        return
    
    total_orders = len(orders)
    total_pages = (total_orders + per_page - 1) // per_page
    
    # Ограничиваем страницу
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    
    # Вычисляем начальный и конечный индексы
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_orders)
    
    active_orders = [o for o in orders if o.get('status') == 'active']
    total_revenue = sum(o.get('price', 0) for o in orders)
    
    text = f"📦 Все заказы VPN (страница {page+1}/{total_pages})\n\n"
    text += f"📊 Всего: {total_orders} зак.\n"
    text += f"🟢 Активных: {len(active_orders)} зак.\n"
    text += f"💰 Выручка: {total_revenue} руб\n\n"
    
    # Показываем заказы на текущей странице
    for i, order in enumerate(orders[start_idx:end_idx], start_idx + 1):
        user_id = order.get('user_id', 'N/A')
        days = order.get('days', 0)
        price = order.get('price', 0)
        status = "🟢" if order.get('status') == 'active' else "🔴"
        created_at = order.get('created_at', '')
        
        # Форматируем дату
        date_str = ""
        if created_at:
            try:
                date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = date_obj.strftime("%d.%m %H:%M")
            except:
                date_str = created_at[:10]
        
        text += f"{i}. User: {user_id}\n"
        text += f"   📅 {days}д | 💰 {price}руб | {status}\n"
        if date_str:
            text += f"   📅 {date_str}\n"
        text += "\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_orders_list_menu(
            orders[start_idx:end_idx],
            page, 
            total_orders, 
            per_page
        )
    )

# ========== ВЫДАЧА БАЛАНСА ==========

@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать выдачу баланса"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await state.set_state(AdminStates.waiting_user_id)
    await callback.message.edit_text(
        "💰 Выдать баланс пользователю\n\nВведите ID пользователя (только цифры):",
        reply_markup=inline.cancel_admin_menu()
    )

@router.message(AdminStates.waiting_user_id)
async def admin_add_user_id(message: types.Message, state: FSMContext):
    """Получить ID пользователя для выдачи баланса"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    
    try:
        user_id = int(message.text.strip())
        user = db.get_user(user_id)
        
        if not user:
            await message.answer(
                f"❌ Пользователь не найден\n\n"
                f"Пользователь с ID {user_id} не зарегистрирован в боте.",
                reply_markup=inline.cancel_admin_menu()
            )
            return
        
        await state.update_data(user_id=user_id, target_username=user.get('username', 'user'))
        await state.set_state(AdminStates.waiting_amount)
        
        await message.answer(
            f"✅ Пользователь найден\n\n"
            f"👤 ID: {user_id}\n"
            f"👤 Имя: {user.get('full_name', 'Не указано')}\n"
            f"💳 Текущий баланс: {user.get('balance', 0)} руб\n\n"
            f"Введите сумму для пополнения (можно отрицательную для списания):",
            reply_markup=inline.cancel_admin_menu()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат ID\n\nID должен состоять только из цифр",
            reply_markup=inline.cancel_admin_menu()
        )

@router.message(AdminStates.waiting_amount)
async def admin_add_amount(message: types.Message, state: FSMContext):
    """Получить сумму для пополнения"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    try:
        amount = float(message.text.strip())
        data = await state.get_data()
        
        # Проверяем, откуда пришел запрос
        if 'target_user_id' in data:
            # Запрос из детального меню пользователя
            user_id = data['target_user_id']
            target_username = data.get('target_username', 'user')
        else:
            # Запрос из старого меню
            user_id = data['user_id']
            target_username = data.get('target_username', 'user')
    
    except ValueError:
        await message.answer(
            "❌ Неверная сумма\n\nВведите число, например: 100 или -50",
            reply_markup=inline.cancel_admin_menu()
        )
        return
    
    # Пополняем баланс
    success = db.update_balance(user_id, amount)
    
    if success:
        # Получаем обновленные данные
        user = db.get_user(user_id)
        new_balance = user.get('balance', 0)
        
        # Отправляем сообщение админу
        admin_message = (
            f"✅ Баланс успешно обновлен!\n\n"
            f"👤 Пользователь: @{target_username} (ID: {user_id})\n"
            f"💰 Изменение: {amount:+} руб\n"
            f"💳 Новый баланс: {new_balance} руб\n"
            f"👨‍💼 Админ: @{message.from_user.username or 'admin'}"
        )
        
        await message.answer(admin_message, reply_markup=inline.admin_menu())
        
        # Отправляем уведомление пользователю
        try:
            user_message = (
                f"🎁 Ваш баланс был изменен администратором!\n\n"
                f"💰 Изменение: {amount:+} руб\n"
                f"💳 Новый баланс: {new_balance} руб\n"
                f"👨‍💼 Администратор: @{message.from_user.username or 'админ'}\n\n"
                f"Спасибо, что вы с нами! ❤️"
            )
            
            await bot.send_message(chat_id=user_id, text=user_message)
        except Exception as e:
            print(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    else:
        await message.answer(
            "❌ Ошибка обновления баланса\n\nПожалуйста, попробуйте позже",
            reply_markup=inline.admin_menu()
        )
    
    await state.clear()

# ========== УПРАВЛЕНИЕ АДМИНАМИ ==========

@router.callback_query(F.data == "admin_manage_admins")
async def admin_manage_admins_handler(callback: types.CallbackQuery):
    """Меню управления администраторами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "👑 Управление администраторами\n\nВыберите действие:",
        reply_markup=inline.admin_manage_admins_menu()
    )

@router.callback_query(F.data == "admin_add_admin")
async def admin_add_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    """Добавить администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await state.set_state(AdminStates.waiting_admin_username)
    await callback.message.edit_text(
        "➕ Добавить администратора\n\n"
        "Введите username пользователя (без @):\n"
        "Пример: username123",
        reply_markup=inline.cancel_admin_menu()
    )

@router.callback_query(F.data == "admin_remove_admin")
async def admin_remove_admin_handler(callback: types.CallbackQuery, state: FSMContext):
    """Удалить администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await state.set_state(AdminStates.waiting_admin_remove)
    await callback.message.edit_text(
        "➖ Удалить администратора\n\n"
        "Введите username администратора (без @):\n"
        "Пример: username123",
        reply_markup=inline.cancel_admin_menu()
    )

@router.callback_query(F.data == "admin_list_admins")
async def admin_list_admins_handler(callback: types.CallbackQuery):
    """Показать список администраторов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    admins = db.get_all_admins()
    
    if not admins:
        await callback.message.edit_text(
            "👑 Список администраторов\n\n📭 Администраторов не найдено",
            reply_markup=inline.admin_manage_admins_menu()
        )
        return
    
    text = "👑 Список администраторов\n\n"
    
    for i, admin in enumerate(admins, 1):
        user_id = admin.get('user_id', 'N/A')
        username = admin.get('username', 'без username') or 'без username'
        full_name = admin.get('full_name', 'без имени') or 'без имени'
        balance = admin.get('balance', 0)
        
        text += f"{i}. @{username}\n"
        text += f"   ID: {user_id}\n"
        text += f"   Имя: {full_name}\n"
        text += f"   Баланс: {balance} руб\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_manage_admins_menu()
    )

@router.message(AdminStates.waiting_admin_username)
async def admin_process_username(message: types.Message, state: FSMContext):
    """Обработать username для добавления админа"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    username = message.text.strip().replace('@', '')
    
    if len(username) < 3:
        await message.answer(
            "❌ Слишком короткий username\n\n"
            "Username должен быть не менее 3 символов.\n"
            "Попробуйте снова:",
            reply_markup=inline.cancel_admin_menu()
        )
        return
    
    # Ищем пользователя в базе
    users = db.get_user_by_username(username)
    
    if not users:
        await message.answer(
            f"❌ Пользователь не найден\n\n"
            f"Пользователь @{username} не зарегистрирован в боте.\n"
            f"Пользователь должен сначала запустить бота (/start).",
            reply_markup=inline.admin_manage_admins_menu()
        )
        await state.clear()
        return
    
    # Найден один пользователь
    user = users[0]
    user_id = user.get('user_id')
    username = user.get('username')
    
    # Проверяем, не админ ли уже
    admin_check = db.get_admin_by_id(user_id)
    if admin_check:
        await message.answer(
            f"ℹ️ Пользователь уже администратор\n\n"
            f"@{username} уже имеет права администратора.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        await state.clear()
        return
    
    # Запоминаем для подтверждения
    await state.update_data(user_id=user_id, username=username)
    
    await message.answer(
        f"✅ Пользователь найден\n\n"
        f"👤 Username: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Имя: {user.get('full_name', 'Не указано')}\n\n"
        f"Добавить @{username} в администраторы?",
        reply_markup=inline.confirm_add_admin_menu(user_id, username)
    )

@router.callback_query(F.data.startswith("admin_confirm_add_"))
async def admin_confirm_add_handler(callback: types.CallbackQuery, state: FSMContext):
    """Подтвердить добавление админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    user_id = int(callback.data.replace("admin_confirm_add_", ""))
    data = await state.get_data()
    username = data.get('username', 'user')
    
    # Назначаем админа
    success = db.set_user_admin(user_id, True)
    
    if success:
        await callback.message.edit_text(
            f"✅ Администратор добавлен!\n\n"
            f"👤 @{username} теперь администратор\n"
            f"🆔 ID: {user_id}\n\n"
            f"Пользователь получит уведомление о новых правах.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        
        # Отправляем уведомление пользователю
        try:
            admin_message = (
                f"👑 Вам назначены права администратора!\n\n"
                f"Поздравляем! Теперь вы администратор VPN бота.\n\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"👨‍💼 Назначил: @{callback.from_user.username or 'админ'}\n\n"
                f"Для доступа к админ-панели:\n"
                f"• Используйте команду /admin\n"
                f"• Или нажмите кнопку 'Админ' в главном меню\n\n"
                f"⚠️ Внимание: Не передавайте свои права другим!"
            )
            
            await bot.send_message(chat_id=user_id, text=admin_message)
        except Exception as e:
            print(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    else:
        await callback.message.edit_text(
            "❌ Ошибка назначения администратора\n\nПожалуйста, попробуйте позже.",
            reply_markup=inline.admin_manage_admins_menu()
        )
    
    await state.clear()

@router.message(AdminStates.waiting_admin_remove)
async def admin_process_remove_username(message: types.Message, state: FSMContext):
    """Обработать username для удаления админа"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    username = message.text.strip().replace('@', '')
    
    if len(username) < 3:
        await message.answer(
            "❌ Слишком короткий username\n\n"
            "Username должен быть не менее 3 символов.\n"
            "Попробуйте снова:",
            reply_markup=inline.cancel_admin_menu()
        )
        return
    
    # Ищем админа в базе
    users = db.get_user_by_username(username)
    
    if not users:
        await message.answer(
            f"❌ Администратор не найден\n\n"
            f"Администратор с username @{username} не найден.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        await state.clear()
        return
    
    # Фильтруем только админов
    admins = [user for user in users if db.get_admin_by_id(user.get('user_id'))]
    
    if not admins:
        await message.answer(
            f"ℹ️ Пользователь не является администратором\n\n"
            f"@{username} не имеет прав администратора.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        await state.clear()
        return
    
    # Найден один админ
    admin = admins[0]
    user_id = admin.get('user_id')
    username = admin.get('username')
    
    # Нельзя удалить себя
    if user_id == message.from_user.id:
        await message.answer(
            "⚠️ Нельзя удалить себя\n\n"
            "Вы не можете удалить свои собственные права администратора.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        await state.clear()
        return
    
    # Запоминаем для подтверждения
    await state.update_data(user_id=user_id, username=username)
    
    await message.answer(
        f"⚠️ Подтверждение удаления\n\n"
        f"Вы уверены, что хотите удалить права администратора у @{username}?\n\n"
        f"👤 Username: @{username}\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Имя: {admin.get('full_name', 'Не указано')}\n\n"
        f"После удаления пользователь потеряет доступ к админ-панели.",
        reply_markup=inline.confirm_remove_admin_menu(user_id, username)
    )

@router.callback_query(F.data.startswith("admin_confirm_remove_"))
async def admin_confirm_remove_handler(callback: types.CallbackQuery, state: FSMContext):
    """Подтвердить удаление админа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    user_id = int(callback.data.replace("admin_confirm_remove_", ""))
    data = await state.get_data()
    username = data.get('username', 'user')
    
    # Снимаем права админа
    success = db.set_user_admin(user_id, False)
    
    if success:
        await callback.message.edit_text(
            f"✅ Права администратора удалены!\n\n"
            f"👤 @{username} больше не администратор\n"
            f"🆔 ID: {user_id}\n\n"
            f"Пользователь получит уведомление об изменении прав.",
            reply_markup=inline.admin_manage_admins_menu()
        )
        
        # Отправляем уведомление пользователю
        try:
            user_message = (
                f"⚠️ Ваши права администратора отозваны\n\n"
                f"Ваши права администратора в VPN боте были отозваны.\n\n"
                f"🆔 Ваш ID: {user_id}\n"
                f"👨‍💼 Отозвал: @{callback.from_user.username or 'админ'}\n\n"
                f"Теперь у вас нет доступа к админ-панели.\n"
                f"Если это ошибка, свяжитесь с администратором."
            )
            
            await bot.send_message(chat_id=user_id, text=user_message)
        except Exception as e:
            print(f"⚠️ Не удалось отправить уведомление пользователю {user_id}: {e}")
    
    else:
        await callback.message.edit_text(
            "❌ Ошибка удаления прав администратора\n\nПожалуйста, попробуйте позже.",
            reply_markup=inline.admin_manage_admins_menu()
        )
    
    await state.clear()

# ========== УПРАВЛЕНИЕ ПРОМОКОДАМИ (ТОЛЬКО НА БАЛАНС) ==========

@router.callback_query(F.data == "admin_promo_menu")
async def admin_promo_menu_handler(callback: types.CallbackQuery):
    """Меню управления промокодами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "🎫 Управление промокодами\n\nВыберите действие:",
        reply_markup=inline.admin_promo_menu()
    )

@router.callback_query(F.data == "admin_create_promo")
async def admin_create_promo_handler(callback: types.CallbackQuery, state: FSMContext):
    """Создание промокода на баланс"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await state.update_data(promo_type='balance')
    await state.set_state(AdminPromoStates.waiting_promo_value)
    
    await callback.message.edit_text(
        "💰 Создание промокода на баланс\n\n"
        "Введите сумму в рублях, которая будет начислена пользователю:\n"
        "• Минимум: 10 руб\n"
        "• Максимум: 10000 руб\n\n"
        "Пример: 100, 500, 1000",
        reply_markup=inline.cancel_admin_menu()
    )

@router.message(AdminPromoStates.waiting_promo_value)
async def admin_promo_value_handler(message: types.Message, state: FSMContext):
    """Обработка значения промокода"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    try:
        value = float(message.text.strip())
        
        # Проверяем допустимые значения
        if value < 10 or value > 10000:
            await message.answer(
                "❌ Неверная сумма\n\nСумма должна быть от 10 до 10000 рублей",
                reply_markup=inline.cancel_admin_menu()
            )
            return
        
        await state.update_data(promo_value=value)
        await state.set_state(AdminPromoStates.waiting_promo_max_uses)
        
        await message.answer(
            f"✅ Значение установлено: {value}₽\n\n"
            f"Введите максимальное количество использований:\n"
            f"• Минимум: 1\n"
            f"• Максимум: 1000\n"
            f"• Для безлимита введите 0\n\n"
            f"Пример: 10, 100, 0 (безлимит)",
            reply_markup=inline.cancel_admin_menu()
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат\n\nВведите число",
            reply_markup=inline.cancel_admin_menu()
        )

@router.message(AdminPromoStates.waiting_promo_max_uses)
async def admin_promo_max_uses_handler(message: types.Message, state: FSMContext):
    """Обработка максимального количества использований"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    try:
        max_uses = int(message.text.strip())
        
        if max_uses < 0 or max_uses > 1000:
            await message.answer(
                "❌ Неверное количество\n\nКоличество должно быть от 0 до 1000",
                reply_markup=inline.cancel_admin_menu()
            )
            return
        
        await state.update_data(promo_max_uses=max_uses)
        await state.set_state(AdminPromoStates.waiting_promo_expiry)
        
        await message.answer(
            f"✅ Максимальное использование: {max_uses if max_uses > 0 else 'безлимит'}\n\n"
            f"Введите срок действия в днях:\n"
            f"• Минимум: 1 день\n"
            f"• Максимум: 365 дней\n"
            f"• По умолчанию: 30 дней\n\n"
            f"Пример: 7, 30, 90",
            reply_markup=inline.cancel_admin_menu()
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат\n\nВведите целое число",
            reply_markup=inline.cancel_admin_menu()
        )

@router.message(AdminPromoStates.waiting_promo_expiry)
async def admin_promo_expiry_handler(message: types.Message, state: FSMContext):
    """Обработка срока действия"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    try:
        expiry_days = int(message.text.strip())
        
        if expiry_days < 1 or expiry_days > 365:
            await message.answer(
                "❌ Неверный срок\n\nСрок должен быть от 1 до 365 дней",
                reply_markup=inline.cancel_admin_menu()
            )
            return
        
        await state.update_data(promo_expiry_days=expiry_days)
        await state.set_state(AdminPromoStates.waiting_promo_custom_code)
        
        await message.answer(
            f"✅ Срок действия: {expiry_days} дней\n\n"
            f"Введите кастомный код промокода (или 'нет' для автоматической генерации):\n"
            f"• Должен быть уникальным\n"
            f"• Рекомендуется 6-12 символов\n"
            f"• Только буквы и цифры\n\n"
            f"Пример: SUMMER2024, WELCOME100, BONUS50\n"
            f"Или просто: нет",
            reply_markup=inline.cancel_admin_menu()
        )
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат\n\nВведите целое число дней",
            reply_markup=inline.cancel_admin_menu()
        )

@router.message(AdminPromoStates.waiting_promo_custom_code)
async def admin_promo_custom_code_handler(message: types.Message, state: FSMContext):
    """Обработка кастомного кода"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    custom_code = message.text.strip().upper()
    
    # Если пользователь ввел "нет" или пустую строку, используем автоматическую генерацию
    if custom_code.lower() == 'нет' or not custom_code:
        custom_code = None
    
    data = await state.get_data()
    promo_value = data.get('promo_value')
    promo_max_uses = data.get('promo_max_uses')
    promo_expiry_days = data.get('promo_expiry_days')
    
    # Создаем промокод
    promo_code = db.create_promocode(
        promo_type='balance',
        value=promo_value,
        created_by=message.from_user.id,
        max_uses=promo_max_uses,
        expiry_days=promo_expiry_days,
        custom_code=custom_code
    )
    
    if promo_code:
        uses_text = f"{promo_max_uses} использований" if promo_max_uses > 0 else "безлимитное использование"
        
        success_text = (
            f"✅ Промокод создан!\n\n"
            f"🎫 Код: <code>{promo_code['code']}</code>\n"
            f"💰 Тип: на баланс\n"
            f"🎯 Значение: {promo_value}₽\n"
            f"📊 Использований: {uses_text}\n"
            f"📅 Срок действия: {promo_expiry_days} дней\n"
            f"👨‍💼 Создал: @{message.from_user.username or 'админ'}\n\n"
            f"Промокод активен и готов к использованию!"
        )
        
        await message.answer(
            success_text,
            reply_markup=inline.admin_promo_menu(),
            parse_mode='HTML'
        )
    else:
        error_text = (
            f"❌ Ошибка создания промокода\n\n"
            f"Возможные причины:\n"
            f"• Промокод с таким кодом уже существует\n"
            f"• Ошибка подключения к базе данных\n\n"
            f"Попробуйте другой код или оставьте автоматическую генерацию."
        )
        
        await message.answer(
            error_text,
            reply_markup=inline.admin_promo_menu()
        )
    
    await state.clear()

# ========== СПИСОК ПРОМОКОДОВ ==========

@router.callback_query(F.data.startswith("admin_list_promos_"))
async def admin_list_promos_handler(callback: types.CallbackQuery):
    """Список промокодов с пагинацией"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    try:
        page = int(callback.data.replace("admin_list_promos_", ""))
    except:
        page = 0
    
    per_page = 10
    all_promos = db.get_all_promocodes()
    
    if not all_promos:
        await callback.message.edit_text(
            "📭 Промокодов нет\n\nСоздайте первый промокод",
            reply_markup=inline.admin_promo_menu()
        )
        return
    
    total_promos = len(all_promos)
    
    # Ограничиваем страницу
    total_pages = (total_promos + per_page - 1) // per_page
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
    
    # Вычисляем начальный и конечный индексы
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, total_promos)
    promos_page = all_promos[start_idx:end_idx]
    
    # Статистика
    active_promos = sum(1 for p in all_promos if p.get('is_active', True))
    total_uses = sum(p.get('used_count', 0) for p in all_promos)
    total_balance_given = sum(p.get('value', 0) * p.get('used_count', 0) for p in all_promos)
    
    text = f"📋 Список промокодов (страница {page+1}/{total_pages})\n\n"
    text += f"📊 Статистика:\n"
    text += f"• Всего: {total_promos} шт\n"
    text += f"• Активных: {active_promos} шт\n"
    text += f"• Использований: {total_uses} раз\n"
    text += f"• Выдано баланса: {total_balance_given}₽\n\n"
    text += f"Нажмите на промокод для управления:"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_promocodes_list_menu(promos_page, page, total_promos, per_page)
    )

@router.callback_query(F.data.startswith("admin_promo_detail_"))
async def admin_promo_detail_handler(callback: types.CallbackQuery):
    """Детальная информация о промокоде"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    promo_code = callback.data.replace("admin_promo_detail_", "")
    promo = db.get_promocode(promo_code)
    
    if not promo:
        await callback.answer("❌ Промокод не найден")
        return
    
    value = promo.get('value', 0)
    max_uses = promo.get('max_uses', 0)
    used_count = promo.get('used_count', 0)
    is_active = promo.get('is_active', True)
    created_by = promo.get('created_by', 'N/A')
    
    # Получаем информацию о создателе
    creator_info = "Неизвестно"
    if created_by:
        creator = db.get_user(created_by)
        if creator:
            creator_info = f"@{creator.get('username', 'N/A')}"
    
    # Парсим даты
    created_at = promo.get('created_at', '')
    expires_at = promo.get('expires_at', '')
    
    created_str = "Неизвестно"
    expires_str = "Неизвестно"
    
    try:
        if created_at:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            created_str = dt.strftime("%d.%m.%Y %H:%M")
        
        if expires_at:
            dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            expires_str = dt.strftime("%d.%m.%Y %H:%M")
            
            # Проверяем истек ли срок
            now = datetime.now()
            if dt < now:
                expires_str += " (Истек)"
    except:
        pass
    
    text = f"🎫 Детальная информация о промокоде\n\n"
    text += f"🔤 Код: <code>{promo_code}</code>\n"
    text += f"💰 Тип: На баланс\n"
    text += f"🎯 Значение: {value}₽\n"
    text += f"📊 Использовано: {used_count}/{max_uses if max_uses > 0 else '∞'}\n"
    text += f"🟢 Статус: {'Активен' if is_active else 'Неактивен'}\n"
    text += f"👨‍💼 Создал: {creator_info}\n"
    text += f"📅 Создан: {created_str}\n"
    text += f"📅 Истекает: {expires_str}\n\n"
    
    # Получаем историю использований
    try:
        response = db.client.table('promo_usages') \
            .select('*') \
            .eq('promo_code', promo_code) \
            .order('used_at', desc=True) \
            .limit(5) \
            .execute()
        
        usages = response.data if response.data else []
        
        if usages:
            text += f"📋 Последние использования:\n"
            for i, usage in enumerate(usages, 1):
                user_id = usage.get('user_id', 'N/A')
                used_at = usage.get('used_at', '')
                value_given = usage.get('value_given', 0)
                
                # Форматируем дату
                date_str = "Неизвестно"
                if used_at:
                    try:
                        dt = datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                        date_str = dt.strftime("%d.%m %H:%M")
                    except:
                        pass
                
                text += f"{i}. User {user_id} - {value_given}₽ - {date_str}\n"
    except:
        pass
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_promo_detail_menu(promo_code, promo),
        parse_mode='HTML'
    )

# ========== ДЕАКТИВАЦИЯ ПРОМОКОДА ==========

@router.callback_query(F.data.startswith("admin_promo_deactivate_"))
async def admin_promo_deactivate_handler(callback: types.CallbackQuery):
    """Деактивация промокода"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    promo_code = callback.data.replace("admin_promo_deactivate_", "")
    promo = db.get_promocode(promo_code)
    
    if not promo:
        await callback.answer("❌ Промокод не найден")
        return
    
    if not promo.get('is_active', True):
        await callback.answer("ℹ️ Промокод уже неактивен")
        return
    
    await callback.message.edit_text(
        f"⚠️ Подтверждение деактивации\n\n"
        f"Вы уверены, что хотите деактивировать промокод?\n\n"
        f"🎫 Код: <code>{promo_code}</code>\n"
        f"💰 Тип: На баланс\n"
        f"🎯 Значение: {promo.get('value', 0)}₽\n"
        f"📊 Использовано: {promo.get('used_count', 0)}/{promo.get('max_uses', 0)}\n\n"
        f"После деактивации промокод нельзя будет использовать.",
        reply_markup=inline.confirm_deactivate_promo_menu(promo_code),
        parse_mode='HTML'
    )

@router.callback_query(F.data.startswith("admin_confirm_deactivate_"))
async def admin_confirm_deactivate_handler(callback: types.CallbackQuery):
    """Подтверждение деактивации промокода"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    promo_code = callback.data.replace("admin_confirm_deactivate_", "")
    
    # Деактивируем промокод
    success = db.deactivate_promocode(promo_code)
    
    if success:
        await callback.message.edit_text(
            f"✅ Промокод деактивирован!\n\n"
            f"🎫 Код: <code>{promo_code}</code>\n\n"
            f"Промокод больше не может быть использован.",
            reply_markup=inline.admin_promo_menu(),
            parse_mode='HTML'
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка деактивации промокода\n\nПожалуйста, попробуйте позже.",
            reply_markup=inline.admin_promo_menu()
        )

# ========== СТАТИСТИКА ПРОМОКОДОВ ==========

@router.callback_query(F.data == "admin_promo_stats")
async def admin_promo_stats_handler(callback: types.CallbackQuery):
    """Статистика промокодов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    all_promos = db.get_all_promocodes()
    
    if not all_promos:
        await callback.message.edit_text(
            "📊 Статистика промокодов\n\nПромокодов еще нет",
            reply_markup=inline.admin_promo_menu()
        )
        return
    
    # Считаем статистику
    total_promos = len(all_promos)
    active_promos = sum(1 for p in all_promos if p.get('is_active', True))
    expired_promos = sum(1 for p in all_promos if not p.get('is_active', True))
    
    total_uses = sum(p.get('used_count', 0) for p in all_promos)
    total_balance_given = sum(p.get('value', 0) * p.get('used_count', 0) for p in all_promos)
    
    # Самые популярные промокоды
    most_used = sorted(all_promos, key=lambda x: x.get('used_count', 0), reverse=True)[:5]
    
    text = f"📊 Статистика промокодов\n\n"
    text += f"📈 Общая статистика:\n"
    text += f"• Всего промокодов: {total_promos} шт\n"
    text += f"• Активных: {active_promos} шт\n"
    text += f"• Неактивных: {expired_promos} шт\n"
    text += f"• Всего использований: {total_uses} раз\n"
    text += f"• Выдано баланса: {total_balance_given}₽\n\n"
    
    text += f"🏆 Самые популярные промокоды:\n"
    for i, promo in enumerate(most_used, 1):
        promo_code = promo.get('code', 'N/A')
        used_count = promo.get('used_count', 0)
        value = promo.get('value', 0)
        
        text += f"{i}. 🎫 {promo_code} - {value}₽ ({used_count} раз)\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_promo_menu()
    )

# ========== РАССЫЛКА ==========

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать рассылку"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await state.set_state(AdminStates.waiting_broadcast_message)
    await callback.message.edit_text(
        "📢 Рассылка сообщений\n\n"
        "Введите сообщение для рассылки:\n"
        "Вы можете использовать HTML разметку.\n\n"
        "Пример:\n"
        "<b>Важное объявление!</b>\n"
        "Мы запустили новую функцию...",
        reply_markup=inline.cancel_admin_menu()
    )

@router.message(AdminStates.waiting_broadcast_message)
async def admin_broadcast_message_handler(message: types.Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        await state.clear()
        return
    
    users = db.get_all_users()
    total_users = len(users)
    
    await state.update_data(
        broadcast_message=message.text,
        broadcast_total=total_users
    )
    
    await message.answer(
        f"✅ Сообщение получено\n\n"
        f"📊 Получателей: {total_users} пользователей\n\n"
        f"Подтвердите отправку:",
        reply_markup=inline.admin_broadcast_confirmation_menu(message.text, total_users)
    )

@router.callback_query(F.data == "admin_broadcast_confirm")
async def admin_broadcast_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    data = await state.get_data()
    message_text = data.get('broadcast_message', '')
    total_users = data.get('broadcast_total', 0)
    
    if not message_text:
        await callback.answer("❌ Нет сообщения для рассылки")
        await state.clear()
        return
    
    await callback.message.edit_text(
        f"📤 Начинаю рассылку...\n\n"
        f"📊 Всего получателей: {total_users}\n"
        f"⏳ Это может занять некоторое время...",
        reply_markup=inline.admin_broadcast_progress_menu(0, total_users)
    )
    
    # Получаем всех пользователей
    users = db.get_all_users()
    success_count = 0
    failed_count = 0
    
    # Отправляем сообщения
    for i, user in enumerate(users, 1):
        user_id = user.get('user_id')
        
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text,
                parse_mode='HTML'
            )
            success_count += 1
        except Exception as e:
            print(f"⚠️ Ошибка отправки пользователю {user_id}: {e}")
            failed_count += 1
        
        # Обновляем прогресс каждые 10 сообщений
        if i % 10 == 0 or i == total_users:
            try:
                await callback.message.edit_text(
                    f"📤 Рассылка в процессе...\n\n"
                    f"📊 Прогресс: {i}/{total_users}\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {failed_count}",
                    reply_markup=inline.admin_broadcast_progress_menu(i, total_users)
                )
            except:
                pass
        
        # Небольшая задержка, чтобы не превысить лимиты Telegram
        await asyncio.sleep(0.1)
    
    # Завершение рассылки
    await callback.message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Итоги:\n"
        f"• Всего получателей: {total_users}\n"
        f"• ✅ Успешно отправлено: {success_count}\n"
        f"• ❌ Не удалось отправить: {failed_count}\n\n"
        f"Процент доставки: {(success_count/total_users*100):.1f}%",
        reply_markup=inline.admin_broadcast_completed_menu(success_count, failed_count)
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_broadcast_edit")
async def admin_broadcast_edit_handler(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование сообщения рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "✏️ Редактирование сообщения\n\n"
        "Введите новое сообщение для рассылки:\n"
        "Вы можете использовать HTML разметку.",
        reply_markup=inline.cancel_admin_menu()
    )

# ========== СТАТИСТИКА ==========

@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: types.CallbackQuery):
    """Показать общую статистику"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    users = db.get_all_users()
    orders = db.get_all_orders()
    payments = db.get_all_payments()
    admins = db.get_all_admins()
    promos = db.get_all_promocodes()
    
    # Фильтруем активных пользователей
    active_users = []
    for user in users:
        active_vpns = db.get_active_vpns(user['user_id'])
        if active_vpns:
            active_users.append(user)
    
    completed_payments = [p for p in payments if p.get('status') == 'completed']
    
    total_revenue = sum(o.get('price', 0) for o in orders)
    total_deposits = sum(p.get('amount', 0) for p in completed_payments)
    
    # Статистика промокодов
    promo_uses = sum(p.get('used_count', 0) for p in promos)
    promo_balance_given = sum(p.get('value', 0) * p.get('used_count', 0) for p in promos)
    
    text = (
        f"📊 Статистика бота\n\n"
        f"👥 Пользователи:\n"
        f"• Всего: {len(users)}\n"
        f"• Активных: {len(active_users)}\n"
        f"• Администраторов: {len(admins)}\n"
        f"• Общий баланс: {sum(u.get('balance', 0) for u in users)} руб\n\n"
        
        f"📦 Заказы:\n"
        f"• Всего: {len(orders)}\n"
        f"• Активных: {len([o for o in orders if o.get('status') == 'active'])}\n"
        f"• Выручка: {total_revenue} руб\n\n"
        
        f"💰 Финансы:\n"
        f"• Пополнений: {total_deposits} руб\n"
        f"• Средний чек: {total_revenue/len(orders) if orders else 0:.1f} руб\n\n"
        
        f"🎫 Промокоды:\n"
        f"• Всего: {len(promos)} шт\n"
        f"• Использований: {promo_uses} раз\n"
        f"• Выдано баланса: {promo_balance_given}₽"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=inline.admin_menu()
    )