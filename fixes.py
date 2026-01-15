"""
ФИКСЫ ДЛЯ UPBOT + FLARESOLVERR
1. Исправление undetected-chromedriver (убраны excludeSwitches)
2. Исправление FlareSolverr подключения
3. Добавление поддержки прокси
4. Правильный порядок действий для 18+ сайта
"""

# =========================
# КРИТИЧЕСКИЙ ФИКС №1: FlareSolverr URL
# =========================
"""
В .env файле ИЗМЕНИТЬ:
БЫЛО: FLARESOLVERR_URL=http://localhost:8191/v1
СТАЛО: FLARESOLVERR_URL=http://localhost:8191
"""

# =========================
# КРИТИЧЕСКИЙ ФИКС №2: Обновленный config.py
# =========================
config_py_fix = '''
import os
from datetime import time as dtime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# FlareSolverr
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")  # ⚠️ БЕЗ /v1!
FLARESOLVERR_ENABLED = os.getenv("FLARESOLVERR_ENABLED", "true").lower() in ("1", "true", "yes")

# Прокси настройки
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() in ("1", "true", "yes")
PROXY_ROTATION = os.getenv("PROXY_ROTATION", "true").lower() in ("1", "true", "yes")
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "30"))

# Список прокси
PROXY_LIST = []
for i in range(1, 11):
    proxy = os.getenv(f"PROXY_{i}")
    if proxy:
        PROXY_LIST.append(proxy.strip())

FALLBACK_PROXY = os.getenv("FALLBACK_PROXY")
FLARESOLVERR_PROXY = os.getenv("FLARESOLVERR_PROXY")

# Настройки сайта
TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))
SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Паузы
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "10"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "20"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "60"))

def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except:
        return default

WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

# Дополнительные настройки
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
'''

