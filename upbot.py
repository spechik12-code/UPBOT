#!/usr/bin/env python3
"""
Основной бот с поддержкой прокси и FlareSolverr
"""
import os
import sys
import time
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Добавляем путь к текущей директории
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    SITE_URL, TBILISI_TZ, PAUSE_MIN, PAUSE_MAX, ROUND_PAUSE_MAX,
    WORK_START, WORK_END, HEADLESS,
    FLARESOLVERR_URL, FLARESOLVERR_ENABLED, USE_FLARESOLVERR_SESSIONS,
    get_proxy, get_proxies_dict, PROXY_LIST
)
from proxy_utils import get_working_proxy, health_check_proxies
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
import json
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/bots/UPBOT/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка аккаунтов из .env
load_dotenv()
ACCOUNTS = []
for i in range(1, 10):
    login = os.getenv(f'ACC{i}_LOGIN')
    password = os.getenv(f'ACC{i}_PASS')
    if login and password:
        ACCOUNTS.append({
            'login': login,
            'password': password,
            'index': i
        })

logger.info(f"Загружено аккаунтов: {len(ACCOUNTS)}")
logger.info(f"Настроено прокси: {len(PROXY_LIST)}")

class FlareSolverrClient:
    """Клиент для работы с FlareSolverr"""
    
    def __init__(self, base_url=FLARESOLVERR_URL):
        self.base_url = base_url
        self.session = None
        self.session_id = None
        
    def create_session(self):
        """Создать сессию в FlareSolverr"""
        if not FLARESOLVERR_ENABLED:
            return None
            
        try:
            payload = {
                "cmd": "sessions.create",
                "session": f"upbot_{int(time.time())}"
            }
            
            # Используем прокси если есть
            proxies = None
            if PROXY_LIST and FLARESOLVERR_ENABLED:
                proxy_url = get_working_proxy()
                if proxy_url:
                    proxies = get_proxies_dict(proxy_url)
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=30,
                proxies=proxies
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    self.session_id = data['session']
                    self.session = data['session']
                    logger.info(f"Создана сессия FlareSolverr: {self.session_id}")
                    return self.session_id
                else:
                    logger.error(f"Ошибка создания сессии: {data.get('message')}")
            else:
                logger.error(f"HTTP ошибка: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка создания сессии FlareSolverr: {e}")
        
        return None
    
    def solve(self, url, max_timeout=60000):
        """Решить капчу/получить страницу через FlareSolverr"""
        if not FLARESOLVERR_ENABLED:
            return None
            
        if not self.session_id and USE_FLARESOLVERR_SESSIONS:
            self.create_session()
        
        try:
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": max_timeout,
            }
            
            if self.session_id and USE_FLARESOLVERR_SESSIONS:
                payload["session"] = self.session_id
            
            # Используем прокси
            proxies = None
            if PROXY_LIST:
                proxy_url = get_working_proxy()
                if proxy_url:
                    proxies = get_proxies_dict(proxy_url)
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=90,
                proxies=proxies
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    logger.info(f"FlareSolverr успешно получил страницу: {url}")
                    return data['solution']
                else:
                    logger.warning(f"FlareSolverr ошибка: {data.get('message')}")
            else:
                logger.error(f"HTTP ошибка FlareSolverr: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ошибка FlareSolverr: {e}")
        
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
            except:
                pass
            self.session_id = None

