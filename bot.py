import time
import random
import os
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

print(f"Загружено {len(accounts)} аккаунтов. UP — с увеличенным таймаутом и несколькими селекторами.")

TBILISI_TZ = ZoneInfo('Asia/Tbilisi')

def is_working_time():
    now = datetime.now(TBILISI_TZ)
    start = dtime(15, 0)
    end = dtime(3, 30)
    if start <= end:
        return start <= now.time() <= end
    else:
        return now.time() >= start or now.time() <= end

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')  # Закомментировано — браузер видим
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(
        options=options,
        version_main=143,
        use_subprocess=True
    )
    return driver

def process_account(driver, acc):
    try:
        print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Подъём: {acc['login']}")
        driver.get(SITE_URL)
        time.sleep(10 + random.uniform(0, 4))

        # Защита 18+
        clicked = False
        for elem in driver.find_elements(By.XPATH, "//button | //div[contains(@style, 'cursor: pointer')]"):
            if any(word in elem.text.lower() for word in ["click", "нажмите", "აქ"]):
                driver.execute_script("arguments[0].click();", elem)
                print("Защита пройдена")
                clicked = True
                time.sleep(6 + random.uniform(0, 3))
                break
        if not clicked:
            print("Защита не появилась")

        # Логин
        try:
            login_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='log' or @id='user_login']"))
            )
            login_field.clear()
            login_field.send_keys(acc['login'])
            print("Логин введён")

            pass_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='pwd' or @id='user_pass']"))
            )
            pass_field.clear()
            pass_field.send_keys(acc['pass'])
            print("Пароль введён")

            login_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @value='შესვლა' or @id='wp-submit']")
            driver.execute_script("arguments[0].click();", login_btn)
            print("Кнопка входа нажата")
            time.sleep(15 + random.uniform(0, 5))  # Больше времени на загрузку кабинета
        except TimeoutException:
            print("Уже залогинен — пропускаем логин")

        # UP — несколько селекторов + большой таймаут
        up_success = False
        try:
            # Попробуем разные варианты селекторов
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
                        up_link = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, sel))
                        )
                    else:
                        up_link = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                        )
                    up_url = up_link.get_attribute("href")
                    print(f"UP найден по селектору '{sel}' — переходим по {up_url}")
                    driver.get(up_url)
                    up_success = True
                    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] UP УСПЕШНО ВЫПОЛНЕН ДЛЯ {acc['login']} 🎉🎉🎉")
                    time.sleep(8 + random.uniform(0, 4))
                    break
                except TimeoutException:
                    continue

            if not up_success:
                print("UP не найден ни по одному селектору — возможно, уже апнуто сегодня")

        except Exception as e:
            print(f"Ошибка при UP у {acc['login']}: {str(e)}")

        # Логаут
        try:
            logout_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'LogOut') or contains(text(), 'გამოსვლა') or contains(@href, 'logout')]"))
            )
            driver.execute_script("arguments[0].click();", logout_btn)
            print("Логаут выполнен")
            time.sleep(5)
        except TimeoutException:
            print("LogOut не найден — следующий цикл будет чистым")

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
                pause = random.randint(10, 30)
                print(f"Пауза {pause} сек...")
                time.sleep(pause)
    finally:
        try:
            driver.quit()
        except:
            pass
    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Цикл завершён\n")

run_cycle()

schedule.every(2).minutes.do(run_cycle)

print("БОТ ЗАПУЩЕН! UP ищется по нескольким селекторам + прямой переход.")
print("Браузер видим — смотри процесс.")
while True:
    schedule.run_pending()
    time.sleep(1)
