
import os
import time
import random
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import requests
import json

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

# Настройки FlareSolverr
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191")
FLARESOLVERR_ENABLED = os.getenv("FLARESOLVERR_ENABLED", "true").lower() in ("1", "true", "yes")

# Настройки сайта
TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))
SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Паузы (увеличил для надежности)
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "8"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "15"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "45"))
ACTION_PAUSE_MIN = 2  # минимальная пауза между действиями
ACTION_PAUSE_MAX = 4  # максимальная пауза между действиями

# Таймауты (увеличил)
PAGE_LOAD_TIMEOUT = 30
ELEMENT_TIMEOUT = 20
LOGIN_TIMEOUT = 25

# Время работы
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
# FLARESOLVERR HELPER
# =========================
class FlareSolverrHelper:
    def __init__(self, flaresolverr_url):
        self.flaresolverr_url = flaresolverr_url
        self.session_id = None
        self.user_agent = None
        
    def is_available(self):
        """Проверяем доступность FlareSolverr"""
        try:
            response = requests.get(f"{self.flaresolverr_url}/health", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def create_session(self):
        """Создаем сессию"""
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
            return False
        except Exception as e:
            print(f"[{now_str()}] ❌ Ошибка создания сессии: {e}")
            return False
    
    def get_with_flaresolverr(self, url, max_timeout=60000):
        """Получаем страницу через FlareSolverr"""
        try:
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": max_timeout,
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
        """Удаляем сессию"""
        if self.session_id:
            try:
                payload = {"cmd": "sessions.destroy", "session": self.session_id}
                requests.post(f"{self.flaresolverr_url}/v1", json=payload, timeout=10)
            except:
                pass
            self.session_id = None

# Инициализируем FlareSolverr
flaresolverr = FlareSolverrHelper(FLARESOLVERR_URL) if FLARESOLVERR_ENABLED else None

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
    """Загружаем аккаунты ПО ПОРЯДКУ"""
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
    """Пауза как у человека"""
    time.sleep(random.uniform(min_sec, max_sec))

def random_mouse_movement(driver):
    """Случайные движения мыши для имитации человека"""
    try:
        script = """
        for(let i = 0; i < 5; i++) {
            let x = Math.random() * window.innerWidth;
            let y = Math.random() * window.innerHeight;
            let elem = document.elementFromPoint(x, y);
            if(elem) {
                let event = new MouseEvent('mousemove', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y
                });
                elem.dispatchEvent(event);
            }
        }
        """
        driver.execute_script(script)
        time.sleep(0.5)
    except:
        pass

# =========================
# BROWSER DRIVER
# =========================
def create_driver(use_flaresolverr=False, flaresolverr_helper=None):
    """Создаем драйвер браузера с автоматическим управлением версией"""
    options = uc.ChromeOptions()
    
    if HEADLESS:
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Если используем FlareSolverr, берем его User-Agent
    if use_flaresolverr and flaresolverr_helper and flaresolverr_helper.user_agent:
        options.add_argument(f"user-agent={flaresolverr_helper.user_agent}")
    else:
        # Стандартный User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={user_agent}")
    
    try:
        # Используем version_main=None чтобы undetected-chromedriver автоматически подобрал версию
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=None)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        # Убираем webdriver признаки
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": driver.execute_script("return navigator.userAgent")
        })
        
        return driver
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка создания драйвера: {e}")
        raise

def apply_flaresolverr_cookies(driver, solution):
    """Применяем куки от FlareSolverr"""
    try:
        cookies = solution.get("cookies", [])
        if not cookies:
            return False
        
        # Переходим на домен чтобы установить куки
        driver.get("https://43xgeorgia.me")
        time.sleep(2)
        
        for cookie in cookies:
            cookie_dict = {
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                'domain': cookie.get('domain', '.43xgeorgia.me'),
            }
            if 'path' in cookie:
                cookie_dict['path'] = cookie['path']
            if 'expiry' in cookie:
                cookie_dict['expiry'] = cookie['expiry']
            if 'secure' in cookie:
                cookie_dict['secure'] = cookie['secure']
            if 'httpOnly' in cookie:
                cookie_dict['httpOnly'] = cookie['httpOnly']
            
            try:
                driver.add_cookie(cookie_dict)
            except Exception as e:
                continue
        
        print(f"[{now_str()}] 🍪 Применено куки: {len(cookies)}")
        return True
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка применения куки: {e}")
        return False

def pass_18plus_protection(driver):
    """Обход 18+ защиты"""
    try:
        human_pause(2, 3)
        
        # Ищем кнопку или чекбокс
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "input[type='checkbox']",
            "button.btn",
            "//button[contains(text(), 'Да')]",
            "//button[contains(text(), 'Войти')]",
            "//input[@type='checkbox']"
        ]
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    elem = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                else:
                    elem = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                
                random_mouse_movement(driver)
                human_pause(1, 2)
                elem.click()
                print(f"[{now_str()}] ✅ 18+ защита пройдена")
                human_pause(3, 4)
                return True
            except:
                continue
        
        print(f"[{now_str()}] ℹ️ 18+ защита не обнаружена или уже пройдена")
        return False
        
    except Exception as e:
        print(f"[{now_str()}] ⚠️ Ошибка обхода 18+: {e}")
        return False

