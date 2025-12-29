import time
import random
import os
import subprocess
import platform
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import schedule
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

load_dotenv()

SITE_URL = os.getenv('SITE_URL', 'https://43xgeorgia.me/ru')

accounts = []
i = 1
while True:
    login = os.getenv(f'ACC{i}_LOGIN')
    password = os.getenv(f'ACC{i}_PASS')
    if login and password:
        accounts.append({'login': login, 'pass': password})
        i += 1
    else:
        break

if not accounts:
    print("ОШИБКА: Нет аккаунтов!")
    exit()

print(f"Загружено {len(accounts)} аккаунтов. Финальная версия с фиксами для сервера.")

TBILISI_TZ = ZoneInfo('Asia/Tbilisi')

def is_working_time():
    now = datetime.now(TBILISI_TZ)
    start = dtime(15, 0)
    end = dtime(6, 0)
    if start <= end:
        return start <= now.time() <= end
    else:
        return now.time() >= start or now.time() <= end

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')

    # Обязательно для сервера
    options.binary_location = "/usr/bin/chromium-browser"

    driver = uc.Chrome(
        options=options,
        use_subprocess=True
    )
    return driver

def kill_chrome_processes():
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Все Chrome-процессы убиты (Windows)")
        else:
            subprocess.run(["pkill", "-f", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "undetected_chromedriver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Все Chrome-процессы убиты (Linux)")
    except:
        pass

def process_account(driver, acc):
    try:
        print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Подъём: {acc['login']}")
        driver.get(SITE_URL)
        time.sleep(5 + random.uniform(0, 3))

        # Защита 18+
        clicked = False
        for elem in driver.find_elements(By.XPATH, "//button | //div[contains(@style, 'cursor: pointer')]"):
            if any(word in elem.text.lower() for word in ["click", "нажмите", "აქ"]):
                driver.execute_script("arguments[0].click();", elem)
                print("Защита пройдена")
                clicked = True
                time.sleep(3 + random.uniform(0, 2))
                break

        # После защиты — принудительно на страницу логина
        if clicked or "online-escorts" in driver.current_url:
            print("После защиты — переходим на страницу логина вручную")
            driver.get("https://43xgeorgia.me/wp-login.php")
            time.sleep(5 + random.uniform(0, 3))

        # Логин
        try:
            login_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='log' or @id='user_login']"))
            )
            login_field.clear()
            login_field.send_keys(acc['login'])
            print("Логин введён")

            pass_field = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='pwd' or @id='user_pass']"))
            )
            pass_field.clear()
            pass_field.send_keys(acc['pass'])
            print("Пароль введён")

            login_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @value='შესვლა' or @id='wp-submit']")
            driver.execute_script("arguments[0].click();", login_btn)
            print("Кнопка входа нажата")
            time.sleep(8 + random.uniform(0, 3))
        except TimeoutException:
            print("Форма логина не найдена — возможно, уже залогинен")

        # UP
        up_success = False
        selectors = [
            "a.k-up.send",
            "a[class*='k-up'][class*='send']",
            "a.up-btn",
            "a[href*='?up=1']",
            "//a[contains(@class, 'up') or contains(text(), 'UP') or contains(text(), 'ქართული')]"
        ]

        for sel in selectors:
            try:
                if sel.startswith("//"):
                    up_link = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.XPATH, sel))
                    )
                else:
                    up_link = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                    )
                up_url = up_link.get_attribute("href")
                print(f"UP найден — переходим по {up_url}")
                driver.get(up_url)
                up_success = True
                print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] UP УСПЕШНО: {acc['login']} 🎉")
                time.sleep(5 + random.uniform(0, 2))
                break
            except TimeoutException:
                continue

        if not up_success:
            print("UP не найден — возможно, уже апнуто")

        # Защита после UP
        clicked = False
        for elem in driver.find_elements(By.XPATH, "//button | //div[contains(@style, 'cursor: pointer')]"):
            if any(word in elem.text.lower() for word in ["click", "нажмите", "აქ"]):
                driver.execute_script("arguments[0].click();", elem)
                print("Защита после UP пройдена")
                clicked = True
                time.sleep(3 + random.uniform(0, 2))
                break

        if clicked:
            # Повторный UP после защиты
            try:
                up_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.k-up.send"))
                )
                driver.get(up_link.get_attribute("href"))
                print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Повторный UP после защиты: {acc['login']} 🎉")
            except TimeoutException:
                print("Повторный UP не найден")

        # ЖЕЛЕЗНЫЙ ЛОГАУТ
        logout_success = False
        try:
            logout_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'LogOut') or contains(text(), 'გამოსვლა') or contains(@href, 'logout')]"))
            )
            driver.execute_script("arguments[0].click();", logout_btn)
            time.sleep(4)
            logout_success = True
        except TimeoutException:
            pass

        if not logout_success:
            print("Кнопка LogOut не сработала — прямой URL")
            driver.get("https://43xgeorgia.me/wp-login.php?action=logout")
            time.sleep(5)
            try:
                confirm_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'action=logout') and contains(text(), 'log out')]"))
                )
                driver.execute_script("arguments[0].click();", confirm_link)
                time.sleep(4)
                logout_success = True
            except TimeoutException:
                print("Подтверждение логаута не найдено")

        if logout_success:
            print("Логаут выполнен успешно")
        else:
            print("Логаут не удался — следующий цикл будет с новым браузером")

    except Exception as e:
        print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] КРИТИЧЕСКАЯ ОШИБКА у {acc['login']}: {str(e)}")

def run_cycle():
    if not is_working_time():
        print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Вне рабочего времени — спим")
        return

    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] === Цикл по {len(accounts)} аккаунтам ===")
    driver = get_driver()
    try:
        for idx, acc in enumerate(accounts):
            process_account(driver, acc)
            if idx < len(accounts) - 1:
                pause = random.randint(5, 15)
                print(f"Пауза {pause} сек...")
                time.sleep(pause)
    finally:
        try:
            driver.quit()
            print("Driver.quit() выполнен")
        except:
            print("Driver.quit() не сработал")
        time.sleep(2)
        kill_chrome_processes()
        time.sleep(3)
    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Цикл завершён — процессы очищены\n")

run_cycle()

schedule.every(1).minutes.do(run_cycle)

print("БОТ ЗАПУЩЕН! Финальная версия с всеми фиксами для сервера.")
while True:
    schedule.run_pending()
    time.sleep(1)


