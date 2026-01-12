import os
import sys
import time
import random
import json
import requests
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Импортируем конфигурацию
from config import *

# =========================
# FLARESOLVERR HELPER
# =========================
class FlareSolverrProxy:
    def __init__(self, base_url=FLARESOLVERR_URL):
        self.base_url = base_url
        self.session_id = None
        self.request_count = 0
        
    def test_connection(self):
        """Проверка подключения к FlareSolverr"""
        try:
            response = requests.get(self.base_url.replace('/v1', ''), timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[{now_str()}] ❌ Ошибка подключения к FlareSolverr: {e}")
            return False
    
    def get_via_flaresolverr(self, url, use_session=True):
        """Получаем страницу через FlareSolverr"""
        self.request_count += 1
        
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 120000,  # 2 минуты
            "disableMedia": True,
            "waitInSeconds": random.randint(3, 7)
        }
        
        if USE_FLARESOLVERR_SESSIONS and use_session and self.session_id:
            payload["session"] = self.session_id
        
        try:
            print(f"[{now_str()}] 📨 Запрос {self.request_count} к FlareSolverr: {url[:50]}...")
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=130
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("status") == "ok":
                    solution = result.get("solution", {})
                    
                    if "session" in result:
                        self.session_id = result["session"]
                    
                    print(f"[{now_str()}] ✅ FlareSolverr успешно обработал запрос")
                    return {
                        "success": True,
                        "url": solution.get("url"),
                        "status": solution.get("status"),
                        "html": solution.get("response"),
                        "cookies": solution.get("cookies", []),
                        "user_agent": solution.get("userAgent"),
                        "headers": solution.get("headers", {})
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    print(f"[{now_str()}] ❌ FlareSolverr ошибка: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                print(f"[{now_str()}] ❌ HTTP ошибка {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print(f"[{now_str()}] ❌ Таймаут FlareSolverr (130s)")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            print(f"[{now_str()}] ❌ Исключение FlareSolverr: {e}")
            return {"success": False, "error": str(e)}
    
    def create_session(self):
        """Создаем новую сессию"""
        if not USE_FLARESOLVERR_SESSIONS:
            return True
            
        try:
            payload = {"cmd": "sessions.create"}
            response = requests.post(self.base_url, json=payload, timeout=30)
            result = response.json()
            
            if result.get("status") == "ok":
                self.session_id = result.get("session")
                print(f"[{now_str()}] 🔑 Создана сессия FlareSolverr: {self.session_id[:8]}...")
                return True
            else:
                print(f"[{now_str()}] ⚠️ Не удалось создать сессию")
                return False
        except Exception as e:
            print(f"[{now_str()}] ❌ Ошибка создания сессии: {e}")
            return False
    
    def destroy_session(self):
        """Уничтожаем текущую сессию"""
        if not self.session_id:
            return
            
        try:
            payload = {"cmd": "sessions.destroy", "session": self.session_id}
            requests.post(self.base_url, json=payload, timeout=10)
            print(f"[{now_str()}] 🗑️ Уничтожена сессия: {self.session_id[:8]}...")
        except:
            pass
        finally:
            self.session_id = None

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
    """Загружаем аккаунты из .env"""
    accounts = []
    i = 1
    while True:
        login = os.getenv(f"ACC{i}_LOGIN")
        password = os.getenv(f"ACC{i}_PASS")
        if login and password:
            accounts.append({
                "id": i,
                "login": login.strip(),
                "password": password.strip()
            })
            i += 1
        else:
            break
    
    if not accounts:
        raise RuntimeError("❌ Нет аккаунтов в .env")
    
    print(f"[{now_str()}] 📋 Загружено аккаунтов: {len(accounts)}")
    return accounts

# =========================
# BROWSER MANAGEMENT
# =========================
def create_driver():
    """Создаем оптимизированный драйвер"""
    options = uc.ChromeOptions()
    
    if HEADLESS:
        options.add_argument("--headless=new")
    
    # Критичные настройки для сервера
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    
    # Экономия памяти
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-background-timer-throttling")
    
    # User-Agent будет установлен позже
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    try:
        print(f"[{now_str()}] 🌐 Создаем браузер...")
        driver = uc.Chrome(options=options, use_subprocess=True)
        
        # Скрываем автоматизацию
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """
        })
        
        return driver
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка создания драйвера: {e}")
        raise

def apply_flaresolverr_cookies(driver, flaresolverr_result):
    """Применяем куки от FlareSolverr"""
    if not flaresolverr_result.get("success"):
        return False
    
    cookies = flaresolverr_result.get("cookies", [])
    if not cookies:
        print(f"[{now_str()}] ⚠️ Нет кук для применения")
        return False
    
    # ОТЛАДКА: смотрим какие куки получили
    print(f"[{now_str()}] 🔍 ДЕБАГ: Получено {len(cookies)} кук от FlareSolverr:")
    for i, cookie in enumerate(cookies):
        print(f"    Кука {i+1}: name='{cookie.get('name')}', domain='{cookie.get('domain')}', "
              f"path='{cookie.get('path')}', secure={cookie.get('secure', False)}")
    
    try:
        # СНАЧАЛА нужно перейти на домен, к которому относятся куки!
        # Куки не будут установлены для произвольного домена
        if cookies and cookies[0].get('domain'):
            domain = cookies[0]['domain']
            # Убираем точку в начале если есть (например .43xgeorgia.me -> 43xgeorgia.me)
            if domain.startswith('.'):
                domain = domain[1:]
            
            # Переходим на домен
            driver.get(f"https://{domain}")
            time.sleep(2)
            print(f"[{now_str()}] 🌐 Перешли на домен кук: {domain}")
        
        # Очищаем старые куки (после перехода на домен)
        driver.delete_all_cookies()
        
        # Устанавливаем User-Agent
        user_agent = flaresolverr_result.get("user_agent")
        if user_agent:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
            print(f"[{now_str()}] 🤖 Установлен User-Agent из FlareSolverr")
        
        # Добавляем все куки
        success_count = 0
        for cookie in cookies:
            try:
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '43xgeorgia.me'),  # Убрал точку!
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                if 'expires' in cookie:
                    cookie_dict['expiry'] = int(cookie['expires'])
                
                driver.add_cookie(cookie_dict)
                success_count += 1
                print(f"[{now_str()}] ✓ Добавлена кука: {cookie['name']}")
            except Exception as e:
                print(f"[{now_str()}] ✗ Ошибка добавления куки {cookie.get('name')}: {e}")
                continue
        
        print(f"[{now_str()}] 🍪 Применено кук: {success_count}/{len(cookies)}")
        
        # Проверяем, что куки установились
        driver.refresh()
        time.sleep(2)
        current_cookies = driver.get_cookies()
        print(f"[{now_str()}] 🔍 Проверка: в браузере сейчас {len(current_cookies)} кук")
        
        return success_count > 0
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка применения кук: {e}")
        return False

# =========================
# WEBSITE FUNCTIONS
# =========================
def navigate_with_flaresolverr(driver, flaresolverr, url):
    """Навигация с использованием FlareSolverr"""
    result = flaresolverr.get_via_flaresolverr(url)
    
    if not result.get("success"):
        print(f"[{now_str()}] ❌ FlareSolverr не смог получить страницу")
        return False
    
    print(f"[{now_str()}] 🔗 FlareSolverr получил страницу, статус: {result.get('status')}")
    
    # 1. ПЕРВОЕ: применяем куки
    if not apply_flaresolverr_cookies(driver, result):
        print(f"[{now_str()}] ⚠️ Куки не применились, пробуем загрузить страницу напрямую")
        # Если куки не применились, просто переходим по URL
        driver.get(url)
        time.sleep(5)
        # Проверяем, не попали ли на капчу
        page_source = driver.page_source.lower()
        if "checking your browser" in page_source or "i'm not a robot" in page_source:
            print(f"[{now_str()}] ❌ Все равно попали на капчу")
            return False
        return True
    
    # 2. После успешного применения кук загружаем HTML или просто переходим
    print(f"[{now_str()}] 🚀 Переходим по URL с примененными куками...")
    driver.get(url)
    time.sleep(5)
    
    # Проверяем, не попали ли на капчу
    page_source = driver.page_source.lower()
    if "checking your browser" in page_source or "i'm not a robot" in page_source:
        print(f"[{now_str()}] ❌ Все равно попали на капчу после применения кук")
        return False
    
    print(f"[{now_str()}] ✅ Успешно обошли защиту!")
    return True

def handle_18plus(driver):
    """Обработка 18+ защиты"""
    print(f"[{now_str()}] 🔞 Ищем 18+ защиту...")
    
    # Сначала проверим, есть ли уже 18+ защита на странице
    page_source = driver.page_source.lower()
    adult_keywords = ["adult", "18+", "age verification", "confirm age", "adult content"]
    
    for keyword in adult_keywords:
        if keyword in page_source:
            print(f"[{now_str()}] 🔍 Найдено упоминание 18+: {keyword}")
            break
    
    try:
        elements = driver.find_elements(By.XPATH, 
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'click') or "
            "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue') or "
            "contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолж') or "
            "contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'наж') or "
            "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'enter') or "
            "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]"
        )
        
        for elem in elements:
            if elem.is_displayed():
                elem_text = elem.text.strip().lower()
                print(f"[{now_str()}] 🔘 Найдена кнопка: '{elem_text}'")
                driver.execute_script("arguments[0].click();", elem)
                print(f"[{now_str()}] ✅ 18+ защита пройдена")
                time.sleep(2)
                return True
        
        # Пробуем другие селекторы
        selectors = [
            "button",
            "input[type='button']",
            "input[type='submit']",
            "a.btn",
            "a.button",
            "div[onclick*='click']",
            "div[style*='cursor:pointer']"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        elem_text = elem.text.strip().lower()
                        if elem_text and len(elem_text) < 50:  # Не слишком длинный текст
                            print(f"[{now_str()}] 🎯 Кликаем по элементу с текстом: '{elem_text}'")
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(1)
                            return True
            except:
                continue
                
    except Exception as e:
        print(f"[{now_str()}] ⚠️ Ошибка при поиске 18+ защиты: {e}")
    
    print(f"[{now_str()}] ℹ️ 18+ защита не найдена или не требуется")
    return False

def login_to_site(driver, account):
    """Логин на сайте"""
    print(f"[{now_str()}] 🔐 Начинаем логин для {account['login']}...")
    
    try:
        # Переходим на страницу логина
        login_url = "https://43xgeorgia.me/wp-login.php"
        print(f"[{now_str()}] 📍 Переходим на {login_url}")
        driver.get(login_url)
        time.sleep(3)
        
        # Проверяем, не попали ли на капчу
        page_source = driver.page_source.lower()
        if "checking your browser" in page_source or "i'm not a robot" in page_source:
            print(f"[{now_str()}] ❌ Попали на капчу при переходе на логин")
            return False
        
        # Ищем поле логина
        print(f"[{now_str()}] 🔍 Ищем поле логина...")
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_login"))
        )
        
        # Человекоподобный ввод
        print(f"[{now_str()}] ⌨️ Вводим логин...")
        username.clear()
        for char in account['login']:
            username.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(0.5, 1))
        
        # Поле пароля
        print(f"[{now_str()}] 🔑 Вводим пароль...")
        password = driver.find_element(By.ID, "user_pass")
        password.clear()
        for char in account['password']:
            password.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(0.5, 1))
        
        # Кнопка входа
        print(f"[{now_str()}] 🖱️ Нажимаем кнопку входа...")
        submit = driver.find_element(By.ID, "wp-submit")
        submit.click()
        
        # Ждем и проверяем результат
        print(f"[{now_str()}] ⏳ Ждем результат логина...")
        time.sleep(5)
        
        current_url = driver.current_url
        print(f"[{now_str()}] 🌐 Текущий URL: {current_url}")
        
        if "wp-admin" in current_url or "profile.php" in current_url or "wp-login.php?loggedout" not in current_url:
            print(f"[{now_str()}] ✅ Успешный логин: {account['login']}")
            return True
        else:
            # Проверяем есть ли ошибка
            try:
                error_div = driver.find_element(By.ID, "login_error")
                if error_div:
                    error_text = error_div.text[:100]
                    print(f"[{now_str()}] ❌ Ошибка логина: {error_text}")
            except:
                print(f"[{now_str()}] ⚠️ Неизвестная ошибка логина")
            
            return False
            
    except Exception as e:
        print(f"[{now_str()}] ❌ Исключение при логине: {e}")
        return False

def perform_up(driver, account):
    """Выполняем UP действие"""
    print(f"[{now_str()}] 🎯 Ищем кнопку UP для {account['login']}...")
    
    selectors = [
        "a.k-up.send",
        "a[class*='k-up'][class*='send']",
        "a.up-btn",
        "a[href*='?up=1']",
        "//a[contains(@class, 'up')]",
        "//button[contains(@class, 'up')]",
        "//*[contains(text(), 'UP') or contains(text(), 'Up') or contains(text(), 'ПОДНЯТЬ')]",
    ]
    
    for selector in selectors:
        try:
            print(f"[{now_str()}] 🔎 Пробуем селектор: {selector}")
            
            if selector.startswith("//"):
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
            else:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
            
            # Кликаем
            href = element.get_attribute("href")
            if href:
                print(f"[{now_str()}] 🔗 Нашли ссылку UP: {href}")
                driver.get(href)
            else:
                print(f"[{now_str()}] 🖱️ Кликаем по элементу UP")
                driver.execute_script("arguments[0].click();", element)
            
            print(f"[{now_str()}] 🎉 UP выполнен для {account['login']}")
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"[{now_str()}] ⚠️ Селектор {selector} не сработал: {e}")
            continue
    
    # Дополнительный поиск по тексту
    print(f"[{now_str()}] 🔍 Дополнительный поиск UP...")
    try:
        # Ищем все ссылки
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            try:
                href = link.get_attribute("href") or ""
                text = link.text or ""
                if "up" in href.lower() or "up" in text.lower() or "поднять" in text.lower():
                    if link.is_displayed():
                        print(f"[{now_str()}] 🎯 Нашли UP по тексту/ссылке: {text}")
                        link.click()
                        time.sleep(3)
                        print(f"[{now_str()}] 🎉 UP выполнен (альтернативный метод)")
                        return True
            except:
                continue
    except:
        pass
    
    print(f"[{now_str()}] ⚠️ UP не найден для {account['login']}")
    return False

def logout(driver):
    """Выход из аккаунта"""
    print(f"[{now_str()}] 👋 Пытаемся выйти...")
    
    try:
        logout_urls = [
            "https://43xgeorgia.me/wp-login.php?action=logout",
            "https://43xgeorgia.me/?action=logout",
            "https://43xgeorgia.me/logout"
        ]
        
        for url in logout_urls:
            try:
                driver.get(url)
                time.sleep(2)
                
                # Ищем подтверждение выхода
                confirm_selectors = [
                    "//a[contains(text(), 'log out') or contains(text(), 'Log Out') or contains(text(), 'Выйти')]",
                    "//a[contains(@href, 'logout')]",
                    "//button[contains(text(), 'Выход') or contains(text(), 'Logout')]",
                ]
                
                for sel in confirm_selectors:
                    try:
                        confirm_btn = driver.find_element(By.XPATH, sel)
                        if confirm_btn.is_displayed():
                            print(f"[{now_str()}] ✅ Нашли кнопку подтверждения выхода")
                            confirm_btn.click()
                            time.sleep(2)
                            break
                    except:
                        continue
                
                print(f"[{now_str()}] ✅ Выход выполнен")
                return True
                
            except:
                continue
        
        # Если не нашли специальную страницу, просто переходим на главную
        driver.get(SITE_URL)
        return True
        
    except Exception as e:
        print(f"[{now_str()}] ⚠️ Ошибка при выходе: {e}")
        return False

# =========================
# ACCOUNT PROCESSING
# =========================
def process_single_account(account, flaresolverr):
    """Обработка одного аккаунта (ОПТИМИЗИРОВАННАЯ ВЕРСИЯ)"""
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 🔄 Обрабатываем аккаунт #{account['id']}: {account['login']}")
    
    driver = None
    try:
        # 1. Создаем драйвер
        driver = create_driver()
        
        # 2. Стратегия: FlareSolverr ТОЛЬКО для страницы логина
        # Потому что главная страница может не требовать кук, а страница логина - требует
        print(f"[{now_str()}] 🎯 Стратегия: FlareSolverr для страницы логина")
        
        login_url = "https://43xgeorgia.me/wp-login.php"
        print(f"[{now_str()}] 🔐 Запрашиваем страницу логина через FlareSolverr...")
        
        result = flaresolverr.get_via_flaresolverr(login_url)
        
        if not result.get("success"):
            print(f"[{now_str()}] ❌ FlareSolverr не смог получить страницу логина")
            return False
        
        print(f"[{now_str()}] ✅ FlareSolverr получил страницу логина")
        
        # 3. Применяем куки к драйверу
        if apply_flaresolverr_cookies(driver, result):
            print(f"[{now_str()}] ✅ Куки успешно применены")
        else:
            print(f"[{now_str()}] ⚠️ Куки не применились, пробуем без них")
        
        # 4. Теперь переходим на главную страницу
        print(f"[{now_str()}] 🏠 Переходим на главную страницу...")
        driver.get(SITE_URL)
        time.sleep(3)
        
        # Проверяем, не попали ли на капчу
        page_source = driver.page_source.lower()
        if "checking your browser" in page_source or "i'm not a robot" in page_source:
            print(f"[{now_str()}] ❌ Попали на капчу на главной странице")
            return False
        
        # 5. Обрабатываем 18+ защиту
        handle_18plus(driver)
        
        # 6. Теперь логин (должен работать, так как у нас есть куки от FlareSolverr)
        if not login_to_site(driver, account):
            print(f"[{now_str()}] ❌ Логин не удался")
            return False
        
        # 7. Выполняем UP
        if not perform_up(driver, account):
            print(f"[{now_str()}] ⚠️ UP не выполнен, но продолжаем...")
        
        # 8. Выход
        logout(driver)
        
        print(f"[{now_str()}] ✅ Аккаунт #{account['id']} успешно обработан!")
        return True
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Всегда закрываем драйвер
        if driver:
            try:
                driver.quit()
                print(f"[{now_str()}] 🗑️ Браузер закрыт")
            except:
                pass

# =========================
# MAIN FUNCTION
# =========================
def main():
    print(f"\n{'='*60}")
    print(f"[{now_str()}] 🚀 ЗАПУСК UPBOT + FLARESOLVERR (ОБНОВЛЕННАЯ ВЕРСИЯ)")
    print(f"{'='*60}")
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print(f"[{now_str()}] ❌ Требуется Python 3.8+")
        return
    
    # Инициализируем FlareSolverr
    if FLARESOLVERR_ENABLED:
        flaresolverr = FlareSolverrProxy()
        
        # Проверяем соединение
        print(f"[{now_str()}] 🔗 Проверяем FlareSolverr...")
        if not flaresolverr.test_connection():
            print(f"[{now_str()}] ❌ FlareSolverr недоступен!")
            print(f"[{now_str()}] Убедитесь что сервис запущен: docker-compose up -d")
            
            if os.getenv("FLARESOLVERR_REQUIRED", "true").lower() in ("1", "true", "yes"):
                return
        else:
            print(f"[{now_str()}] ✅ FlareSolverr доступен")
            
            # Создаем сессию
            if USE_FLARESOLVERR_SESSIONS:
                flaresolverr.create_session()
    else:
        print(f"[{now_str()}] ⚠️ FlareSolverr отключен в настройках")
        flaresolverr = None
    
    # Загружаем аккаунты
    try:
        accounts = load_accounts()
    except Exception as e:
        print(f"[{now_str()}] ❌ {e}")
        return
    
    # Основной цикл
    cycle = 0
    print(f"\n[{'='*50}]")
    print(f"[{now_str()}] ⏰ Режим работы: {WORK_START.strftime('%H:%M')} - {WORK_END.strftime('%H:%M')}")
    print(f"[{now_str()}] 💾 Headless режим: {'Да' if HEADLESS else 'Нет'}")
    print(f"[{now_str()}] 📊 Аккаунтов для обработки: {len(accounts)}")
    print(f"[{'='*50}]\n")
    
    while True:
        current_time = datetime.now(TBILISI_TZ)
        
        if is_working_time():
            cycle += 1
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] 🔄 ЦИКЛ #{cycle} НАЧАТ")
            print(f"[{'='*50}]\n")
            
            # Перемешиваем аккаунты для разнообразия
            random.shuffle(accounts)
            
            # Обрабатываем каждый аккаунт
            success_count = 0
            for account in accounts:
                if process_single_account(account, flaresolverr):
                    success_count += 1
                
                # Пауза между аккаунтами
                pause = random.randint(PAUSE_MIN, PAUSE_MAX)
                print(f"[{now_str()}] ⏸️ Пауза {pause} сек...")
                time.sleep(pause)
            
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] ✅ ЦИКЛ #{cycle} ЗАВЕРШЕН")
            print(f"[{now_str()}] 📈 Успешно обработано: {success_count}/{len(accounts)} аккаунтов")
            print(f"[{'='*50}]\n")
            
            # Большая пауза между циклами
            cycle_pause = random.randint(30, ROUND_PAUSE_MAX)
            print(f"[{now_str()}] ⏸️ Пауза между циклами {cycle_pause} сек...\n")
            time.sleep(cycle_pause)
            
            # Пересоздаем сессию каждые 3 цикла
            if FLARESOLVERR_ENABLED and USE_FLARESOLVERR_SESSIONS and cycle % 3 == 0:
                print(f"[{now_str()}] 🔄 Пересоздаем сессию FlareSolverr...")
                flaresolverr.destroy_session()
                time.sleep(2)
                flaresolverr.create_session()
                
        else:
            # Вне рабочего времени
            print(f"[{now_str()}] 😴 Вне рабочего времени. Следующая проверка через 5 мин...")
            
            # Уничтожаем сессию если есть
            if FLARESOLVERR_ENABLED and flaresolverr and flaresolverr.session_id:
                flaresolverr.destroy_session()
            
            time.sleep(300)  # 5 минут

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] ⏹️ Остановлено пользователем")
    except Exception as e:
        print(f"\n[{now_str()}] 💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Финальная очистка
        print(f"\n[{now_str()}] 🧹 Завершение работы...")
