
import os
import asyncio
from typing import Dict, Any
import uuid
from datetime import datetime

try:
    from yookassa import Payment, Configuration
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False
    print("⚠️ Установите библиотеку: pip install yookassa")

class YooKassaClient:

    
    def __init__(self):
        if not YOOKASSA_AVAILABLE:
            print("❌ Библиотека yookassa не установлена")
            return
        
        self.shop_id = os.getenv("YOOKASSA_SHOP_ID")
        self.secret_key = os.getenv("YOOKASSA_SECRET_KEY")
        
        if not self.shop_id or not self.secret_key:
            print("❌ Не заданы YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY в .env")
            return
        
        Configuration.account_id = self.shop_id
        Configuration.secret_key = self.secret_key
        print("✅ ЮKassa клиент готов")
    
    async def create_payment(self, user_id: int, amount: float, description: str) -> Dict[str, Any]:

        try:

            invoice_id = str(uuid.uuid4())
            

            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/your_bot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "created_at": datetime.now().isoformat(),
                    "invoice_id": invoice_id
                }
            }
            
            # Создаем платеж в ЮKassa
            payment = await asyncio.to_thread(
                Payment.create,
                payment_data,
                invoice_id
            )
            
            print(f"✅ Создан платеж {payment.id} для user {user_id}, сумма: {amount} руб")
            

            from supabase_client import SupabaseClient
            supabase = SupabaseClient()
            

            payment_db_data = {
                'user_id': user_id,
                'amount': float(amount),
                'currency': 'RUB',
                'invoice_id': payment.id,
                'payment_method': 'yookassa',
                'status': payment.status,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'metadata': {
                    'yookassa_payment_id': payment.id,
                    'user_id': user_id,
                    'invoice_id_original': invoice_id,  # Оригинальный invoice_id
                    'confirmation_url': payment.confirmation.confirmation_url,
                    'created_at': datetime.now().isoformat()
                }
            }
            

            result = supabase.client.table('payments').insert(payment_db_data).execute()
            
            print(f"✅ Платеж сохранен в БД, ID записи: {result.data[0]['id'] if result.data else 'N/A'}")
            
            return {
                'success': True,
                'payment_id': payment.id,  # ID платежа ЮKassa
                'confirmation_url': payment.confirmation.confirmation_url,
                'status': payment.status,
                'invoice_id': payment.id,  # Для совместимости с вашей БД
                'amount': amount,
                'db_id': result.data[0]['id'] if result.data else None
            }
            
        except Exception as e:
            print(f"❌ Ошибка создания платежа: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:

        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
            
            return {
                'success': True,
                'status': payment.status,
                'paid': payment.paid,
                'amount': float(payment.amount.value),
                'metadata': payment.metadata,
                'payment_id': payment.id
            }
            
        except Exception as e:
            print(f"❌ Ошибка проверки платежа {payment_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def find_payment_in_db(self, payment_id: str):

        try:
            from supabase_client import SupabaseClient
            supabase = SupabaseClient()
            

            response = supabase.client.table('payments') \
                .select('*') \
                .eq('invoice_id', payment_id) \
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Ошибка поиска платежа в БД: {e}")
            return None


yookassa_client = YooKassaClient()