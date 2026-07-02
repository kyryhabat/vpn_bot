from aiogram import Router, types, F
from aiogram.filters import Command
from supabase_client import db
from keyboards import inline
from config import ADMIN_IDS
from datetime import datetime

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    text = message.text or ""
    
    # Проверяем есть ли реферальный код
    referral_code = None
    parts = text.split()
    if len(parts) > 1:
        code = parts[1].strip()
        if code.startswith('REF'):
            referral_code = code
    
    # Создаем или получаем пользователя
    user = db.get_user(user_id)
    
    if not user:
        # Новый пользователь
        user = db.create_user(user_id, username, full_name)
        
        # Если есть реферальный код
        if referral_code:
            # Находим пригласившего
            referrer = None
            try:
                result = db.client.table('users').select('*').eq('referral_code', referral_code).execute()
                if result.data:
                    referrer = result.data[0]
            except:
                pass
            
            if referrer and referrer['user_id'] != user_id:
                # Начисляем 50 рублей
                bonus = 35
                new_balance = float(referrer.get('balance', 0)) + bonus
                
                # Обновляем баланс
                db.client.table('users').update({'balance': new_balance}).eq('user_id', referrer['user_id']).execute()
                
                # Сохраняем в referrals
                db.client.table('referrals').insert({
                    'referrer_id': referrer['user_id'],
                    'new_user_id': user_id,
                    'bonus_amount': bonus,
                    'created_at': datetime.now().isoformat()
                }).execute()
                
                # Отправляем уведомление
                try:
                    await message.bot.send_message(
                        chat_id=referrer['user_id'],
                        text=f"🎉 +{bonus}₽ НА БАЛАНС!\n\n"
                             f"👤 @{username or 'пользователь'} зарегистрировался\n"
                             f"💰 Вам начислено: {bonus} руб"
                    )
                except:
                    pass
    
    # Показываем меню
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        f"👋 Привет, {full_name or 'друг'}!",
        reply_markup=inline.main_menu(user_id=user_id, admin=is_admin)
    )

@router.message(Command("ref"))
async def ref_command(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if not user:
        await message.answer("❌ Сначала /start")
        return
    
    # Получаем или создаем код
    referral_code = user.get('referral_code')
    if not referral_code:
        import hashlib
        referral_code = f"REF{hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()}"
        db.client.table('users').update({'referral_code': referral_code}).eq('user_id', user_id).execute()
    
    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    await message.answer(
        f"🔗 Твоя ссылка:\n"
        f"{ref_link}\n\n"
        f"Отправь другу и получи 35₽ когда он зарегистрируется",
        reply_markup=inline.referral_menu()
    )

@router.message(Command("menu"))
async def menu_handler(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    await message.answer(
        "🏠 Главное меню",
        reply_markup=inline.main_menu(user_id=user_id, admin=is_admin)
    )

@router.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "❓ Помощь\n\n"
        "Используйте кнопки меню для навигации.",
        reply_markup=inline.help_menu()
    )