class UpBot:
    """Основной класс бота"""
    
    def __init__(self, account, use_proxy=True):
        self.account = account
        self.use_proxy = use_proxy
        self.driver = None
        self.flaresolverr = FlareSolverrClient() if FLARESOLVERR_ENABLED else None
        self.current_proxy = None
        
    def setup_driver(self):
        """Настройка ChromeDriver с прокси"""
        options = uc.ChromeOptions()
        
        if HEADLESS:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # User-Agent
        from config import CUSTOM_USER_AGENT
        if CUSTOM_USER_AGENT:
            options.add_argument(f'--user-agent={CUSTOM_USER_AGENT}')
        
        # Настройки для обхода детекции
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Прокси настройки
        if self.use_proxy and PROXY_LIST:
            self.current_proxy = get_working_proxy()
            if self.current_proxy:
                logger.info(f"Используем прокси: {self.current_proxy[:50]}...")
                
                # Для undetected-chromedriver добавляем прокси как аргумент
                if 'http://' in self.current_proxy:
                    # Извлекаем хост и порт из URL с аутентификацией
                    proxy_url = self.current_proxy
                    if '@' in proxy_url:
                        # Формат: http://user:pass@host:port
                        proxy_url = proxy_url.replace('http://', '')
                        credentials, hostport = proxy_url.split('@')
                        options.add_argument(f'--proxy-server={hostport}')
                        # Для аутентификации может потребоваться расширение
                    else:
                        options.add_argument(f'--proxy-server={proxy_url.replace("http://", "")}')
        
        try:
            self.driver = uc.Chrome(
                options=options,
                version_main=120  # Укажите версию Chrome
            )
            
            # Скрываем WebDriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("ChromeDriver успешно запущен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска ChromeDriver: {e}")
            return False
    
    def login_with_flaresolverr(self):
        """Вход через FlareSolverr"""
        if not self.flaresolverr:
            return False
            
        try:
            solution = self.flaresolverr.solve(SITE_URL)
            if solution and 'response' in solution:
                # Здесь можно обработать ответ от FlareSolverr
                # Например, извлечь cookies и использовать их
                logger.info("Получен ответ от FlareSolverr")
                
                # Если FlareSolverr вернул cookies, можно установить их
                if 'cookies' in solution:
                    # Устанавливаем cookies в драйвер
                    self.driver.get(SITE_URL)
                    for cookie in solution['cookies']:
                        self.driver.add_cookie(cookie)
                    
                    # Обновляем страницу с cookies
                    self.driver.get(SITE_URL)
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Ошибка FlareSolverr: {e}")
            return False
    
    def manual_login(self):
        """Ручной вход через Selenium"""
        try:
            self.driver.get(SITE_URL)
            logger.info(f"Загружена страница: {SITE_URL}")
            
            # Ждем появления формы входа
            wait = WebDriverWait(self.driver, 20)
            
            # Ищем поле логина
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                username_field.send_keys(self.account['login'])
                logger.info("Введен логин")
            except:
                # Пробуем другие селекторы
                selectors = [
                    (By.ID, "username"),
                    (By.NAME, "email"),
                    (By.ID, "email"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[type='email']")
                ]
                
                for by, selector in selectors:
                    try:
                        elem = self.driver.find_element(by, selector)
                        elem.send_keys(self.account['login'])
                        logger.info(f"Логин введен через селектор {by}: {selector}")
                        break
                    except:
                        continue
            
            # Ищем поле пароля
            try:
                password_field = self.driver.find_element(By.NAME, "password")
                password_field.send_keys(self.account['password'])
                logger.info("Введен пароль")
            except:
                selectors = [
                    (By.ID, "password"),
                    (By.CSS_SELECTOR, "input[type='password']")
                ]
                
                for by, selector in selectors:
                    try:
                        elem = self.driver.find_element(by, selector)
                        elem.send_keys(self.account['password'])
                        logger.info(f"Пароль введен через селектор {by}: {selector}")
                        break
                    except:
                        continue
            
            # Ищем кнопку входа
            try:
                login_button = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    "button[type='submit'], input[type='submit']"
                )
                login_button.click()
                logger.info("Нажата кнопка входа")
            except:
                # Пробуем нажать Enter в поле пароля
                password_field.submit()
                logger.info("Отправлена форма через submit")
            
            # Ждем успешного входа
            time.sleep(5)
            
            # Проверяем успешность входа
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                logger.info(f"Вход успешен! Текущий URL: {current_url}")
                return True
            else:
                logger.warning("Возможно не удалось войти")
                # Делаем скриншот для отладки
                try:
                    screenshot_path = f"/tmp/login_error_acc{self.account['index']}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"Скриншот сохранен: {screenshot_path}")
                except:
                    pass
                
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при входе: {e}")
            return False
    
    def perform_actions(self):
        """Выполнить действия после входа"""
        try:
            # Пауза перед действиями
            time.sleep(random.randint(PAUSE_MIN, PAUSE_MAX))
            
            # Здесь добавляйте нужные действия
            # Например: проверка баланса, размещение объявлений и т.д.
            
            logger.info(f"Аккаунт {self.account['index']}: действия выполнены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении действий: {e}")
            return False
    
    def run(self):
        """Запуск бота для одного аккаунта"""
        logger.info(f"Запуск для аккаунта {self.account['index']}: {self.account['login']}")
        
        try:
            # Настройка драйвера
            if not self.setup_driver():
                return False
            
            # Попытка входа через FlareSolverr если включен
            login_success = False
            if FLARESOLVERR_ENABLED and self.flaresolverr:
                logger.info("Пробуем вход через FlareSolverr...")
                login_success = self.login_with_flaresolverr()
            
            # Если FlareSolverr не сработал, пробуем ручной вход
            if not login_success:
                logger.info("Пробуем ручной вход...")
                login_success = self.manual_login()
            
            if login_success:
                # Выполняем действия
                self.perform_actions()
                
                # Пауза перед выходом
                pause = random.randint(ROUND_PAUSE_MAX // 2, ROUND_PAUSE_MAX)
                logger.info(f"Пауза {pause} секунд перед выходом...")
                time.sleep(pause)
                
                return True
            else:
                logger.warning(f"Не удалось войти в аккаунт {self.account['index']}")
                return False
                
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            return False
            
        finally:
            # Закрываем драйвер
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("ChromeDriver закрыт")
                except:
                    pass
            
            # Закрываем сессию FlareSolverr
            if self.flaresolverr:
                self.flaresolverr.destroy_session()

def is_working_hours():
    """Проверка рабочего времени"""
    now_tbilisi = datetime.now(TBILISI_TZ).time()
    
    # Если время конца больше времени начала (нормальный интервал)
    if WORK_END > WORK_START:
        return WORK_START <= now_tbilisi <= WORK_END
    else:
        # Интервал пересекает полночь
        return now_tbilisi >= WORK_START or now_tbilisi <= WORK_END

def main():
    """Основная функция"""
    logger.info("=" * 50)
    logger.info("ЗАПУСК UPBOT")
    logger.info(f"Время в Тбилиси: {datetime.now(TBILISI_TZ).strftime('%H:%M:%S')}")
    logger.info(f"Рабочие часы: {WORK_START.strftime('%H:%M')} - {WORK_END.strftime('%H:%M')}")
    logger.info(f"Аккаунтов: {len(ACCOUNTS)}")
    logger.info(f"Прокси: {len(PROXY_LIST)}")
    logger.info(f"FlareSolverr: {'ВКЛ' if FLARESOLVERR_ENABLED else 'ВЫКЛ'}")
    logger.info("=" * 50)
    
    # Проверка рабочего времени
    if not is_working_hours():
        logger.info("Сейчас не рабочее время. Выход.")
        return
    
    # Проверка здоровья прокси
    if PROXY_LIST:
        working_proxies = health_check_proxies()
        if not working_proxies:
            logger.warning("Нет рабочих прокси! Будет использоваться прямое соединение.")
    
    # Запуск для каждого аккаунта
    for account in ACCOUNTS:
        logger.info(f"\nОбработка аккаунта {account['index']}")
        
        bot = UpBot(account, use_proxy=True)
        success = bot.run()
        
        if success:
            logger.info(f"✅ Аккаунт {account['index']} успешно обработан")
        else:
            logger.warning(f"⚠️  Аккаунт {account['index']} не обработан")
        
        # Пауза между аккаунтами
        if account != ACCOUNTS[-1]:
            pause = random.randint(ROUND_PAUSE_MAX // 2, ROUND_PAUSE_MAX)
            logger.info(f"Пауза {pause} секунд перед следующим аккаунтом...")
            time.sleep(pause)
    
    logger.info("\n" + "=" * 50)
    logger.info("ВСЕ АККАУНТЫ ОБРАБОТАНЫ")
    logger.info("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nБот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