# =========================
# КРИТИЧЕСКИЙ ФИКС №3: Исправленный upbot.py
# =========================
upbot_py_fix = '''import os
import time
import random
import socket
import requests
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# =========================
# CONFIG
# =========================
load_dotenv()

# FlareSolverr
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")
FLARESOLVERR_ENABLED = os.getenv("FLARESOLVERR_ENABLED", "true").lower() in ("1", "true", "yes")

# Прокси
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() in ("1", "true", "yes")
PROXY_ROTATION = os.getenv("PROXY_ROTATION", "true").lower() in ("1", "true", "yes")
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "30"))
PROXY_LIST = []
for i in range(1, 11):
    proxy = os.getenv(f"PROXY_{i}")
    if proxy:
        PROXY_LIST.append(proxy.strip())
FALLBACK_PROXY = os.getenv("FALLBACK_PROXY")

# Сайт
TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))
SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Паузы
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "8"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "15"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "45"))

def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except:
        return default

WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

# =========================
# UTILITIES
# =========================
def now_str() -> str:
    return datetime.now(TBILISI_TZ).strftime("%H:%M:%S")

def is_working_time() -> bool:
    now_t = datetime.now(TBILISI_TZ).time()
    if WORK_START <= WORK_END:
        return WORK_START <= now_t <= WORK_END
    return now_t >= WORK_START or now_t <= WORK_END

def load_accounts():
    accounts = []
    i = 1
    while True:
        login = os.getenv(f"ACC{i}_LOGIN")
        password = os.getenv(f"ACC{i}_PASS")
        if login and password:
            accounts.append({
                "number": i,
                "login": login.strip(),
                "password": password.strip()
            })
            i += 1
        else:
            break
    if not accounts:
        raise RuntimeError("Нет аккаунтов в .env")
    return accounts

def human_pause(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

# =========================
# PROXY MANAGER
# =========================
class ProxyManager:
    def __init__(self, proxy_list, fallback_proxy=None):
        self.proxy_list = proxy_list
        self.fallback_proxy = fallback_proxy
        self.current_index = 0
        self.bad_proxies = set()
        
    def get_proxy_for_account(self, account_index):
        if not self.proxy_list:
            return self.fallback_proxy
            
        if PROXY_ROTATION:
            proxy = self.proxy_list[account_index % len(self.proxy_list)]
            if proxy in self.bad_proxies:
                for p in self.proxy_list:
                    if p not in self.bad_proxies:
                        return p
                return self.fallback_proxy
            return proxy
        else:
            return self.proxy_list[0] if self.proxy_list else self.fallback_proxy
    
    def mark_bad(self, proxy):
        if proxy:
            self.bad_proxies.add(proxy)
            print(f"[{now_str()}] ⚠️ Прокси помечен как нерабочий: {proxy[:50]}...")
    
    def reset_bad_proxies(self):
        self.bad_proxies.clear()
        
    def test_proxy(self, proxy):
        if not proxy:
            return False
        try:
            parsed = urlparse(proxy)
            host = parsed.hostname
            port = parsed.port or (8080 if "http" in proxy else 1080)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

# =========================
# FLARESOLVERR HELPER (ИСПРАВЛЕННЫЙ)
# =========================
class FlareSolverrHelper:
    def __init__(self, flaresolverr_url):
        self.flaresolverr_url = flaresolverr_url.rstrip('/')
        self.session_id = None
        self.user_agent = None
        
    def is_available(self):
        try:
            response = requests.get(f"{self.flaresolverr_url}/", timeout=5)
            return response.status_code == 200
        except:
            try:
                response = requests.get(f"{self.flaresolverr_url}/v1", timeout=5)
                return response.status_code == 200
            except:
                return False
    
    def create_session(self):
        try:
            payload = {"cmd": "sessions.create"}
            response = requests.post(
                f"{self.flaresolverr_url}/v1",
                json=payload,
                timeout=30
            )
            data = response.json()
            
            if data.get("status") == "ok":
                self.session_id = data["session"]
                print(f"[{now_str()}] 🔑 Создана сессия FlareSolverr: {self.session_id[:8]}...")
                return True
            else:
                print(f"[{now_str()}] ❌ FlareSolverr ошибка: {data}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"[{now_str()}] ❌ Не могу подключиться к FlareSolverr")
            return False
        except Exception as e:
            print(f"[{now_str()}] ❌ Ошибка создания сессии: {e}")
            return False
    
    def get_with_flaresolverr(self, url):
        try:
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
                "session": self.session_id
            }
            
            response = requests.post(
                f"{self.flaresolverr_url}/v1",
                json=payload,
                timeout=90
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.user_agent = data["solution"].get("userAgent")
                    return data["solution"]
            
            return None
        except Exception as e:
            print(f"[{now_str()}] ❌ Ошибка FlareSolverr: {e}")
            return None
    
    def destroy_session(self):
        if self.session_id:
            try:
                payload = {"cmd": "sessions.destroy", "session": self.session_id}
                requests.post(f"{self.flaresolverr_url}/v1", json=payload, timeout=10)
            except:
                pass
            self.session_id = None

# Инициализируем
flaresolverr = FlareSolverrHelper(FLARESOLVERR_URL) if FLARESOLVERR_ENABLED else None

# =========================
# BROWSER DRIVER (ИСПРАВЛЕННЫЙ - БЕЗ excludeSwitches)
# =========================
def create_driver(proxy=None, user_agent=None):
    options = uc.ChromeOptions()
    
    if HEADLESS:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-automation")
    
    # User-Agent
    if user_agent:
        options.add_argument(f"user-agent={user_agent}")
    else:
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Прокси (простая версия - только без аутентификации)
    if proxy:
        print(f"[{now_str()}] 🌐 Используем прокси: {proxy[:50]}...")
        options.add_argument(f'--proxy-server={proxy}')
    
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_page_load_timeout(30)
        
        # Убираем webdriver признаки
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка создания драйвера: {e}")
        raise

# =========================
# WEBSITE FUNCTIONS
# =========================
def pass_18plus_protection(driver):
    try:
        human_pause(2, 3)
        
        # Ищем кнопки
        selectors = ["button", "a", "input[type='submit']", "div[onclick]"]
        
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                try:
                    text = (elem.text or "").lower()
                    if any(word in text for word in ["continue", "далее", "войти", "enter", "18+"]):
                        elem.click()
                        print(f"[{now_str()}] ✅ 18+ защита пройдена")
                        human_pause(3, 5)
                        return True
                except:
                    continue
        
        return False
    except Exception as e:
        print(f"[{now_str()}] ⚠️ Ошибка при прохождении 18+: {e}")
        return False

def do_login(driver, acc):
    try:
        print(f"[{now_str()}] 🔐 Логин для {acc['login']}...")
        
        driver.get("https://43xgeorgia.me/wp-login.php")
        human_pause(4, 6)
        
        # Логин
        username_field = driver.find_element(By.ID, "user_login")
        username_field.clear()
        for char in acc['login']:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        human_pause(1, 2)
        
        # Пароль
        password_field = driver.find_element(By.ID, "user_pass")
        password_field.clear()
        for char in acc['password']:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        
        human_pause(1, 2)
        
        # Кнопка входа
        submit_button = driver.find_element(By.ID, "wp-submit")
        submit_button.click()
        
        print(f"[{now_str()}] ✅ Логин отправлен")
        human_pause(5, 8)
        
        # Проверка
        current_url = driver.current_url
        if "wp-login.php" not in current_url:
            print(f"[{now_str()}] 🎉 Успешный логин!")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка логина: {e}")
        return False

def do_up(driver, acc):
    try:
        print(f"[{now_str()}] 🔼 Ищем кнопку UP...")
        human_pause(3, 5)
        
        # Ищем кнопку UP
        selectors = [
            "a.k-up.send",
            "a[class*='k-up']",
            "a[href*='?up=']",
            "//a[contains(text(), 'UP')]"
        ]
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    up_link = driver.find_element(By.XPATH, sel)
                else:
                    up_link = driver.find_element(By.CSS_SELECTOR, sel)
                
                href = up_link.get_attribute("href")
                if href:
                    driver.get(href)
                    print(f"[{now_str()}] 🎉 UP выполнен")
                else:
                    up_link.click()
                    print(f"[{now_str()}] 🎉 UP выполнен")
                
                human_pause(3, 5)
                return True
            except:
                continue
        
        print(f"[{now_str()}] ⚠️ Кнопка UP не найдена")
        return False
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка при UP: {e}")
        return False

def do_logout(driver):
    try:
        logout_url = "https://43xgeorgia.me/wp-login.php?action=logout"
        driver.get(logout_url)
        human_pause(3, 5)
        return True
    except:
        return False

# =========================
# PROCESS ACCOUNT (ИСПРАВЛЕННЫЙ ПОРЯДОК)
# =========================
def process_account(acc, account_index, total_accounts, proxy_manager=None):
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 🔄 Аккаунт #{acc['number']} ({account_index}/{total_accounts}): {acc['login']}")
    print(f"{'='*50}")
    
    driver = None
    proxy = None
    
    try:
        # 1. Получаем прокси
        if proxy_manager and PROXY_ENABLED:
            proxy = proxy_manager.get_proxy_for_account(account_index - 1)
            if proxy:
                print(f"[{now_str()}] 🌐 Используем прокси")
        
        # 2. Создаем драйвер
        user_agent = flaresolverr.user_agent if flaresolverr else None
        driver = create_driver(proxy=proxy, user_agent=user_agent)
        human_pause(2, 3)
        
        # 3. FlareSolverr (если доступен)
        if FLARESOLVERR_ENABLED and flaresolverr and flaresolverr.session_id:
            print(f"[{now_str()}] 🎯 Используем FlareSolverr...")
            
            solution = flaresolverr.get_with_flaresolverr(SITE_URL)
            if solution:
                print(f"[{now_str()}] ✅ FlareSolverr получил страницу")
                
                # Переходим на сайт
                driver.get(SITE_URL)
                human_pause(3, 4)
                
                # Пробуем применить cookies
                try:
                    cookies = solution.get("cookies", [])
                    for cookie in cookies:
                        try:
                            driver.add_cookie({
                                'name': cookie['name'],
                                'value': cookie['value'],
                                'domain': cookie.get('domain', '.43xgeorgia.me')
                            })
                        except:
                            pass
                    driver.refresh()
                    human_pause(2, 3)
                except:
                    pass
            else:
                print(f"[{now_str()}] ⚠️ FlareSolverr не сработал")
                driver.get(SITE_URL)
                human_pause(5, 7)
        else:
            # 4. Прямой заход на сайт
            driver.get(SITE_URL)
            human_pause(5, 7)
        
        # 5. 18+ защита
        pass_18plus_protection(driver)
        
        # 6. Логин
        if not do_login(driver, acc):
            print(f"[{now_str()}] ❌ Ошибка логина")
            return
        
        # 7. UP
        if do_up(driver, acc):
            print(f"[{now_str()}] ✅ UP успешно выполнен")
            human_pause(2, 4)
        else:
            print(f"[{now_str()}] ⚠️ UP не удался")
        
        # 8. Логаут
        do_logout(driver)
        print(f"[{now_str()}] ✅ Аккаунт #{acc['number']} обработан!")
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Критическая ошибка: {e}")
        if proxy:
            proxy_manager.mark_bad(proxy)
        
    finally:
        if driver:
            try:
                driver.quit()
                print(f"[{now_str()}] 🗑️ Браузер закрыт")
            except:
                pass
        
        # Пауза между аккаунтами
        if account_index < total_accounts:
            pause = random.randint(PAUSE_MIN, PAUSE_MAX)
            print(f"[{now_str()}] ⏸️ Пауза {pause} сек...")
            time.sleep(pause)

# =========================
# MAIN FUNCTION
# =========================
def main():
    print(f"\n{'='*60}")
    print(f"[{now_str()}] 🚀 ЗАПУСК UPBOT с прокси")
    print(f"{'='*60}")
    
    # Инициализируем прокси менеджер
    proxy_manager = None
    if PROXY_ENABLED and PROXY_LIST:
        proxy_manager = ProxyManager(PROXY_LIST, FALLBACK_PROXY)
        print(f"[{now_str()}] 🌐 Загружено прокси: {len(PROXY_LIST)}")
    
    # FlareSolverr
    if FLARESOLVERR_ENABLED:
        print(f"[{now_str()}] 🔗 Проверяем FlareSolverr...")
        if flaresolverr and flaresolverr.is_available():
            print(f"[{now_str()}] ✅ FlareSolverr доступен")
            if flaresolverr.create_session():
                print(f"[{now_str()}] ✅ Сессия создана")
            else:
                print(f"[{now_str()}] ⚠️ Не удалось создать сессию")
        else:
            print(f"[{now_str()}] ❌ FlareSolverr недоступен")
    
    # Загружаем аккаунты
    try:
        accounts = load_accounts()
        print(f"[{now_str()}] 📋 Аккаунтов: {len(accounts)}")
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка загрузки аккаунтов: {e}")
        return
    
    cycle_count = 0
    
    while True:
        if is_working_time():
            cycle_count += 1
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] 🔄 ЦИКЛ #{cycle_count}")
            print(f"[{'='*50}]\n")
            
            for i, account in enumerate(accounts, 1):
                process_account(account, i, len(accounts), proxy_manager)
            
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] ✅ ЦИКЛ #{cycle_count} ЗАВЕРШЕН")
            
            if proxy_manager:
                proxy_manager.reset_bad_proxies()
            
            pause = random.randint(ROUND_PAUSE_MAX // 2, ROUND_PAUSE_MAX)
            print(f"[{now_str()}] ⏸️ Пауза {pause} сек...")
            time.sleep(pause)
            
        else:
            print(f"[{now_str()}] ⏰ Вне времени работы, ждем...")
            time.sleep(300)

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] ⏹️ Остановлено")
        if FLARESOLVERR_ENABLED and flaresolverr:
            flaresolverr.destroy_session()
    except Exception as e:
        print(f"\n[{now_str()}] ❌ Критическая ошибка: {e}")
'''

