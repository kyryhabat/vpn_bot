
import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import routers
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from utils import check_and_send_expiry_notifications
from tasks import daily_vpn_cleanup

scheduler = AsyncIOScheduler()

async def scheduled_notifications():

    try:
        bot = Bot(token=BOT_TOKEN)
        await check_and_send_expiry_notifications(bot)
        await bot.session.close()
    except Exception as e:
        print(f"❌ Ошибка уведомлений: {e}")

async def cleanup_expired_vpns_job():

    try:
        await daily_vpn_cleanup()
    except Exception as e:
        print(f"❌ Ошибка очистки: {e}")

async def test_notifications_job():

    try:
        print(f"🔄 Проверка {datetime.now().strftime('%H:%M')}")
        bot = Bot(token=BOT_TOKEN)
        await check_and_send_expiry_notifications(bot)
        await bot.session.close()
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")

async def on_startup():

    try:
        await daily_vpn_cleanup()
        

        scheduler.add_job(
            test_notifications_job,
            CronTrigger(minute='*/5'),
            id='test_notifications',
            replace_existing=True,
            timezone='Europe/Moscow'
        )
        

        scheduler.add_job(
            scheduled_notifications,
            CronTrigger(hour=10, minute=0),
            id='vpn_expiry_notifications_morning',
            replace_existing=True,
            timezone='Europe/Moscow'
        )
        
        scheduler.add_job(
            scheduled_notifications,
            CronTrigger(hour=18, minute=0),
            id='vpn_expiry_notifications_evening',
            replace_existing=True,
            timezone='Europe/Moscow'
        )
        

        scheduler.add_job(
            cleanup_expired_vpns_job,
            CronTrigger(hour=3, minute=0),
            id='vpn_cleanup',
            replace_existing=True,
            timezone='Europe/Moscow'
        )
        
        scheduler.start()
        

        await test_notifications_job()
        
    except Exception as e:
        print(f"❌ Ошибка планировщика: {e}")

async def on_shutdown():

    if scheduler.running:
        scheduler.shutdown(wait=False)

async def main():

    bot = None
    
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        
        for router in routers:
            dp.include_router(router)
        
        await on_startup()
        
        print("🤖 VPN Bot запущен")
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        await on_shutdown()
        if bot:
            await bot.session.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())