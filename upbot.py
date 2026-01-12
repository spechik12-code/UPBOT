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
    
    try:
        # Очищаем старые куки
        driver.delete_all_cookies()
        
        # Устанавливаем User-Agent
        user_agent = flaresolverr_result.get("user_agent")
        if user_agent:
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": user_agent
            })
        
        # Добавляем все куки
        success_count = 0
        for cookie in cookies:
            try:
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.43xgeorgia.me'),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False),
                    'httpOnly': cookie.get('httpOnly', False)
                }
                
                if 'expires' in cookie:
                    cookie_dict['expiry'] = int(cookie['expires'])
                
                driver.add_cookie(cookie_dict)
                success_count += 1
            except:
                continue
        
        print(f"[{now_str()}] 🍪 Применено кук: {success_count}/{len(cookies)}")
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
        return False
    
    # Загружаем HTML
    driver.get("about:blank")
    html = result.get("html", "")
    if html:
        try:
            # Экранируем обратные кавычки
            safe_html = html.replace('`', '\\`').replace('${', '\\${')
            driver.execute_script(f"""
                document.open();
                document.write(`{safe_html}`);
                document.close();
            """)
            time.sleep(2)
        except Exception as e:
            print(f"[{now_str()}] ⚠️ Ошибка загрузки HTML: {e}")
    
    # Применяем куки и обновляем
    if apply_flaresolverr_cookies(driver, result):
        driver.refresh()
        time.sleep(3)
        return True
    
    return False

def handle_18plus(driver):
    """Обработка 18+ защиты"""
    try:
        elements = driver.find_elements(By.XPATH, 
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'click') or "
            "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue') or "
            "contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'продолж') or "
            "contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'наж')]"
        )
        
        for elem in elements:
            if elem.is_displayed():
                driver.execute_script("arguments[0].click();", elem)
                print(f"[{now_str()}] ✅ 18+ защита пройдена")
                time.sleep(2)
                return True
    except:
        pass
    
    return False

def login_to_site(driver, account):
    """Логин на сайте"""
    try:
        # Переходим на страницу логина
        driver.get("https://43xgeorgia.me/wp-login.php")
        time.sleep(3)
        
        # Поле логина
        username = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_login"))
        )
        username.clear()
        
        # Человекоподобный ввод
        for char in account['login']:
            username.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(0.5, 1))
        
        # Поле пароля
        password = driver.find_element(By.ID, "user_pass")
        password.clear()
        for char in account['password']:
            password.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(random.uniform(0.5, 1))
        
        # Кнопка входа
        submit = driver.find_element(By.ID, "wp-submit")
        submit.click()
        
        # Ждем и проверяем результат
        time.sleep(5)
        
        if "wp-admin" in driver.current_url or "profile.php" in driver.current_url:
            print(f"[{now_str()}] ✅ Успешный логин: {account['login']}")
            return True
        else:
            # Проверяем есть ли ошибка
            try:
                error_div = driver.find_element(By.ID, "login_error")
                if error_div:
                    print(f"[{now_str()}] ❌ Ошибка логина: {error_div.text[:100]}")
            except:
                print(f"[{now_str()}] ⚠️ Неизвестная ошибка логина")
            
            return False
            
    except Exception as e:
        print(f"[{now_str()}] ❌ Исключение при логине: {e}")
        return False

def perform_up(driver, account):
    """Выполняем UP действие"""
    selectors = [
        "a.k-up.send",
        "a[class*='k-up'][class*='send']",
        "a.up-btn",
        "a[href*='?up=1']",
        "//a[contains(@class, 'up')]",
        "//button[contains(@class, 'up')]",
        "//*[contains(text(), 'UP') or contains(text(), 'Up')]",
    ]
    
    for selector in selectors:
        try:
            if selector.startswith("//"):
                element = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
            else:
                element = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
            
            # Кликаем
            href = element.get_attribute("href")
            if href:
                driver.get(href)
            else:
                driver.execute_script("arguments[0].click();", element)
            
            print(f"[{now_str()}] 🎯 UP выполнен для {account['login']}")
            time.sleep(3)
            return True
            
        except:
            continue
    
    print(f"[{now_str()}] ⚠️ UP не найден для {account['login']}")
    return False

def logout(driver):
    """Выход из аккаунта"""
    try:
        driver.get("https://43xgeorgia.me/wp-login.php?action=logout")
        time.sleep(2)
        
        # Ищем ссылку подтверждения выхода
        try:
            confirm = driver.find_element(By.LINK_TEXT, "log out")
            if confirm:
                confirm.click()
        except:
            pass
            
        print(f"[{now_str()}] 👋 Выход выполнен")
        return True
    except:
        return False

# =========================
# ACCOUNT PROCESSING
# =========================
def process_single_account(account, flaresolverr):
    """Обработка одного аккаунта"""
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 🔄 Обрабатываем аккаунт #{account['id']}: {account['login']}")
    
    driver = None
    try:
        # 1. Создаем драйвер
        driver = create_driver()
        
        # 2. Получаем главную страницу через FlareSolverr
        if not navigate_with_flaresolverr(driver, flaresolverr, SITE_URL):
            print(f"[{now_str()}] ❌ Не удалось обойти защиту")
            return False
        
        # 3. Обрабатываем 18+
        handle_18plus(driver)
        
        # 4. Логин
        if not login_to_site(driver, account):
            return False
        
        # 5. Выполняем UP
        perform_up(driver, account)
        
        # 6. Выход
        logout(driver)
        
        print(f"[{now_str()}] ✅ Аккаунт #{account['id']} успешно обработан!")
        return True
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Критическая ошибка: {e}")
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
    print(f"[{now_str()}] 🚀 ЗАПУСК UPBOT + FLARESOLVERR")
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
    print(f"[{'='*50}]\n")
    
    while True:
        current_time = datetime.now(TBILISI_TZ)
        
        if is_working_time():
            cycle += 1
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] 🔄 ЦИКЛ #{cycle} НАЧАТ")
            print(f"[{'='*50}]\n")
            
            # Перемешиваем аккаунты
            random.shuffle(accounts)
            
            # Обрабатываем каждый аккаунт
            for account in accounts:
                process_single_account(account, flaresolverr)
                
                # Пауза между аккаунтами
                pause = random.randint(PAUSE_MIN, PAUSE_MAX)
                print(f"[{now_str()}] ⏸️ Пауза {pause} сек...")
                time.sleep(pause)
            
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] ✅ ЦИКЛ #{cycle} ЗАВЕРШЕН")
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