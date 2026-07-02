from aiogram import Router, types, F
from keyboards import inline 

router = Router()

@router.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📞 Поддержка\n\n"
        "По всем вопросам:\n"
        "👤 @mr_flive\n\n"
        "Время ответа: 5-30 минут\n"
        "Работаем 24/7",
        reply_markup=inline.contact_support_menu()
    )

@router.callback_query(F.data == "help")
async def help_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "❓ Помощь\n\n"
        "Выберите раздел:",
        reply_markup=inline.help_menu()
    )

@router.callback_query(F.data == "faq")
async def faq_handler(callback: types.CallbackQuery):
    faq_text = """📖 FAQ - Частые вопросы

🔸 Подключение:
1. Купить VPN в боте
2. Скопировать ссылку из "Мои VPN"
3. Вставить в V2RayTun/Hiddify
4. Включить

🔸 Приложения:
• Android: V2RayTun, Hiddify
• iOS: Shadowrocket, Streisand
• ПК: Clash, V2rayN

🔸 Проблемы:
1. Перезапустить приложение
2. Проверить дату/время
3. Сменить сеть Wi-Fi/4G
4. Написать в поддержку

🔸 Оплата:
• Пополнение: Юкасса, Крипта
• Продление: Купить новый тариф
• Уведомление: За 3 и 1 день

🔸 Лимиты:
• Устройств: 3-5 одновременных
• Трафик: По тарифу
• Срок: По тарифу


Есть вопросы? Напишите в поддержку 👇"""

    await callback.message.edit_text(
        faq_text,
        reply_markup=inline.help_menu()
    )