# =========================
# КРИТИЧЕСКИЙ ФИКС №4: Обновленный .env файл
# =========================
env_fix = '''
# Основные настройки
SITE_URL=https://43xgeorgia.me/ru
TIMEZONE=Asia/Tbilisi

# Время работы
WORK_START=15:00
WORK_END=10:30

# Браузер
HEADLESS=true

# Паузы
PAUSE_MIN_SECONDS=5
PAUSE_MAX_SECONDS=12
ROUND_PAUSE_MAX_SECONDS=30

# FlareSolverr
FLARESOLVERR_URL=http://localhost:8191  # ⚠️ БЕЗ /v1!
FLARESOLVERR_ENABLED=true

# Прокси настройки
PROXY_ENABLED=false  # Поставь true когда добавишь прокси
PROXY_ROTATION=true
PROXY_TIMEOUT=30

# Примеры прокси (раскомментируй и заполни):
# PROXY_1=http://user:pass@193.123.123.123:8080
# PROXY_2=http://user:pass@194.124.124.124:8080
# PROXY_3=http://45.85.65.44:8080
# FALLBACK_PROXY=http://backup:pass@proxy.com:8080

# =========================
# АККАУНТЫ
# =========================
ACC1_LOGIN=ilona1tbs@gmail.com
ACC1_PASS=Sofasofa202626

ACC2_LOGIN=marina1tbilisi@gmail.com
ACC2_PASS=Sofasofa202626

ACC3_LOGIN=ellatbs
ACC3_PASS=Sofasofa202626

ACC4_LOGIN=martatbs
ACC4_PASS=Sofasofa202626

ACC5_LOGIN=alinayerevan2@gmail.com
ACC5_PASS=Sofasofa202626

ACC6_LOGIN=dasha1tbilisi@gmail.com
ACC6_PASS=Sofasofa202626
'''

