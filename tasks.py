
import asyncio
from datetime import datetime
from supabase_client import SupabaseClient
from config import BOT_TOKEN
from aiogram import Bot

async def daily_vpn_cleanup():

    try:
        supabase = SupabaseClient()
        
        response = supabase.client.table('vpn_orders') \
            .select('*') \
            .eq('status', 'active') \
            .execute()
        
        expired_count = 0
        
        for vpn in response.data:
            expiry_date_str = vpn.get('expires_at')
            if not expiry_date_str:
                continue
            
            try:
                if 'Z' in expiry_date_str:
                    expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                else:
                    expiry_date = datetime.fromisoformat(expiry_date_str)
                
                if expiry_date < datetime.now():
                    supabase.client.table('vpn_orders') \
                        .update({'status': 'expired'}) \
                        .eq('id', vpn['id']) \
                        .execute()
                    expired_count += 1
            except:
                pass
        
        if expired_count > 0:
            print(f"🧹 Очищено VPN: {expired_count}")
            
        return expired_count
    except Exception as e:
        print(f"❌ Ошибка очистки: {e}")
        return 0

async def check_expired_notifications(bot: Bot = None):

    try:
        from utils import check_and_send_expiry_notifications
        
        if bot is None:
            bot = Bot(token=BOT_TOKEN)
            need_close = True
        else:
            need_close = False
        
        await check_and_send_expiry_notifications(bot)
        
        if need_close:
            await bot.session.close()
            
    except Exception as e:
        print(f"❌ Ошибка уведомлений: {e}")