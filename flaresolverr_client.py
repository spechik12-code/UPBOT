#!/usr/bin/env python3
"""
Улучшенный клиент FlareSolverr с поддержкой прокси
"""
import requests
import time
import logging
import random
from config import FLARESOLVERR_URL, PROXY_LIST, USE_DIRECT_PROXY

logger = logging.getLogger(__name__)

class AdvancedFlareSolverrClient:
    """Продвинутый клиент FlareSolverr с ротацией прокси"""
    
    def __init__(self, base_url=FLARESOLVERR_URL):
        self.base_url = base_url
        self.session_id = None
        self.proxy_index = 0
        self.session_created = None
        
    def get_next_proxy(self):
        """Получить следующий прокси из списка"""
        if not PROXY_LIST:
            return None
        
        self.proxy_index = (self.proxy_index + 1) % len(PROXY_LIST)
        return PROXY_LIST[self.proxy_index]
    
    def create_session_with_proxy(self):
        """Создать сессию FlareSolverr с использованием прокси"""
        try:
            session_name = f"upbot_{int(time.time())}_{random.randint(1000, 9999)}"
            
            payload = {
                "cmd": "sessions.create",
                "session": session_name
            }
            
            # Если есть прокси, используем первый
            proxy_for_flare = None
            if PROXY_LIST:
                proxy_for_flare = self.get_next_proxy()
                payload["proxy"] = {"url": proxy_for_flare}
                logger.info(f"Создаем сессию FlareSolverr с прокси: {proxy_for_flare[:50]}...")
            else:
                logger.info("Создаем сессию FlareSolverr без прокси")
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    self.session_id = data['session']
                    self.session_created = time.time()
                    logger.info(f"✅ Создана сессия FlareSolverr: {self.session_id}")
                    if proxy_for_flare:
                        logger.info(f"   Используется прокси: {proxy_for_flare[:40]}...")
                    return self.session_id
                else:
                    logger.error(f"Ошибка создания сессии: {data.get('message')}")
            else:
                logger.error(f"HTTP ошибка: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка создания сессии FlareSolverr: {e}")
        
        return None
    
    def solve_with_proxy_rotation(self, url, max_timeout=90000):
        """Решить капчу с ротацией прокси если нужно"""
        if not self.session_id:
            self.create_session_with_proxy()
        
        max_attempts = len(PROXY_LIST) if PROXY_LIST else 1
        if max_attempts > 3:
            max_attempts = 3  # Максимум 3 попытки
        
        for attempt in range(max_attempts):
            try:
                # Выбираем прокси для этой попытки
                current_proxy = None
                if PROXY_LIST:
                    current_proxy = self.get_next_proxy()
                    logger.info(f"Попытка {attempt+1}/{max_attempts} с прокси: {current_proxy[:40]}...")
                
                payload = {
                    "cmd": "request.get",
                    "url": url,
                    "maxTimeout": max_timeout,
                    "session": self.session_id if self.session_id else None
                }
                
                if current_proxy:
                    payload["proxy"] = {"url": current_proxy}
                
                response = requests.post(
                    self.base_url,
                    json=payload,
                    timeout=120  # Большой таймаут для FlareSolverr
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status') == 'ok':
                        solution = data.get('solution', {})
                        
                        # Проверяем результат
                        if solution.get('status') == 200:
                            logger.info(f"✅ Успешно получена страница через FlareSolverr")
                            if current_proxy:
                                logger.info(f"   Использован прокси: {current_proxy[:40]}...")
                            return solution
                        else:
                            logger.warning(f"FlareSolverr вернул статус {solution.get('status')}")
                            
                            # Проверяем на капчу/блокировку
                            response_text = solution.get('response', '').lower()
                            if 'captcha' in response_text or 'ddos-guard' in response_text:
                                logger.warning(f"Обнаружена защита, пробуем другой прокси...")
                                time.sleep(2)
                                continue
                    else:
                        logger.warning(f"FlareSolverr ошибка: {data.get('message')}")
                        
                        # Если ошибка связана с сессией, создаем новую
                        if "session" in data.get('message', '').lower():
                            logger.info("Создаем новую сессию...")
                            self.create_session_with_proxy()
                            time.sleep(1)
                            continue
                else:
                    logger.error(f"HTTP ошибка FlareSolverr: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут FlareSolverr, пробуем другой подход...")
            except Exception as e:
                logger.error(f"Ошибка FlareSolverr: {type(e).__name__}")
            
            # Пауза между попытками
            if attempt < max_attempts - 1:
                time.sleep(3)
        
        logger.error("Все попытки FlareSolverr не удались")
        return None
    
    def destroy_session(self):
        """Уничтожить сессию"""
        if self.session_id:
            try:
                payload = {
                    "cmd": "sessions.destroy",
                    "session": self.session_id
                }
                requests.post(self.base_url, json=payload, timeout=10)
                logger.info(f"Сессия FlareSolverr уничтожена: {self.session_id}")
            except Exception as e:
                logger.warning(f"Ошибка уничтожения сессии: {e}")
            self.session_id = None
    
    def __del__(self):
        """Деструктор - закрываем сессию"""
        self.destroy_session()

# Тестирование
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=== ТЕСТ FLARESOLVERR С ПРОКСИ ===")
    
    client = AdvancedFlareSolverrClient()
    
    # Тестовый запрос
    solution = client.solve_with_proxy_rotation("https://43xgeorgia.me")
    
    if solution:
        print(f"✅ Статус: {solution.get('status')}")
        print(f"   URL: {solution.get('url')}")
        print(f"   Cookies: {len(solution.get('cookies', []))}")
        print(f"   User-Agent: {solution.get('userAgent', '')[:50]}...")
        
        # Проверяем содержимое
        response = solution.get('response', '')
        if response:
            print(f"   Размер ответа: {len(response)} байт")
            
            if 'георгий' in response.lower() or 'продаж' in response.lower():
                print("   🎉 Найден контент сайта!")
            elif 'ddos-guard' in response.lower():
                print("   ⚠️  Обнаружен DDoS-Guard")
            elif 'captcha' in response.lower():
                print("   ⚠️  Обнаружена капча")
    else:
        print("❌ Не удалось получить страницу")