# =========================
# КРИТИЧЕСКИЙ ФИКС №5: Скрипт диагностики
# =========================
diagnostic_script = '''#!/usr/bin/env python3
"""
Скрипт диагностики для проверки всех компонентов
"""

import os
import sys
import socket
import requests
from dotenv import load_dotenv

load_dotenv()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def test_flaresolverr():
    """Тестируем FlareSolverr"""
    print_section("ПРОВЕРКА FLARESOLVERR")
    
    url = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")
    print(f"URL из .env: {url}")
    
    # Пробуем разные варианты
    test_urls = [
        url,
        url.rstrip('/'),
        f"{url.rstrip('/')}/",
        f"{url.rstrip('/')}/v1",
        "http://localhost:8191",
        "http://localhost:8191/v1",
        "http://127.0.0.1:8191",
        "http://127.0.0.1:8191/v1"
    ]
    
    working = False
    for test_url in test_urls:
        try:
            print(f"  Тестируем: {test_url}")
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ ДОСТУПЕН (статус: {response.status_code})")
                working = True
                
                # Пробуем создать сессию
                try:
                    payload = {"cmd": "sessions.create"}
                    resp = requests.post(f"{test_url.rstrip('/')}/v1", json=payload, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        print(f"  ✅ Сессия создана: {data.get('session', 'N/A')}")
                    else:
                        print(f"  ❌ Ошибка создания сессии: {resp.status_code}")
                except Exception as e:
                    print(f"  ⚠️ Не удалось создать сессию: {e}")
                
                return test_url.rstrip('/')
                
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Нет подключения")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    if not working:
        print("  ❌ FlareSolverr недоступен!")
        print("\n  Проверьте:")
        print("  1. docker-compose up -d flaresolverr")
        print("  2. docker ps")
        print("  3. docker-compose logs flaresolverr")
    
    return None

def test_proxies():
    """Тестируем прокси"""
    print_section("ПРОВЕРКА ПРОКСИ")
    
    proxy_list = []
    for i in range(1, 11):
        proxy = os.getenv(f"PROXY_{i}")
        if proxy:
            proxy_list.append(proxy)
    
    if not proxy_list:
        print("  ℹ️ Прокси не настроены")
        return
    
    print(f"  Найдено прокси: {len(proxy_list)}")
    
    working_count = 0
    for proxy in proxy_list:
        try:
            print(f"  Тестируем: {proxy[:50]}...")
            
            # Простой TCP тест
            parsed = urlparse(proxy)
            host = parsed.hostname
            port = parsed.port or (8080 if "http" in proxy else 1080)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"  ✅ Прокси доступен")
                working_count += 1
            else:
                print(f"  ❌ Прокси недоступен")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
    
    print(f"\n  📊 Итого: {working_count}/{len(proxy_list)} рабочих прокси")

def test_accounts():
    """Проверяем загрузку аккаунтов"""
    print_section("ПРОВЕРКА АККАУНТОВ")
    
    accounts = []
    i = 1
    while True:
        login = os.getenv(f"ACC{i}_LOGIN")
        password = os.getenv(f"ACC{i}_PASS")
        if login and password:
            accounts.append({"login": login, "password": "***" + password[-3:]})
            i += 1
        else:
            break
    
    if accounts:
        print(f"  ✅ Загружено аккаунтов: {len(accounts)}")
        for acc in accounts[:3]:  # Показываем только первые 3
            print(f"    • {acc['login']} : {acc['password']}")
        if len(accounts) > 3:
            print(f"    ... и еще {len(accounts)-3} аккаунтов")
    else:
        print("  ❌ Аккаунты не найдены в .env")

def test_requirements():
    """Проверяем установленные пакеты"""
    print_section("ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    
    required = ["undetected-chromedriver", "selenium", "requests", "python-dotenv"]
    
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - НЕ УСТАНОВЛЕН")

if __name__ == "__main__":
    print("🚀 ДИАГНОСТИЧЕСКИЙ СКРИПТ UPBOT")
    print("Версия: 2.0 (с фиксами)")
    
    test_requirements()
    test_flaresolverr()
    test_proxies()
    test_accounts()
    
    print_section("РЕКОМЕНДАЦИИ")
    
    # Проверяем настройки
    flaresolverr_url = os.getenv("FLARESOLVERR_URL", "")
    if "/v1" in flaresolverr_url:
        print("⚠️  ВНИМАНИЕ: FLARESOLVERR_URL не должен содержать /v1")
        print(f"   Было: {flaresolverr_url}")
        print(f"   Должно быть: {flaresolverr_url.replace('/v1', '')}")
    
    print("\n✅ Диагностика завершена")
'''

