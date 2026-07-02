
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards import inline
from supabase_client import SupabaseClient
from yookassa_client import yookassa_client
from cryptobot_client import cryptobot_client
from datetime import datetime
from aiogram.fsm.state import State, StatesGroup
import hashlib

router = Router()
supabase = SupabaseClient()

class DepositStates(StatesGroup):
    waiting_amount = State()

# Кэш для хранения хешей сообщений
message_cache = {}

def get_message_hash(text: str, markup_data: str = "") -> str:
    """Генерируем хеш сообщения для проверки изменений"""
    content = f"{text}|{markup_data}"
    return hashlib.md5(content.encode()).hexdigest()

# ========== ПОПОЛНЕНИЕ БАЛАНСА ==========

@router.callback_query(F.data == "deposit")
async def deposit_handler(callback: types.CallbackQuery):
    """Меню пополнения баланса"""
    user_id = callback.from_user.id
    user = supabase.get_user(user_id)
    balance = user.get('balance', 0) if user else 0
    
    await callback.message.edit_text(
        f"💰 Пополнение баланса\n\n"
        f"💳 Текущий баланс: {balance} руб\n\n"
        f"👇 Выберите способ пополнения:",
        reply_markup=inline.payment_methods()
    )

@router.callback_query(F.data.startswith("payment_"))
async def payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Выбор способа оплаты"""
    method = callback.data.replace("payment_", "")
    
    if method == "yookassa":
        await state.set_state(DepositStates.waiting_amount)
        await state.update_data(payment_method="yookassa")
        
        await callback.message.edit_text(
            "💳 ЮKassa (карты РФ)\n\n"
            "Введите сумму для пополнения (рубли):\n"
            "• Минимум: 150 руб\n"
            "• Максимум: 50000 руб\n\n"
            "Напишите только цифры:",
            reply_markup=inline.cancel_deposit_menu()
        )
    
    elif method == "crypto_bot":
        # Проверяем доступность CryptoBot
        check = cryptobot_client.get_me()
        
        if not check['success']:
            await callback.message.edit_text(
                "❌ CryptoBot временно недоступен\n\n"
                "Пожалуйста, используйте ЮKassa для оплаты.\n",
                reply_markup=inline.payment_methods()
            )
            return
        
        await state.set_state(DepositStates.waiting_amount)
        await state.update_data(payment_method="crypto_bot")
        
        await callback.message.edit_text(
            "🤖 Crypto Bot (USDT)\n\n"
            "Введите сумму пополнения в рублях:\n"
            "• Минимум: 150 руб\n"
            "• Максимум: 50000 руб\n"
            "• Курс: ~1 USDT = 90 RUB\n\n"
            "Напишите только цифры:",
            reply_markup=inline.cancel_deposit_menu()
        )

@router.message(DepositStates.waiting_amount)
async def deposit_amount_handler(message: types.Message, state: FSMContext):
    """Обработка суммы платежа"""
    try:
        amount = float(message.text.strip())
        
        # Проверка суммы
        if amount < 150 or amount > 50000:
            await message.answer(
                "❌ Неверная сумма\n\n"
                "Сумма должна быть от 150 до 50000 рублей",
                reply_markup=inline.payment_methods()
            )
            await state.clear()
            return
        
        data = await state.get_data()
        payment_method = data.get('payment_method')
        user_id = message.from_user.id
        
        # ========== CRYPTOBOT ==========
        if payment_method == "crypto_bot":
            result = cryptobot_client.create_invoice(
                user_id=user_id,
                amount_rub=amount,
                description=f"Пополнение баланса на {amount} руб"
            )
            
            if result['success']:
                await message.answer(
                    f"🤖 Счет создан в Crypto Bot!\n\n"
                    f"💰 Сумма: {amount} руб\n"
                    f"💰 В USDT: ~{result['amount_usdt']}\n"
                    f"⏳ Срок оплаты: 1 час\n\n"
                    f"👇 Нажмите на кнопку ниже для оплаты:",
                    reply_markup=inline.crypto_payment_menu(
                        result['pay_url'], 
                        amount,
                        result['invoice_id']
                    )
                )
            else:
                await message.answer(
                    f"❌ Ошибка создания счета\n\n"
                    f"{result.get('error', 'Неизвестная ошибка')}\n\n"
                    f"Попробуйте другой способ оплаты.",
                    reply_markup=inline.payment_methods()
                )
        
        # ========== YOOKASSA ==========
        elif payment_method == "yookassa":
            result = await yookassa_client.create_payment(
                user_id=user_id,
                amount=amount,
                description=f"Пополнение баланса на {amount} руб"
            )
            
            if result['success']:
                await message.answer(
                    f"✅ Счет создан!\n\n"
                    f"💰 Сумма: {amount} руб\n"
                    f"💳 Оплата: Банковской картой РФ\n"
                    f"🔄 Статус: Ожидает оплаты\n"
                    f"📝 ID:{result['payment_id'][:15]}...\n\n"
                    f"👇 Нажмите на кнопку ниже для оплаты:",
                    reply_markup=inline.yookassa_payment_menu(
                        result['confirmation_url'], 
                        amount,
                        result['payment_id']
                    )
                )
            else:
                await message.answer(
                    f"❌ Ошибка создания счета\n\n"
                    f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                    reply_markup=inline.payment_methods()
                )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат\n\n"
            "Введите число, например: 1000",
            reply_markup=inline.cancel_deposit_menu()
        )
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await message.answer(
            "❌ <b>Ошибка обработки платежа</b>",
            reply_markup=inline.payment_methods()
        )
        await state.clear()

# ========== ПРОВЕРКА ПЛАТЕЖЕЙ YOOKASSA ==========

@router.callback_query(F.data.startswith("check_payment_"))
async def check_yookassa_payment_handler(callback: types.CallbackQuery):
    """Проверить статус платежа ЮKassa"""
    payment_id = callback.data.replace("check_payment_", "")
    user_id = callback.from_user.id
    
    await callback.answer("🔄 Проверяем ЮKassa...")
    
    try:
        # Проверяем статус в ЮKassa
        result = await yookassa_client.check_payment_status(payment_id)
        
        if not result['success']:
            new_text = (
                f"❌ Ошибка проверки\n\n"
                f"Не удалось проверить статус платежа.\n"
                f"Попробуйте позже."
            )
            new_markup = inline.check_payment_again_menu(payment_id)
            await _safe_edit_message(callback, new_text, new_markup)
            return
        
        status = result['status']
        amount = result.get('amount', 0)
        is_paid = result.get('paid', False)
        
        # Ищем платеж в БД
        response = supabase.client.table('payments') \
            .select('*') \
            .eq('invoice_id', payment_id) \
            .execute()
        
        db_payment = response.data[0] if response.data else None
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Если платеж успешен
        if status == 'succeeded' and is_paid:
            # Проверяем, не обработан ли уже
            if db_payment and db_payment.get('status') != 'completed':
                # Начисляем баланс
                success = supabase.update_balance(user_id, amount)
                
                if success:
                    # Обновляем статус
                    supabase.client.table('payments') \
                        .update({
                            'status': 'completed',
                            'completed_at': datetime.now().isoformat()
                        }) \
                        .eq('invoice_id', payment_id) \
                        .execute()
                    
                    print(f"✅ Платеж {payment_id} обработан, баланс user {user_id} пополнен")
            
            # Показываем успех
            user = supabase.get_user(user_id)
            new_balance = user.get('balance', 0) if user else 0
            
            new_text = (
                f"✅ Оплата прошла успешно!\n\n"
                f"💰 Зачислено: {amount} руб\n"
                f"💳 Новый баланс: {new_balance} руб\n"
                f"📝 ID: <code>{payment_id[:15]}...</code>\n\n"
                f"Спасибо за пополнение! 🎉"
            )
            new_markup = inline.after_payment_menu()
            await _safe_edit_message(callback, new_text, new_markup)
        
        # Если платеж в обработке
        elif status in ['pending', 'waiting_for_capture']:
            status_text = {
                'pending': '⏳ Ожидает оплаты',
                'waiting_for_capture': '⏳ Ожидает подтверждения'
            }.get(status, status)
            
            new_text = (
                f"{status_text}\n\n"
                f"💰 Сумма: {amount} руб\n"
                f"📝 ID: <code>{payment_id[:15]}...</code>\n"
                f"⏰ Проверено: {timestamp}\n\n"
                f"Если вы уже оплатили, подождите 2-3 минуты\n"
                f"и проверьте снова."
            )
            new_markup = inline.check_payment_again_menu(payment_id)
            await _safe_edit_message(callback, new_text, new_markup)
        
        # Если платеж отменен
        elif status == 'canceled':
            if db_payment:
                supabase.client.table('payments') \
                    .update({'status': 'canceled'}) \
                    .eq('invoice_id', payment_id) \
                    .execute()
            
            new_text = (
                f"❌ Платеж отменен\n\n"
                f"💰 Сумма: {amount} руб\n"
                f"📝 ID: <code>{payment_id[:15]}...</code>\n\n"
                f"Вы можете создать новый платеж."
            )
            new_markup = inline.payment_methods()
            await _safe_edit_message(callback, new_text, new_markup)
        
        # Другие статусы
        else:
            new_text = (
                f"ℹ️ Статус платежа\n\n"
                f"💰 Сумма: {amount} руб\n"
                f"🔄 Статус: {status}\n"
                f"📝 ID: <code>{payment_id[:15]}...</code>\n"
                f"⏰ Проверено: {timestamp}\n\n"
                f"Попробуйте проверить позже."
            )
            new_markup = inline.check_payment_again_menu(payment_id)
            await _safe_edit_message(callback, new_text, new_markup)
    
    except Exception as e:
        print(f"❌ Ошибка проверки платежа: {e}")
        
        new_text = (
            "❌ Ошибка проверки\n\n"
            "Пожалуйста, попробуйте позже."
        )
        new_markup = inline.payment_methods()
        await _safe_edit_message(callback, new_text, new_markup)

# ========== ПРОВЕРКА ПЛАТЕЖЕЙ CRYPTOBOT ==========

@router.callback_query(F.data.startswith("check_crypto_"))
async def check_crypto_payment_handler(callback: types.CallbackQuery):
    """Проверить статус платежа CryptoBot"""
    invoice_id = callback.data.replace("check_crypto_", "")
    user_id = callback.from_user.id
    
    await callback.answer("🔄 Проверяем CryptoBot...")
    
    try:
        result = cryptobot_client.check_invoice(invoice_id)
        
        if not result['success']:
            new_text = (
                f"❌ Ошибка проверки\n\n"
                f"Не удалось проверить статус счёта.\n"
                f"Попробуйте позже."
            )
            new_markup = inline.crypto_check_again_menu(invoice_id)
            await _safe_edit_message(callback, new_text, new_markup)
            return
        
        status = result['status']
        amount_usdt = result.get('amount', 0)
        
        # Получаем актуальный курс
        rate_result = cryptobot_client.get_exchange_rate("USDT")
        rate = rate_result.get('rate', 90) if rate_result['success'] else 90
        
        # Конвертируем USDT в RUB
        amount_rub = round(amount_usdt * rate, 2)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Ищем платеж в БД
        response = supabase.client.table('payments') \
            .select('*') \
            .eq('invoice_id', invoice_id) \
            .execute()
        
        db_payment = response.data[0] if response.data else None
        
        # ========== СТАТУС "PAID" = ОПЛАЧЕНО ==========
        if status == 'paid':
            # Проверяем payload (user_id) для безопасности
            payload = result.get('payload')
            if payload and str(payload) != str(user_id):
                new_text = (
                    f"⚠️ Ошибка верификации\n\n"
                    f"Счёт предназначен для другого пользователя.\n"
                    f"Обратитесь в поддержку."
                )
                new_markup = inline.contact_support_menu()
                await _safe_edit_message(callback, new_text, new_markup)
                return
            
            # Проверяем, не обработан ли уже
            if db_payment and db_payment.get('status') != 'completed':
                # Находим оригинальную сумму из БД
                original_amount = db_payment.get('amount', amount_rub)
                
                # Начисляем баланс
                success = supabase.update_balance(user_id, original_amount)
                
                if success:
                    # Обновляем статус
                    supabase.client.table('payments') \
                        .update({
                            'status': 'completed',
                            'completed_at': datetime.now().isoformat(),
                            'metadata': result.get('metadata', {})
                        }) \
                        .eq('invoice_id', invoice_id) \
                        .execute()
                    
                    print(f"✅ CryptoBot платеж {invoice_id} обработан")
                else:
                    print(f"❌ Ошибка начисления для платежа {invoice_id}")
            
            # Показываем успех
            user = supabase.get_user(user_id)
            new_balance = user.get('balance', 0) if user else 0
            
            new_text = (
                f"✅ Оплата прошла успешно!\n\n"
                f"💰 Зачислено: {amount_rub} руб\n"
                f"💎 В крипте: {amount_usdt} USDT\n"
                f"💳 Новый баланс: {new_balance} руб\n"
                f"🤖 Система: CryptoBot\n"
                f"📝 ID: <code>{invoice_id[:12]}...</code>\n\n"
                f"Спасибо за пополнение! 🎉"
            )
            new_markup = inline.after_payment_menu()
            await _safe_edit_message(callback, new_text, new_markup)
        
        # ========== СТАТУС "ACTIVE" = ОЖИДАЕТ ОПЛАТЫ ==========
        elif status == 'active':
            new_text = (
                f"⏳ Счёт ожидает оплаты\n\n"
                f"💰 Сумма: {amount_rub} руб\n"
                f"💎 Оплатить: {amount_usdt} USDT\n"
                f"📊 Курс: 1 USDT ≈ {rate} RUB\n"
                f"🤖 Система: CryptoBot\n"
                f"📝 ID: <code>{invoice_id[:12]}...</code>\n"
                f"⏰ Проверено: {timestamp}\n\n"
                f"Инструкция:\n"
                f"1. Нажмите 'Оплатить'\n"
                f"2. Переведите {amount_usdt} USDT\n"
                f"3. Проверьте статус через 2-3 минуты"
            )
            new_markup = inline.crypto_check_again_menu(invoice_id)
            await _safe_edit_message(callback, new_text, new_markup)
        
        # ========== СТАТУС "EXPIRED" = ИСТЕК ==========
        elif status == 'expired':
            new_text = (
                f"❌ Счёт истёк\n\n"
                f"💰 Сумма: {amount_rub} руб\n"
                f"📝 ID: <code>{invoice_id[:12]}...</code>\n\n"
                f"Время на оплату истекло.\n"
                f"Создайте новый счёт."
            )
            new_markup = inline.payment_methods()
            await _safe_edit_message(callback, new_text, new_markup)
        
        # ========== ДРУГИЕ СТАТУСЫ ==========
        else:
            new_text = (
                f"ℹ️ Статус счёта: {status}</b>\n\n"
                f"💰 Сумма: {amount_rub} руб\n"
                f"💎 В крипте: {amount_usdt} USDT\n"
                f"📝 ID: <code>{invoice_id[:12]}...</code>\n"
                f"⏰ Проверено: {timestamp}\n\n"
                f"Попробуйте проверить позже."
            )
            new_markup = inline.crypto_check_again_menu(invoice_id)
            await _safe_edit_message(callback, new_text, new_markup)
    
    except Exception as e:
        print(f"❌ Ошибка проверки CryptoBot платежа: {e}")
        
        new_text = (
            "❌ <b>Ошибка проверки</b>\n\n"
            "Пожалуйста, попробуйте позже.\n"
            "Если проблема повторяется, используйте ЮKassa."
        )
        new_markup = inline.payment_methods()
        await _safe_edit_message(callback, new_text, new_markup)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

async def _safe_edit_message(callback: types.CallbackQuery, new_text: str, new_markup):
    """
    Безопасное обновление сообщения с проверкой изменений
    """
    try:
        # Генерируем хеш нового сообщения
        markup_str = str(new_markup.inline_keyboard) if new_markup else ""
        new_hash = get_message_hash(new_text, markup_str)
        
        # Получаем ID сообщения и пользователя для ключа кэша
        message_id = callback.message.message_id
        user_id = callback.from_user.id
        cache_key = f"{user_id}_{message_id}"
        
        # Проверяем, не совпадает ли с предыдущим сообщением
        old_hash = message_cache.get(cache_key)
        
        if old_hash == new_hash:
            # Сообщение не изменилось - просто отвечаем
            await callback.answer("ℹ️ Статус не изменился")
            return
        
        # Обновляем сообщение
        await callback.message.edit_text(
            text=new_text,
            reply_markup=new_markup,
            parse_mode='HTML'
        )
        
        # Сохраняем новый хеш в кэш
        message_cache[cache_key] = new_hash
        
    except Exception as e:
        # Если ошибка "message not modified" - игнорируем
        if "message is not modified" in str(e):
            await callback.answer("ℹ️ Статус не изменился")
        else:
            print(f"⚠️ Ошибка обновления сообщения: {e}")
            # Пробуем отправить новое сообщение
            try:
                await callback.message.answer(
                    text=new_text,
                    reply_markup=new_markup,
                    parse_mode='HTML'
                )
            except:
                await callback.answer("⚠️ Ошибка обновления")

# ========== АВТОМАТИЧЕСКАЯ ПРОВЕРКА ПЛАТЕЖЕЙ ==========

async def auto_check_payments():
    """Автоматическая проверка всех pending платежей"""
    try:
        from supabase_client import SupabaseClient
        from yookassa_client import yookassa_client
        from cryptobot_client import cryptobot_client
        
        supabase = SupabaseClient()
        
        # Находим все pending платежи
        response = supabase.client.table('payments') \
            .select('*') \
            .eq('status', 'pending') \
            .execute()
        
        payments = response.data if response.data else []
        count = len(payments)
        
        if count > 0:
            print(f"🔍 Автопроверка: найдено {count} pending платежей")
        
        for payment in payments:
            payment_method = payment.get('payment_method')
            invoice_id = payment.get('invoice_id')
            user_id = payment.get('user_id')
            amount = payment.get('amount', 0)
            db_id = payment.get('id')
            
            if not invoice_id:
                continue
            
            try:
                # Проверяем в зависимости от платежной системы
                if payment_method == 'yookassa':
                    result = await yookassa_client.check_payment_status(invoice_id)
                    
                    if result['success'] and result['status'] == 'succeeded' and result['paid']:
                        # Начисляем баланс
                        success = supabase.update_balance(user_id, amount)
                        
                        if success:
                            # Обновляем статус
                            supabase.client.table('payments') \
                                .update({
                                    'status': 'completed',
                                    'completed_at': datetime.now().isoformat()
                                }) \
                                .eq('id', db_id) \
                                .execute()
                            
                            print(f"✅ Автоматически обработан платеж ЮKassa {invoice_id} для user {user_id}")
                
                elif payment_method == 'cryptobot':
                    result = cryptobot_client.check_invoice(invoice_id)
                    
                    if result['success'] and result['status'] == 'paid':
                        # Начисляем баланс
                        success = supabase.update_balance(user_id, amount)
                        
                        if success:
                            # Обновляем статус
                            supabase.client.table('payments') \
                                .update({
                                    'status': 'completed',
                                    'completed_at': datetime.now().isoformat()
                                }) \
                                .eq('id', db_id) \
                                .execute()
                            
                            print(f"✅ Автоматически обработан платеж CryptoBot {invoice_id} для user {user_id}")
                            
            except Exception as e:
                print(f"❌ Ошибка проверки платежа {invoice_id}: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Ошибка автоматической проверки: {e}")