# handlers/errors.py
from aiogram import Router, types
from aiogram.exceptions import TelegramBadRequest

router = Router()

@router.callback_query(lambda c: c.data == "no_vpns")
async def no_vpns_handler(callback: types.CallbackQuery):
    await callback.answer("У вас нет VPN")

@router.callback_query(lambda c: c.data == "main_menu")
async def main_menu_handler(callback: types.CallbackQuery):
    """Обработчик для кнопки 'Главное меню'"""
    from keyboards import inline
    try:
        await callback.message.edit_text(
            "🏠 Главное меню",
            reply_markup=inline.main_menu(
                user_id=callback.from_user.id, 
                admin=False  # Можно добавить проверку is_admin
            )
        )
    except TelegramBadRequest:
        await callback.answer("Меню обновлено")

@router.callback_query()
async def unknown_callback_handler(callback: types.CallbackQuery):
    """Обработчик неизвестных callback"""
    print(f"⚠️ Неизвестный callback: {callback.data}")
    await callback.answer("⚠️ Эта кнопка временно не работает")