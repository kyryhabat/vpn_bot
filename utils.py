
from supabase_client import SupabaseClient
from datetime import datetime, timezone
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def is_admin(user_id: int):

    try:
        from config import ADMIN_IDS
        if user_id in ADMIN_IDS:
            return True
        
        supabase = SupabaseClient()
        admin = supabase.get_admin_by_id(user_id)
        return admin is not None
    except:
        from config import ADMIN_IDS
        return user_id in ADMIN_IDS

def get_all_admins():

    try:
        from config import ADMIN_IDS
        supabase = SupabaseClient()
        response = supabase.client.table('users') \
            .select('user_id') \
            .eq('is_admin', True) \
            .execute()
        
        db_admin_ids = [user['user_id'] for user in response.data]
        return list(set(ADMIN_IDS + db_admin_ids))
    except:
        from config import ADMIN_IDS
        return ADMIN_IDS



def _get_expiry_keyboard(vpn_id: int):

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 Мои VPN", callback_data="my_vpn_0")]
    ])

async def send_vpn_expiry_notification(bot, user_id: int, vpns: list):

    try:
        for vpn in vpns:
            days_left = vpn.get('days_remaining', 0)
            vpn_id = vpn.get('vpn_id')
            tariff_name = vpn.get('tariff_name', 'VPN')
            
            if days_left == 2:
                message_text = (
                    "⚠️ *Внимание!*\n\n"
                    f"Ваш VPN тариф *{tariff_name}* истекает через *2 дня*.\n"
                    f"Подключение VPN #{vpn_id} скоро закончится.\n\n"
                )
            elif days_left == 1:
                message_text = (
                    "🚨 *СРОЧНОЕ УВЕДОМЛЕНИЕ!*\n\n"
                    f"Ваш VPN тариф *{tariff_name}* истекает *ЗАВТРА*!\n"
                    f"Подключение VPN #{vpn_id} закончится завтра.\n\n"
                )
            else:
                continue
            
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode="Markdown",
                    reply_markup=_get_expiry_keyboard(vpn_id)
                )
                print(f"📨 Уведомление отправлено пользователю {user_id} (VPN #{vpn_id}, {days_left} дней)")
            except Exception as e:
                if "bot was blocked" not in str(e) and "user is deactivated" not in str(e):
                    print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                
    except Exception as e:
        print(f"❌ Ошибка send_vpn_expiry_notification: {e}")

def _calculate_days_remaining(expiry_date_str: str) -> int:

    try:
        if not expiry_date_str:
            return 999
        
        if 'Z' in expiry_date_str:
            expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
        else:
            expiry_date = datetime.fromisoformat(expiry_date_str)
        
        now_utc = datetime.now(timezone.utc)
        
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=timezone.utc)
        
        delta = expiry_date - now_utc
        
        if delta.total_seconds() <= 0:
            return 0
        
        days = delta.days
        
        if days == 0 and delta.total_seconds() > 0:
            return 1
        
        return days
        
    except:
        return 999

async def check_and_send_expiry_notifications(bot):

    try:
        print(f"🔄 Проверка уведомлений VPN: {datetime.now().strftime('%H:%M:%S')}")
        
        supabase = SupabaseClient()
        
        response = supabase.client.table('vpn_orders') \
            .select('*') \
            .eq('status', 'active') \
            .execute()
        
        active_vpns = response.data
        
        if not active_vpns:
            return
        
        users_vpns = {}
        
        for vpn in active_vpns:
            user_id = vpn.get('user_id')
            expiry_date_str = vpn.get('expires_at')
            last_notification = vpn.get('last_notification')
            
            if not user_id or not expiry_date_str:
                continue
            
            days_left = _calculate_days_remaining(expiry_date_str)
            
            if days_left <= 0:
                supabase.client.table('vpn_orders') \
                    .update({'status': 'expired'}) \
                    .eq('id', vpn.get('id')) \
                    .execute()
                continue
            
            if days_left in [1, 2]:
                notification_key = f'expire_in_{days_left}_days'
                
                if last_notification == notification_key:
                    continue
                
                if user_id not in users_vpns:
                    users_vpns[user_id] = []
                
                users_vpns[user_id].append({
                    'vpn_id': vpn.get('id'),
                    'days_remaining': days_left,
                    'tariff_name': vpn.get('tariff_id', 'VPN'),
                    'notification_key': notification_key,
                })
        
        if not users_vpns:
            return
        
        total_notifications = 0
        
        for user_id, vpns_list in users_vpns.items():
            try:
                await send_vpn_expiry_notification(bot, user_id, vpns_list)
                total_notifications += len(vpns_list)
                
                for vpn in vpns_list:
                    supabase.client.table('vpn_orders') \
                        .update({'last_notification': vpn['notification_key']}) \
                        .eq('id', vpn['vpn_id']) \
                        .execute()
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Ошибка пользователю {user_id}: {e}")
        
        if total_notifications > 0:
            print(f"✅ Отправлено уведомлений: {total_notifications}")
        
    except Exception as e:
        print(f"❌ Ошибка check_and_send_expiry_notifications: {e}")