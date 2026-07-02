
import os
import requests
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class CryptoBotClient:

    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("CRYPTO_BOT_TOKEN")
        self.base_url = "https://pay.crypt.bot/api"
        
        if not self.token:
            logger.error("❌ Не задан CRYPTO_BOT_TOKEN в .env")
            raise ValueError("Не задан токен CryptoBot")
        
        self.headers = {
            "Crypto-Pay-API-Token": self.token,
            "Content-Type": "application/json"
        }
    
    def get_me(self) -> Dict[str, Any]:

        try:
            response = requests.get(
                f"{self.base_url}/getMe",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get("ok"):
                return {
                    'success': True,
                    'app_id': result['result'].get('app_id'),
                    'name': result['result'].get('name')
                }
            else:
                return {
                    'success': False,
                    'error': result.get("error", {}).get("name", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка CryptoBot getMe: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_invoice(self, user_id: int, amount_rub: float, description: str = "") -> Dict[str, Any]:

        try:

            amount_usdt = round(amount_rub / 90, 6)
            
            data = {
                "asset": "USDT",
                "amount": str(amount_usdt),
                "description": description or f"Пополнение баланса на {amount_rub} руб",
                "hidden_message": f"User ID: {user_id}",
                "paid_btn_name": "viewItem",
                "payload": str(user_id),
                "allow_comments": False,
                "allow_anonymous": False,
                "expires_in": 1800
            }
            
            response = requests.post(
                f"{self.base_url}/createInvoice",
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get("ok"):
                invoice = result["result"]
                
                logger.info(f"✅ Создан счёт CryptoBot: {invoice.get('invoice_id')} для user {user_id}")
                
                return {
                    'success': True,
                    'invoice_id': invoice.get('invoice_id'),
                    'pay_url': invoice.get('pay_url'),
                    'amount_rub': amount_rub,
                    'amount_usdt': amount_usdt,
                    'status': 'active'
                }
            else:
                error = result.get("error", {})
                logger.error(f"❌ Ошибка CryptoBot createInvoice: {error}")
                return {
                    'success': False,
                    'error': error.get("name", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка CryptoBot create_invoice: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_invoice(self, invoice_id: str) -> Dict[str, Any]:

        try:
            response = requests.get(
                f"{self.base_url}/getInvoices?invoice_ids={invoice_id}",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get("ok"):
                invoices = result.get("result", {}).get("items", [])
                if invoices:
                    invoice = invoices[0]
                    

                    status = invoice.get('status')
                    
                    return {
                        'success': True,
                        'status': status,
                        'amount': float(invoice.get('amount', 0)),
                        'asset': invoice.get('asset'),
                        'paid_at': invoice.get('paid_at'),
                        'payload': invoice.get('payload'),
                        'metadata': invoice
                    }
            
            return {
                'success': False,
                'error': 'Invoice not found'
            }
                
        except Exception as e:
            logger.error(f"❌ Ошибка CryptoBot check_invoice: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_exchange_rate(self, asset: str = "USDT") -> Dict[str, Any]:

        try:
            response = requests.get(
                f"{self.base_url}/getExchangeRates",
                headers=self.headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get("ok"):
                rates = result.get("result", [])
                for rate in rates:
                    if rate.get("source") == asset and rate.get("target") == "RUB":
                        return {
                            'success': True,
                            'rate': float(rate.get("rate", 90)),
                            'asset': asset
                        }
            
            return {
                'success': False,
                'error': 'Rate not found',
                'rate': 90.0
            }
                
        except Exception as e:
            logger.error(f"❌ Ошибка CryptoBot get_exchange_rate: {e}")
            return {
                'success': False,
                'error': str(e),
                'rate': 90.0
            }

cryptobot_client = CryptoBotClient()