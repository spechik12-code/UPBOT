#!/usr/bin/env python3
"""
Основной бот - использует FlareSolverr как основной метод
"""
import os
import sys
import time
import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    SITE_URL, TBILISI_TZ, PAUSE_MIN, PAUSE_MAX, ROUND_PAUSE_MAX,
    WORK_START, WORK_END, HEADLESS,
    FLARESOLVERR_URL, FLARESOLVERR_ENABLED, USE_FLARESOLVERR_SESSIONS,
    USE_DIRECT_PROXY, PROXY_LIST
)
from flaresolverr_client import AdvancedFlareSolverrClient
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import json
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка аккаунтов из .env
load_dotenv()
ACCOUNTS = []
for i in range(1, 20):
    login = os.getenv(f'ACC{i}_LOGIN')
    password = os.getenv(f'ACC{i}_PASS')
    if login and password:
        ACCOUNTS.append({
            'login': login,
            'password': password,
            'index': i
        })

logger.info(f"Загружено аккаунтов: {len(ACCOUNTS)}")
logger.info(f"Настроено прокси для FlareSolverr: {len(PROXY_LIST)}")
logger.info(f"FlareSolverr основной метод: {'ДА' if FLARESOLVERR_ENABLED else 'НЕТ'}")

class UpBot:
    """Основной класс бота с FlareSolverr как основным методом"""
    
    def __init__(self, account):
        self.account = account
        self.driver = None
        self.flaresolverr = AdvancedFlareSolverrClient() if FLARESOLVERR_ENABLED else None
        
    def setup_driver_no_proxy(self):
        """Настройка ChromeDriver БЕЗ прокси (так как сайт блокирует прокси)"""
        options = uc.ChromeOptions()
        
        if HEADLESS:
            options.add_argument('--headless=new')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        from config import CUSTOM_USER_AGENT
        if CUSTOM_USER_AGENT:
            options.add_argument(f'--user-agent={CUSTOM_USER_AGENT}')
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = uc.Chrome(
                options=options,
                version_main=120
            )
            
            # Скрываем WebDriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("ChromeDriver успешно запущен (без прокси)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска ChromeDriver: {e}")
            return False
    
    def login_via_flaresolverr_cookies(self):
        """Вход через FlareSolverr с передачей cookies в Selenium"""
        if not self.flaresolverr:
            logger.warning("FlareSolverr отключен, пробуем прямой вход")
            return False
        
        try:
            logger.info("Получаем страницу через FlareSolverr...")
            solution = self.flaresolverr.solve_with_proxy_rotation(SITE_URL)
            
            if not solution:
                logger.error("FlareSolverr не вернул решение")
                return False
            
            status = solution.get('status', 0)
            if status != 200:
                logger.warning(f"FlareSolverr вернул статус {status}")
                return False
            
            # Получаем cookies от FlareSolverr
            cookies = solution.get('cookies', [])
            user_agent = solution.get('userAgent', '')
            
            if not cookies:
                logger.warning("FlareSolverr не вернул cookies")
                return False
            
            logger.info(f"Получено {len(cookies)} cookies от FlareSolverr")
            
            # 1. Устанавливаем User-Agent если есть
            if user_agent:
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": user_agent
                })
            
            # 2. Открываем сайт
            self.driver.get(SITE_URL)
            time.sleep(2)
            
            # 3. Устанавливаем все cookies
            for cookie in cookies:
                try:
                    # Приводим cookie к формату Selenium
                    selenium_cookie = {
                        'name': cookie.get('name', ''),
                        'value': cookie.get('value', ''),
                        'domain': cookie.get('domain', ''),
                        'path': cookie.get('path', '/')
                    }
                    
                    # Добавляем дополнительные поля если есть
                    if 'expires' in cookie:
                        selenium_cookie['expiry'] = cookie['expires']
                    if 'httpOnly' in cookie:
                        selenium_cookie['httpOnly'] = cookie['httpOnly']
                    if 'secure' in cookie:
                        selenium_cookie['secure'] = cookie['secure']
                    
                    self.driver.add_cookie(selenium_cookie)
                except Exception as e:
                    logger.debug(f"Ошибка добавления cookie: {e}")
            
            logger.info(f"Cookies установлены")
            
            # 4. Обновляем страницу с cookies
            self.driver.get(SITE_URL)
            time.sleep(3)
            
            # 5. Проверяем успешность
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            # Проверяем что мы не на странице входа
            if "login" not in current_url.lower() and "auth" not in current_url.lower():
                logger.info(f"✅ Успешный вход через FlareSolverr cookies!")
                return True
            else:
                # Проверяем может быть нужно заполнить форму
                logger.info("Возможно нужно заполнить форму входа...")
                return self.fill_login_form()
                
        except Exception as e:
            logger.error(f"Ошибка входа через FlareSolverr: {e}")
            return False
    
    def fill_login_form(self):
        """Заполнить форму входа если cookies недостаточно"""
        try:
            logger.info("Заполняем форму входа...")
            
            # Ищем поле логина
            selectors = [
                (By.NAME, "username"),
                (By.ID, "username"),
                (By.NAME, "email"),
                (By.ID, "email"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[type='email']")
            ]
            
            username_field = None
            for by, selector in selectors:
                try:
                    username_field = self.driver.find_element(by, selector)
                    logger.info(f"Найдено поле логина: {by}={selector}")
                    break
                except:
                    continue
            
            if not username_field:
                logger.warning("Не найдено поле логина")
                return False
            
            # Вводим логин
            username_field.clear()
            username_field.send_keys(self.account['login'])
            time.sleep(1)
            
            # Ищем поле пароля
            password_field = None
            for by, selector in [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]:
                try:
                    password_field = self.driver.find_element(by, selector)
                    logger.info(f"Найдено поле пароля: {by}={selector}")
                    break
                except:
                    continue
            
            if not password_field:
                logger.warning("Не найдено поле пароля")
                return False
            
            # Вводим пароль
            password_field.clear()
            password_field.send_keys(self.account['password'])
            time.sleep(1)
            
            # Ищем кнопку отправки
            for by, selector in [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button"),
                (By.CSS_SELECTOR, "input[value='Войти']"),
                (By.CSS_SELECTOR, "input[value='Login']")
            ]:
                try:
                    submit_button = self.driver.find_element(by, selector)
                    submit_button.click()
                    logger.info(f"Нажата кнопка: {by}={selector}")
                    break
                except:
                    continue
            
            time.sleep(5)
            
            # Проверяем результат
            current_url = self.driver.current_url
            if "login" not in current_url.lower() and "auth" not in current_url.lower():
                logger.info(f"✅ Успешный вход после заполнения формы!")
                return True
            else:
                logger.warning("Вход не удался после заполнения формы")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка заполнения формы: {e}")
            return False
    
    def perform_actions(self):
        """Выполнить действия после входа"""
        try:
            time.sleep(random.randint(PAUSE_MIN, PAUSE_MAX))
            
            # Здесь твоя логика действий
            # Например: проверка баланса, размещение объявлений и т.д.
            
            logger.info(f"Аккаунт {self.account['index']}: базовые действия выполнены")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении действий: {e}")
            return False
    
    def run(self):
        """Запуск бота для одного аккаунта"""
        logger.info(f"Запуск для аккаунта {self.account['index']}: {self.account['login']}")
        
        try:
            # Настройка драйвера (БЕЗ прокси!)
            if not self.setup_driver_no_proxy():
                return False
            
            # Пытаемся войти через FlareSolverr
            login_success = False
            
            if FLARESOLVERR_ENABLED and self.flaresolverr:
                logger.info("Пытаемся вход через FlareSolverr...")
                login_success = self.login_via_flaresolverr_cookies()
            
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
    
    if WORK_END > WORK_START:
        return WORK_START <= now_tbilisi <= WORK_END
    else:
        return now_tbilisi >= WORK_START or now_tbilisi <= WORK_END

def main():
    """Основная функция"""
    logger.info("=" * 50)
    logger.info("ЗАПУСК UPBOT (FlareSolverr + прокси)")
    logger.info(f"Время в Тбилиси: {datetime.now(TBILISI_TZ).strftime('%H:%M:%S')}")
    logger.info(f"Рабочие часы: {WORK_START.strftime('%H:%M')} - {WORK_END.strftime('%H:%M')}")
    logger.info(f"Аккаунтов: {len(ACCOUNTS)}")
    logger.info(f"Прокси для FlareSolverr: {len(PROXY_LIST)}")
    logger.info("=" * 50)
    
    # Проверка рабочего времени
    if not is_working_hours():
        logger.info("Сейчас не рабочее время. Выход.")
        return
    
    # Запуск для каждого аккаунта
    for account in ACCOUNTS:
        logger.info(f"\nОбработка аккаунта {account['index']}")
        
        bot = UpBot(account)
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