# =========================
# КРИТИЧЕСКИЙ ФИКС №6: Скрипт обновления на сервере
# =========================
update_script = '''#!/bin/bash
# update_bot.sh - Обновление бота на сервере

echo "🔄 ОБНОВЛЕНИЕ UPBOT НА СЕРВЕРЕ"
echo "================================"

# 1. Переходим в директорию проекта
cd ~/upbot-flaresolverr || { echo "❌ Директория не найдена"; exit 1; }

# 2. Делаем backup старой версии
echo "📦 Создаем backup..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp *.py *.yml *.txt *.sh "$BACKUP_DIR/" 2>/dev/null
echo "✅ Backup создан: $BACKUP_DIR"

# 3. Останавливаем текущий бот
echo "⏹️ Останавливаем текущий процесс..."
pkill -f "python3 upbot.py" 2>/dev/null
sleep 2

# 4. Обновляем config.py
echo "⚙️ Обновляем config.py..."
cat > config.py << 'EOF'
import os
from datetime import time as dtime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# FlareSolverr
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")
FLARESOLVERR_ENABLED = os.getenv("FLARESOLVERR_ENABLED", "true").lower() in ("1", "true", "yes")

# Прокси настройки
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() in ("1", "true", "yes")
PROXY_ROTATION = os.getenv("PROXY_ROTATION", "true").lower() in ("1", "true", "yes")
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "30"))

# Список прокси
PROXY_LIST = []
for i in range(1, 11):
    proxy = os.getenv(f"PROXY_{i}")
    if proxy:
        PROXY_LIST.append(proxy.strip())

FALLBACK_PROXY = os.getenv("FALLBACK_PROXY")

# Настройки сайта
TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))
SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Паузы
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "10"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "20"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "60"))

def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except:
        return default

WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
EOF
echo "✅ config.py обновлен"

# 5. Обновляем upbot.py
echo "🤖 Обновляем upbot.py..."
# (Здесь будет вставлен полный код upbot.py из фиксов)
echo "ℹ️  upbot.py нужно обновить вручную из файла фиксов"

# 6. Обновляем .env (если нужно)
echo "📝 Проверяем .env..."
if grep -q "FLARESOLVERR_URL.*/v1" .env 2>/dev/null; then
    echo "⚠️  Исправляю FLARESOLVERR_URL в .env"
    sed -i 's|FLARESOLVERR_URL=.*/v1|FLARESOLVERR_URL=http://localhost:8191|' .env
    echo "✅ FLARESOLVERR_URL исправлен"
fi

# 7. Проверяем FlareSolverr
echo "🔧 Проверяем FlareSolverr..."
docker-compose ps | grep flaresolverr | grep Up
if [ $? -eq 0 ]; then
    echo "✅ FlareSolverr запущен"
else
    echo "⚠️  FlareSolverr не запущен, запускаю..."
    docker-compose up -d flaresolverr
    sleep 5
fi

# 8. Запускаем диагностику
echo "🔍 Запускаем диагностику..."
cat > diagnostic.py << 'EOF'
import requests
try:
    r = requests.get("http://localhost:8191", timeout=5)
    print(f"✅ FlareSolverr: {r.status_code}")
except:
    print("❌ FlareSolverr недоступен")
EOF
python3 diagnostic.py
rm diagnostic.py

# 9. Обновляем requirements если нужно
echo "📦 Проверяем зависимости..."
pip install -r requirements.txt 2>/dev/null || pip install undetected-chromedriver selenium requests python-dotenv

# 10. Запускаем бота
echo "🚀 Запускаем бота..."
echo ""
echo "Команда для запуска:"
echo "cd ~/upbot-flaresolverr && python3 upbot.py"
echo ""
echo "Или в screen:"
echo "screen -S upbot -d -m python3 upbot.py"
echo ""
echo "✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО"
'''

