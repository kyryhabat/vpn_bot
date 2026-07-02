
import requests
import uuid
import time
import json
import random
from config import XUI_URL, XUI_USER, XUI_PASS, INBOUND_ID, INBOUND_ID_FREE, DOMAIN
import warnings
import urllib3
import ssl
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')
urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

class XUIClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.base_url = XUI_URL.rstrip('/')
        self.is_logged_in = False
        
        # Очищаем домен от порта
        if DOMAIN and ':' in DOMAIN:
            self.domain = DOMAIN.split(':')[0]
        else:
            self.domain = DOMAIN
        
        # Порты
        self.PORTS = {
            int(INBOUND_ID): 25895,
            int(INBOUND_ID_FREE): 31537
        }
        

        self.REALITY_CONFIG = {
            int(INBOUND_ID): {  # Платные
                "public_key": "Ed0YJJ2JDmZxAXcTJ90lH6l2dvhu3pX38aq1RLYpKA4",
                "short_ids": ["11c2af", "1a6d", "6fd6db39fd9878b5", "fc69325c9542", 
                             "f1237936", "6f38d01765", "23f0c408237661", "06"],
                "sni": "google.com"
            },
            int(INBOUND_ID_FREE): {  # Бесплатные
                "public_key": "HKdMMp656G893NXY_5XwXK5c_IMATnSP9ARxsEuabVY",
                "short_ids": ["d679c126", "cc7f29fe46bc017c", "2c96", "17c6272c8256",
                             "ae", "5eeeb914ab", "5177e9", "ebed3a78b7496b"],
                "sni": "google.com"
            }
        }
        

        self._login_with_retry()
    
    def _login_with_retry(self, retries=3):

        for attempt in range(retries):
            try:
                if self._login():
                    self.is_logged_in = True
                    logger.info(f"✅ Успешная авторизация в X-UI (попытка {attempt + 1})")
                    return True
                else:
                    logger.warning(f"❌ Неудачная авторизация (попытка {attempt + 1})")
            except Exception as e:
                logger.error(f"❌ Ошибка авторизации X-UI (попытка {attempt + 1}): {str(e)}")
            
            if attempt < retries - 1:
                time.sleep(2)
        
        logger.error("❌ Не удалось авторизоваться в X-UI после всех попыток")
        self.is_logged_in = False
    
    def _login(self):

        try:
            login_url = f"{self.base_url}/login"
            logger.info(f"🔄 Пытаюсь подключиться к X-UI: {login_url}")
            
            response = self.session.post(
                login_url,
                json={"username": XUI_USER, "password": XUI_PASS},
                timeout=15,
                verify=False,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"📡 Ответ X-UI: статус={response.status_code}")
            logger.info(f"📡 Ответ X-UI: содержимое={response.text[:200]}")
            

            if response.status_code != 200:
                logger.error(f"❌ X-UI вернул статус {response.status_code}")
                return False
            

            if not response.text or response.text.strip() == "":
                logger.error("❌ X-UI вернул пустой ответ")
                return False
            

            try:
                data = response.json()
                logger.info(f"📋 JSON ответ: {data}")
                
                # Проверяем разные возможные ответы от X-UI
                if isinstance(data, dict):
                    if data.get("success") is True:
                        return True
                    elif data.get("success") is False:
                        logger.error(f"❌ X-UI: {data.get('msg', 'Неизвестная ошибка')}")
                        return False
                elif isinstance(data, bool):
                    return data
                else:
                    logger.warning(f"⚠️ Необычный ответ от X-UI: {type(data)}")
                    return True
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
                logger.error(f"📄 Полученный текст: {response.text[:500]}")
                

                if "success" in response.text.lower() or "true" in response.text.lower():
                    logger.info("⚠️ Получен не-JSON ответ, но содержит success/true")
                    return True
                
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Таймаут при подключении к X-UI")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ Ошибка подключения к X-UI")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка авторизации: {str(e)}")
            return False
    
    def create_user(self, days: int, traffic_gb: int = 0, is_free: bool = False):

        if not self.is_logged_in:
            logger.warning("⚠️ Не авторизованы, пытаюсь перелогиниться...")
            if not self._login_with_retry():
                return {
                    "success": False,
                    "error": "Ошибка авторизации в X-UI"
                }
        
        inbound_id = int(INBOUND_ID_FREE) if is_free else int(INBOUND_ID)
        port = self.PORTS.get(inbound_id, 443)
        
        try:
            uid = str(uuid.uuid4())
            expire_time = int(time.time() * 1000) + (days * 86400000)
            total_bytes = traffic_gb * (1024 ** 3) if traffic_gb > 0 else 0
            
            client = {
                "id": uid,
                "email": f"user_{uid[:8]}",
                "enable": True,
                "expiryTime": expire_time,
                "limitIp": 0,
                "totalGB": total_bytes
            }
            
            payload = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [client]})
            }
            
            logger.info(f"🔄 Создаю пользователя в inbound {inbound_id}, порт {port}")
            
            response = self.session.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json=payload,
                timeout=30,
                verify=False,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json"
                }
            )
            
            logger.info(f"📡 Ответ создания пользователя: статус={response.status_code}")
            
            if not response.text:
                return {
                    "success": False,
                    "error": "X-UI вернул пустой ответ"
                }
            
            try:
                result = response.json()
                logger.info(f"📋 JSON результат: {result}")
            except json.JSONDecodeError:
                logger.error(f"❌ Ошибка парсинга JSON: {response.text[:500]}")
                # Пробуем парсить как текст
                if "success" in response.text.lower():
                    result = {"success": True}
                else:
                    return {
                        "success": False,
                        "error": f"Некорректный ответ от X-UI: {response.text[:100]}"
                    }
            
            if not result.get("success"):
                error_msg = result.get("msg", "Неизвестная ошибка")
                logger.error(f"❌ X-UI ошибка: {error_msg}")
                raise RuntimeError(f"X-UI: {error_msg}")
            
            link = self._make_vless_link(uid, inbound_id, port)
            
            logger.info(f"✅ Пользователь создан: {uid}")
            
            return {
                "success": True,
                "uuid": uid,
                "link": link,
                "email": client["email"],
                "port": port,
                "inbound_id": inbound_id
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _make_vless_link(self, uid: str, inbound_id: int, port: int):

        try:
            config = self.REALITY_CONFIG.get(inbound_id, self.REALITY_CONFIG[int(INBOUND_ID)])
            short_id = config["short_ids"][0]
            
            link = (
                f"vless://{uid}@{self.domain}:{port}"
                f"?type=tcp&encryption=none&security=reality"
                f"&pbk={config['public_key']}"
                f"&fp=chrome"
                f"&sni={config['sni']}"
                f"&sid={short_id}"
                f"&spx=%2F"
                f"#✈️Для соцсетей"
            )
            
            return link
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания ссылки: {str(e)}")
            return f"vless://{uid}@{self.domain}:{port}?security=reality&sni=google.com"


xui = XUIClient()