def do_login(driver, acc):
    """Логин"""
    try:
        print(f"[{now_str()}] 🔑 Выполняем логин: {acc['login']}")
        
        # Ищем поле логина
        login_field = None
        login_selectors = [
            "#user_login",
            "input[name='log']",
            "input[type='text']",
            "input[id*='login']",
            "input[name*='username']"
        ]
        
        for sel in login_selectors:
            try:
                login_field = WebDriverWait(driver, LOGIN_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                break
            except:
                continue
        
        if not login_field:
            print(f"[{now_str()}] ❌ Не найдено поле логина")
            return False
        
        # Заполняем логин
        random_mouse_movement(driver)
        human_pause(1, 2)
        login_field.clear()
        for char in acc["login"]:
            login_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        # Ищем поле пароля
        pass_field = None
        pass_selectors = [
            "#user_pass",
            "input[name='pwd']",
            "input[type='password']",
            "input[id*='pass']",
            "input[name*='password']"
        ]
        
        for sel in pass_selectors:
            try:
                pass_field = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                break
            except:
                continue
        
        if not pass_field:
            print(f"[{now_str()}] ❌ Не найдено поле пароля")
            return False
        
        # Заполняем пароль
        random_mouse_movement(driver)
        human_pause(1, 2)
        pass_field.clear()
        for char in acc["password"]:
            pass_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        # Ищем кнопку входа
        submit_btn = None
        submit_selectors = [
            "#wp-submit",
            "input[type='submit']",
            "button[type='submit']",
            "input[value*='Войти']",
            "button[value*='Войти']",
            "input[name='wp-submit']"
        ]
        
        for sel in submit_selectors:
            try:
                submit_btn = WebDriverWait(driver, ELEMENT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                break
            except:
                continue
        
        if not submit_btn:
            print(f"[{now_str()}] ❌ Не найдена кнопка входа")
            return False
        
        # Кликаем
        random_mouse_movement(driver)
        human_pause(1, 2)
        submit_btn.click()
        print(f"[{now_str()}] ✅ Форма отправлена, ждем...")
        
        # Ждем загрузки
        human_pause(5, 7)
        
        # Проверяем успешность логина
        current_url = driver.current_url
        if "wp-login" not in current_url or "login" not in current_url:
            print(f"[{now_str()}] ✅ Логин успешен")
            return True
        else:
            print(f"[{now_str()}] ⚠️ Возможно, логин не удался")
            return False
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка логина: {e}")
        return False

def do_up(driver, acc):
    """Выполняем UP"""
    try:
        print(f"[{now_str()}] 🔼 Ищем кнопку UP...")
        human_pause(3, 5)
        
        # Разные селекторы для кнопки UP
        selectors = [
            "a.k-up.send",
            "a[class*='k-up']",
            "a[class*='up-btn']",
            "a[href*='?up=']",
            "a[onclick*='up']",
            "//a[contains(text(), 'UP') or contains(text(), 'Up') or contains(@class, 'up')]"
        ]
        
        for sel in selectors:
            try:
                if sel.startswith("//"):
                    up_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, sel))
                    )
                else:
                    up_link = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                
                # Прокручиваем и кликаем
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", up_link)
                random_mouse_movement(driver)
                human_pause(1, 2)
                
                href = up_link.get_attribute("href")
                if href:
                    # Переходим по ссылке если есть
                    driver.get(href)
                    print(f"[{now_str()}] 🎉 UP выполнен через переход по ссылке")
                else:
                    # Кликаем если нет ссылки
                    up_link.click()
                    print(f"[{now_str()}] 🎉 UP выполнен через клик")
                
                human_pause(3, 5)
                return True
                
            except Exception as e:
                continue
        
        print(f"[{now_str()}] ⚠️ Кнопка UP не найдена")
        return False
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка при UP: {e}")
        return False

def do_logout(driver):
    """Логаут"""
    try:
        logout_url = "https://43xgeorgia.me/wp-login.php?action=logout"
        driver.get(logout_url)
        human_pause(3, 5)
        return True
    except:
        return False