# =========================
# КРИТИЧЕСКИЙ ФИКС №7: Быстрый старт
# =========================
quick_start_guide = '''
🚀 БЫСТРЫЙ СТАРТ С ФИКСАМИ:

1. ОБНОВИТЬ .env файл:
   - FLARESOLVERR_URL=http://localhost:8191  (БЕЗ /v1!)
   - Добавить прокси если нужно

2. ЗАПУСТИТЬ НА СЕРВЕРЕ:
   git pull
   ./update_bot.sh

3. ПРОВЕРИТЬ ВСЕ КОМПОНЕНТЫ:
   python3 diagnostic.py

4. ЗАПУСТИТЬ БОТА:
   screen -S upbot -d -m python3 upbot.py

5. ПРОВЕРИТЬ ЛОГИ:
   screen -r upbot
   Или: tail -f upbot.log (если настроено логирование)

🔧 ЕСЛИ ПРОБЛЕМЫ:

1. FlareSolverr не работает:
   docker-compose down
   docker-compose up -d flaresolverr
   docker-compose logs -f flaresolverr

2. Ошибка ChromeDriver:
   pip install --upgrade undetected-chromedriver
   apt update && apt install -y google-chrome-stable

3. Нет прокси:
   Временно отключи: PROXY_ENABLED=false
   Или добавь рабочие прокси в .env

📞 ПОМОЩЬ:
1. Проверь diagnostic.py
2. Проверь логи: docker-compose logs flaresolverr
3. Запусти тест: python3 test_flaresolverr.py
'''

