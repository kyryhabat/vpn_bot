
import hashlib
import math
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime, timedelta, timezone
import secrets
import string
import random

class SupabaseClient:
    def __init__(self):
        self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase подключен успешно")
        

        self._create_tables_if_not_exists()
        

        self.cleanup_expired_vpns()
    
    def _create_tables_if_not_exists(self):

        try:

            try:
                self.client.table('promocodes').select('count', count='exact').limit(1).execute()
                print("✅ Таблица promocodes уже существует")
            except:
                print("⚠️ Таблица promocodes не существует, будет создана при первом промокоде")
                

            try:
                self.client.table('promo_usages').select('count', count='exact').limit(1).execute()
                print("✅ Таблица promo_usages уже существует")
            except:
                print("⚠️ Таблица promo_usages не существует, будет создана при первом использовании")
                
        except Exception as e:
            print(f"⚠️ Ошибка проверки таблиц: {e}")
    
    def calculate_days_remaining(self, expires_datetime):

        if not expires_datetime:
            return 0
            
        now_utc = datetime.now(timezone.utc)
        delta = expires_datetime - now_utc
        
        if delta.total_seconds() <= 0:
            return 0
        
        return math.ceil(delta.total_seconds() / 86400)
    

    
    def get_user(self, user_id: int):
        try:
            result = self.client.table('users').select('*').eq('user_id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"⚠️ Ошибка получения пользователя {user_id}: {e}")
            return None
    
    def create_user(self, user_id: int, username: str, full_name: str):
        try:
            existing_user = self.get_user(user_id)
            
            if existing_user and existing_user.get('referral_code'):
                return existing_user
            
            referral_code = self.generate_referral_code(user_id)
            
            user_data = {
                'user_id': user_id,
                'username': username or 'user',
                'full_name': full_name or 'User',
                'balance': 0,
                'is_admin': False,
                'referral_code': referral_code,
                'referred_by': None,
                'referral_count': 0,
                'referral_earnings': 0,
                'used_promocodes': []
            }
            
            response = self.client.table('users').upsert(user_data, on_conflict='user_id').execute()
            
            if response.data:
                print(f"✅ Пользователь {user_id} создан/обновлен")
                return response.data[0]
            return None
                
        except Exception as e:
            print(f"❌ Ошибка создания пользователя: {e}")
            return None
    
    def generate_referral_code(self, user_id: int):
        code = f"REF{hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()}"
        return code
    
    def update_balance(self, user_id: int, amount: float):
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            new_balance = float(user.get('balance', 0)) + float(amount)
            
            result = self.client.table('users') \
                .update({'balance': new_balance}) \
                .eq('user_id', user_id) \
                .execute()
            
            return True if result.data else False
        except Exception as e:
            print(f"❌ Ошибка обновления баланса для {user_id}: {e}")
            return False
    
    def get_balance(self, user_id: int):
        user = self.get_user(user_id)
        return float(user.get('balance', 0)) if user else 0
    

    
    def generate_promo_code(self, length: int = 8):

        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(length))
        

        prefixes = ["PROMO", "BONUS", "GIFT", "VIP", "WELCOME"]
        prefix = random.choice(prefixes)
        
        return f"{prefix}{code}"
    
    def create_promocode(self, promo_type: str, value: float, created_by: int, 
                         max_uses: int = 100, expiry_days: int = 30, 
                         custom_code: str = None):

        try:

            if promo_type != 'balance':
                print(f"❌ Неподдерживаемый тип промокода: {promo_type}")
                return None
            

            if custom_code:
                promo_code = custom_code.upper()
            else:
                promo_code = self.generate_promo_code()

                while self.get_promocode(promo_code):
                    promo_code = self.generate_promo_code()
            

            expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)
            
            promo_data = {
                'code': promo_code,
                'type': promo_type,
                'value': float(value),
                'max_uses': max_uses,
                'used_count': 0,
                'expires_at': expires_at.isoformat(),
                'created_by': created_by,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'is_active': True
            }
            
            response = self.client.table('promocodes').insert(promo_data).execute()
            
            if response.data:
                print(f"✅ Создан промокод {promo_code} ({promo_type}={value})")
                return response.data[0]
            return None
            
        except Exception as e:
            print(f"❌ Ошибка создания промокода: {e}")
            return None
    
    def get_promocode(self, code: str):

        try:
            response = self.client.table('promocodes').select('*').eq('code', code.upper()).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Ошибка получения промокода: {e}")
            return None
    
    def get_all_promocodes(self):

        try:
            response = self.client.table('promocodes').select('*').order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Ошибка получения промокодов: {e}")
            return []
    
    def has_user_used_promocode(self, user_id: int, promo_code: str):

        try:

            response = self.client.table('promo_usages') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('promo_code', promo_code.upper()) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return True
            

            user = self.get_user(user_id)
            if user:
                used_promocodes = user.get('used_promocodes', [])
                return promo_code.upper() in used_promocodes
            
            return False
        except Exception as e:
            print(f"❌ Ошибка проверки использования промокода: {e}")
            return False
    
    def apply_promocode_to_balance(self, user_id: int, promo_code: str, amount: float):

        try:

            success = self.update_balance(user_id, amount)
            if not success:
                return False
            

            promo = self.get_promocode(promo_code)
            if promo:
                new_used_count = promo.get('used_count', 0) + 1
                self.client.table('promocodes') \
                    .update({'used_count': new_used_count}) \
                    .eq('code', promo_code.upper()) \
                    .execute()
            

            usage_data = {
                'user_id': user_id,
                'promo_code': promo_code.upper(),
                'value_given': amount,
                'used_at': datetime.now(timezone.utc).isoformat()
            }
            self.client.table('promo_usages').insert(usage_data).execute()
            

            user = self.get_user(user_id)
            if user:
                used_promocodes = user.get('used_promocodes', [])
                if promo_code.upper() not in used_promocodes:
                    used_promocodes.append(promo_code.upper())
                    self.client.table('users') \
                        .update({'used_promocodes': used_promocodes}) \
                        .eq('user_id', user_id) \
                        .execute()
            
            return True
        except Exception as e:
            print(f"❌ Ошибка применения промокода: {e}")
            return False
    
    def deactivate_promocode(self, code: str):

        try:
            response = self.client.table('promocodes') \
                .update({'is_active': False}) \
                .eq('code', code.upper()) \
                .execute()
            
            return True if response.data else False
        except Exception as e:
            print(f"❌ Ошибка деактивации промокода: {e}")
            return False
    
    def get_promo_usage_history(self, promo_code: str = None, user_id: int = None):

        try:
            query = self.client.table('promo_usages').select('*')
            
            if promo_code:
                query = query.eq('promo_code', promo_code.upper())
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            query = query.order('used_at', desc=True)
            response = query.execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"❌ Ошибка получения истории промокодов: {e}")
            return []
    

    
    def get_admin_by_id(self, user_id: int):

        try:
            response = self.client.table('users') \
                .select('*') \
                .eq('user_id', user_id) \
                .execute()
            
            if response.data:
                user = response.data[0]
                if user.get('is_admin'):
                    return user
            return None
        except Exception as e:
            print(f"⚠️ Ошибка проверки администратора {user_id}: {e}")
            return None
    
    def get_all_users(self):

        try:
            response = self.client.table('users').select('*').order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка получения всех пользователей: {e}")
            return []
    
    def get_all_orders(self):

        try:
            response = self.client.table('vpn_orders').select('*').order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка получения всех заказов: {e}")
            return []
    
    def get_all_payments(self):

        try:
            response = self.client.table('payments').select('*').order('created_at', desc=True).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка получения всех платежей: {e}")
            return []
    
    def get_all_admins(self):

        try:
            response = self.client.table('users') \
                .select('*') \
                .eq('is_admin', True) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка получения всех администраторов: {e}")
            return []
    
    def set_user_admin(self, user_id: int, is_admin: bool):

        try:
            response = self.client.table('users') \
                .update({'is_admin': is_admin}) \
                .eq('user_id', user_id) \
                .execute()
            
            if response.data:
                print(f"✅ Права администратора {'установлены' if is_admin else 'сняты'} для пользователя {user_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка установки прав администратора: {e}")
            return False
    
    def get_user_by_username(self, username: str):

        try:
            response = self.client.table('users') \
                .select('*') \
                .ilike('username', f'%{username}%') \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка поиска пользователя по username: {e}")
            return []
    
    def get_user_by_username_exact(self, username: str):

        try:
            response = self.client.table('users') \
                .select('*') \
                .eq('username', username) \
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Ошибка поиска пользователя по точному username: {e}")
            return []
    
    def create_vpn_order(self, user_id: int, tariff_id: str, uuid: str, link: str):
        try:
            from config import TARIFFS
            tariff = TARIFFS.get(tariff_id)
            if not tariff:
                return None
            
            expires_at = datetime.now() + timedelta(days=tariff['days'])
            
            order_data = {
                'user_id': user_id,
                'tariff_id': tariff_id,
                'uuid': uuid,
                'link': link,
                'days': tariff['days'],
                'traffic_gb': tariff['traffic_gb'],
                'price': tariff['price'],
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
            
            response = self.client.table('vpn_orders').insert(order_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"⚠️ Ошибка создания заказа VPN: {e}")
            return None
    
    def get_user_orders(self, user_id: int):
        try:
            response = self.client.table('vpn_orders').select('*').eq('user_id', user_id).execute()
            return response.data if response.data else []
        except:
            return []
    
    def _parse_datetime(self, dt_str: str) -> datetime:

        if not dt_str:
            return datetime.now()
        
        dt_str = dt_str.replace('Z', '')
        
        if '+' in dt_str or dt_str.endswith('+00:00'):
            return datetime.fromisoformat(dt_str)
        else:
            naive_dt = datetime.fromisoformat(dt_str)
            return naive_dt.replace(tzinfo=timezone.utc)
    
    def get_active_vpns(self, user_id: int):

        try:
            response = self.client.table('vpn_orders') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('status', 'active') \
                .execute()
            
            active_vpns = []
            
            for vpn in (response.data if response.data else []):
                expires_at = vpn.get('expires_at')
                if expires_at:
                    expires_datetime = self._parse_datetime(expires_at)
                    now_utc = datetime.now(timezone.utc)
                    
                    if expires_datetime < now_utc:
                        self.client.table('vpn_orders') \
                            .update({'status': 'expired'}) \
                            .eq('id', vpn['id']) \
                            .execute()
                        continue
                
                if expires_at:
                    expires_datetime = self._parse_datetime(expires_at)
                    vpn['remaining_days'] = self.calculate_days_remaining(expires_datetime)
                else:
                    vpn['remaining_days'] = 0
                
                traffic_gb = vpn.get('traffic_gb', 0)
                used_traffic = vpn.get('used_traffic_gb', 0)
                vpn['remaining_traffic_gb'] = traffic_gb - used_traffic if traffic_gb > 0 else 9999
                
                active_vpns.append(vpn)
            
            return active_vpns
        except Exception as e:
            print(f"⚠️ Ошибка получения активных VPN: {e}")
            return []
    
    def get_active_vpn_by_id(self, vpn_id: int, user_id: int):

        try:
            self.cleanup_expired_vpns()
            
            response = self.client.table('vpn_orders') \
                .select('*') \
                .eq('id', vpn_id) \
                .eq('user_id', user_id) \
                .eq('status', 'active') \
                .execute()
            
            vpn = response.data[0] if response.data else None
            
            if vpn:
                expires_at = vpn.get('expires_at')
                if expires_at:
                    expires_datetime = self._parse_datetime(expires_at)
                    now_utc = datetime.now(timezone.utc)
                    
                    if expires_datetime < now_utc:
                        self.client.table('vpn_orders') \
                            .update({'status': 'expired'}) \
                            .eq('id', vpn_id) \
                            .execute()
                        return None
                
                vpn['remaining_days'] = self.calculate_days_remaining(expires_datetime)
            
            return vpn
        except Exception as e:
            print(f"❌ Ошибка получения VPN {vpn_id}: {e}")
            return None
    
    def cleanup_expired_vpns(self):

        try:
            print("🧹 Проверка истекших VPN...")
            
            response = self.client.table('vpn_orders') \
                .select('*') \
                .eq('status', 'active') \
                .execute()
            
            if not response.data:
                return 0
            
            expired_count = 0
            
            for vpn in response.data:
                expires_at = vpn.get('expires_at')
                if expires_at:
                    expires_datetime = self._parse_datetime(expires_at)
                    now_utc = datetime.now(timezone.utc)
                    
                    if expires_datetime < now_utc:
                        self.client.table('vpn_orders') \
                            .update({'status': 'expired'}) \
                            .eq('id', vpn['id']) \
                            .execute()
                        
                        expired_count += 1
            
            if expired_count > 0:
                print(f"✅ Помечено как истекших: {expired_count} VPN")
            
            return expired_count
        except Exception as e:
            print(f"❌ Ошибка очистки VPN: {e}")
            return 0
    
    #  РЕФЕРАЛЬКА
    
    def get_user_by_referral_code(self, code: str):
        try:
            response = self.client.table('users').select('*').eq('referral_code', code).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Ошибка поиска по коду: {e}")
            return None
    
    def apply_referral(self, new_user_id: int, referrer_id: int):
        try:
            from config import REFERRAL_SETTINGS
            
            if new_user_id == referrer_id:
                return False
            
            existing_ref = self.client.table('referrals').select('*').eq('new_user_id', new_user_id).execute()
            if existing_ref.data:
                return False
            
            bonus = REFERRAL_SETTINGS.get("bonus_for_referrer", 50)
            
            success = self.update_balance(referrer_id, bonus)
            if not success:
                return False
            
            self.client.table('users').update({'referred_by': referrer_id}).eq('user_id', new_user_id).execute()
            
            referral_data = {
                'referrer_id': referrer_id,
                'new_user_id': new_user_id,
                'bonus_amount': bonus,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            self.client.table('referrals').insert(referral_data).execute()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка применения реферала: {e}")
            return False
    
    def get_referral_stats(self, user_id: int):

        try:

            referrals_response = self.client.table('referrals') \
                .select('count', count='exact') \
                .eq('referrer_id', user_id) \
                .execute()
            
            total_referrals = referrals_response.count if hasattr(referrals_response, 'count') else 0
            

            bonuses_response = self.client.table('referrals') \
                .select('bonus_amount') \
                .eq('referrer_id', user_id) \
                .execute()
            
            total_bonus = sum([float(b['bonus_amount']) for b in bonuses_response.data]) if bonuses_response.data else 0
            
            return {
                'total_referrals': total_referrals,
                'total_bonus': total_bonus
            }
        except Exception as e:
            print(f"❌ Ошибка получения статистики рефералов: {e}")
            return {'total_referrals': 0, 'total_bonus': 0}


db = SupabaseClient()