# =========================
# MAIN PROCESS
# =========================
def process_account(acc, account_index, total_accounts):
    """Обработка аккаунта ПО ПОРЯДКУ"""
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 🔄 Обрабатываем аккаунт #{acc['number']} ({account_index}/{total_accounts}): {acc['login']}")
    print(f"{'='*50}")
    
    driver = None
    try:
        # Создаем драйвер
        print(f"[{now_str()}] 🌐 Создаем браузер...")
        driver = create_driver()
        human_pause(2, 3)
        
        # Используем FlareSolverr если включен
        if FLARESOLVERR_ENABLED and flaresolverr and flaresolverr.session_id:
            print(f"[{now_str()}] 🎯 Используем FlareSolverr...")
            
            # Получаем главную страницу через FlareSolverr
            solution = flaresolverr.get_with_flaresolverr(SITE_URL)
            if solution:
                print(f"[{now_str()}] ✅ FlareSolverr получил страницу")
                
                # Применяем куки
                if not apply_flaresolverr_cookies(driver, solution):
                    print(f"[{now_str()}] ⚠️ Не удалось применить куки, продолжаем без них")
                
                # Обновляем страницу
                driver.get(SITE_URL)
                human_pause(4, 6)
            else:
                print(f"[{now_str()}] ⚠️ FlareSolverr не сработал, продолжаем стандартно")
                driver.get(SITE_URL)
                human_pause(5, 7)
        else:
            # Стандартный переход
            driver.get(SITE_URL)
            human_pause(5, 7)
        
        # 18+ защита
        pass_18plus_protection(driver)
        
        # Логин
        if not do_login(driver, acc):
            print(f"[{now_str()}] ❌ Ошибка логина, пропускаем аккаунт")
            return
        
        # UP
        if do_up(driver, acc):
            print(f"[{now_str()}] ✅ UP успешно выполнен")
            human_pause(2, 4)
        else:
            print(f"[{now_str()}] ⚠️ UP не удался")
        
        # Логаут
        do_logout(driver)
        print(f"[{now_str()}] ✅ Аккаунт #{acc['number']} обработан!")
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Критическая ошибка: {e}")
        
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
            print(f"[{now_str()}] ⏸️ Пауза {pause} сек до следующего аккаунта...")
            time.sleep(pause)

# =========================
# MAIN FUNCTION
# =========================
def main():
    print(f"\n{'='*60}")
    print(f"[{now_str()}] 🚀 ЗАПУСК UPBOT + FLARESOLVERR (AUTO-VERSION)")
    print(f"{'='*60}")
    
    # Проверяем FlareSolverr
    if FLARESOLVERR_ENABLED:
        print(f"[{now_str()}] 🔗 Проверяем FlareSolverr...")
        if flaresolverr and flaresolverr.is_available():
            print(f"[{now_str()}] ✅ FlareSolverr доступен")
            
            # Создаем сессию
            if flaresolverr.create_session():
                print(f"[{now_str()}] ✅ Сессия создана")
            else:
                print(f"[{now_str()}] ⚠️ Не удалось создать сессию, работаем без FlareSolverr")
        else:
            print(f"[{now_str()}] ❌ FlareSolverr недоступен, работаем без него")
    else:
        print(f"[{now_str()}] ℹ️ FlareSolverr отключен")
    
    # Загружаем аккаунты
    try:
        accounts = load_accounts()
        print(f"[{now_str()}] 📋 Загружено аккаунтов: {len(accounts)}")
        
        # Показываем порядок аккаунтов
        print(f"\n[{'='*50}]")
        print(f"[{now_str()}] ⏰ Режим работы: {WORK_START.strftime('%H:%M')} - {WORK_END.strftime('%H:%M')}")
        print(f"[{now_str()}] 💾 Headless режим: {'Да' if HEADLESS else 'Нет'}")
        print(f"[{now_str()}] 📊 Аккаунтов для обработки: {len(accounts)} ПО ПОРЯДКУ")
        print(f"[{'='*50}]\n")
        
    except Exception as e:
        print(f"[{now_str()}] ❌ Ошибка загрузки аккаунтов: {e}")
        return
    
    cycle_count = 0
    
    while True:
        if is_working_time():
            cycle_count += 1
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] 🔄 ЦИКЛ #{cycle_count} НАЧАТ")
            print(f"[{'='*50}]\n")
            
            # Обрабатываем аккаунты ПО ПОРЯДКУ
            for i, account in enumerate(accounts, 1):
                process_account(account, i, len(accounts))
            
            print(f"\n[{'='*50}]")
            print(f"[{now_str()}] ✅ ЦИКЛ #{cycle_count} ЗАВЕРШЕН")
            print(f"[{'='*50}]\n")
            
            # Пауза между циклами
            pause = random.randint(ROUND_PAUSE_MAX // 2, ROUND_PAUSE_MAX)
            print(f"[{now_str()}] ⏸️ Пауза {pause} сек до следующего цикла...")
            time.sleep(pause)
            
        else:
            print(f"[{now_str()}] ⏰ Вне времени работы, ждем 5 минут...")
            time.sleep(300)

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now_str()}] ⏹️ Остановлено пользователем")
        
        # Уничтожаем сессию FlareSolverr
        if FLARESOLVERR_ENABLED and flaresolverr:
            flaresolverr.destroy_session()
            
        print(f"[{now_str()}] 🧹 Завершение работы...")
        
    except Exception as e:
        print(f"\n[{now_str()}] ❌ Критическая ошибка: {e}")
        
        # Уничтожаем сессию FlareSolverr
        if FLARESOLVERR_ENABLED and flaresolverr:
            flaresolverr.destroy_session()