# =========================
# Сохраняем все фиксы в файлы
# =========================
if __name__ == "__main__":
    import os
    
    print("🧩 СОЗДАНИЕ ФАЙЛОВ С ФИКСАМИ...")
    
    # 1. Сохраняем исправленный config.py
    with open("config_fixed.py", "w", encoding="utf-8") as f:
        f.write(config_py_fix)
    print("✅ config_fixed.py создан")
    
    # 2. Сохраняем исправленный upbot.py
    with open("upbot_fixed.py", "w", encoding="utf-8") as f:
        f.write(upbot_py_fix)
    print("✅ upbot_fixed.py создан")
    
    # 3. Сохраняем пример .env
    with open(".env.example", "w", encoding="utf-8") as f:
        f.write(env_fix)
    print("✅ .env.example создан")
    
    # 4. Сохраняем диагностический скрипт
    with open("diagnostic.py", "w", encoding="utf-8") as f:
        f.write(diagnostic_script)
    os.chmod("diagnostic.py", 0o755)
    print("✅ diagnostic.py создан (исполняемый)")
    
    # 5. Сохраняем скрипт обновления
    with open("update_bot.sh", "w", encoding="utf-8") as f:
        f.write(update_script)
    os.chmod("update_bot.sh", 0o755)
    print("✅ update_bot.sh создан (исполняемый)")
    
    # 6. Сохраняем руководство
    with open("QUICK_START.md", "w", encoding="utf-8") as f:
        f.write(quick_start_guide)
    print("✅ QUICK_START.md создан")
    
    print("\n🎯 ФАЙЛЫ ГОТОВЫ К ЗАЛИВКЕ НА ГИТ:")
    print("  1. config_fixed.py → замените config.py")
    print("  2. upbot_fixed.py → замените upbot.py") 
    print("  3. .env.example → используйте как шаблон")
    print("  4. diagnostic.py → запустите для проверки")
    print("  5. update_bot.sh → для быстрого обновления")
    print("  6. QUICK_START.md → инструкция по запуску")
    
    print("\n📋 КОМАНДЫ ДЛЯ СЕРВЕРА:")
    print("  git add .")
    print("  git commit -m 'Фиксы: FlareSolverr, прокси, порядок действий'")
    print("  git push")
    print("  На сервере: git pull && ./update_bot.sh")
