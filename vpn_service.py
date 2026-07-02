from xui_client import XUIClient
from config import INBOUND_ID_FREE, INBOUND_ID
from datetime import datetime, timedelta

class VPNService:
    def __init__(self):
        self.xui = XUIClient()
    
    def create_free_vpn(self, user_id: int):

        try:
            print(f"🔄 Создаю бесплатный VPN для пользователя {user_id}")
            
            result = self.xui.create_user(
                days=3,
                traffic_gb=1,
                is_free=True
            )
            
            return {
                "success": True,
                "uuid": result["uuid"],
                "link": result["link"],
                "email": result["email"],
                "expire_date": datetime.now() + timedelta(days=3),
                "traffic_limit_gb": 1,
                "inbound_id": INBOUND_ID_FREE
            }
            
        except Exception as e:
            print(f"❌ Ошибка создания бесплатного VPN: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_paid_vpn(self, user_id: int, tariff: dict):

        try:
            print(f"🔄 Создаю платный VPN ({tariff['name']}) для {user_id}")
            
            result = self.xui.create_user(
                days=tariff["days"],
                traffic_gb=tariff["traffic_gb"],
                is_free=False
            )
            
            return {
                "success": True,
                "uuid": result["uuid"],
                "link": result["link"],
                "email": result["email"],
                "expire_date": datetime.now() + timedelta(days=tariff["days"]),
                "traffic_limit_gb": tariff["traffic_gb"],
                "inbound_id": INBOUND_ID
            }
            
        except Exception as e:
            print(f"❌ Ошибка создания платного VPN: {e}")
            return {
                "success": False,
                "error": str(e)
            }