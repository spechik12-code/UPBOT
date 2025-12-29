import os
import time
import random
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from pathlib import Path

from dotenv import load_dotenv
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =========================
# Config
# =========================
load_dotenv()

SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))

# РЕЖИМ РАБОТЫ (Тбилиси):
# С 16:00 до 03:30 (через полночь)
WORK_START = dtime(16, 0)
WORK_END = dtime(3, 30)

# Headless режим: на сервере true, локально можно false
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

# Паузы между аккаунтами (короткие, чтобы не быть слишком "ровным")
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "5"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "12"))

# Пауза между кругами (обычно 0–30 сек)
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "30"))

# Лок-файл (чтобы случайно не запустить два экземпляра одновременно)
LOCK_FILE = Path(".upbot.lock")


def now_str() -> str:
    return datetime.now(TBILISI_TZ).strftime("%H:%M:%S")


def is_working_time() -> bool:
    """Работаем только с 16:00 до 03:30 по Тбилиси."""
    now_t = datetime.now(TBILISI_TZ).time()
    # окно через полночь
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
            accounts.append({"login": login.strip(), "password": password.strip()})
            i += 1
        else:
            break

    if not accounts:
        raise RuntimeError("ОШИБКА: Нет аккаунтов в .env (ACC1_LOGIN/ACC1_PASS и т.д.)")

    return accounts


def build_driver():
    options = uc.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    return uc.Chrome(options=options, use_subprocess=True)


def pass_18plus(driver):
    for elem in driver.find_elements(By.XPATH, "//button | //div[contains(@style, 'cursor: pointer')]"):
        text = (elem.text or "").lower()
        if any(w in text for w in ("click", "нажмите", "აქ")):
            driver.execute_script("arguments[0].click();", elem)
            print(f"[{now_str()}] 18+ защита пройдена")
            time.sleep(3 + random.uniform(0, 2))
            return True
    return False


def do_login(driver, acc):
    driver.get(SITE_URL)
    time.sleep(5 + random.uniform(0, 3))

    clicked = pass_18plus(driver)

    if clicked or "online-escorts" in (driver.current_url or ""):
        print(f"[{now_str()}] После защиты — переходим на страницу логина")
        driver.get("https://43xgeorgia.me/wp-login.php")
        time.sleep(5 + random.uniform(0, 3))

    try:
        login_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='log' or @id='user_login']"))
        )
        login_field.clear()
        login_field.send_keys(acc["login"])
        print(f"[{now_str()}] Логин введён: {acc['login']}")

        pass_field = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='pwd' or @id='user_pass']"))
        )
        pass_field.clear()
        pass_field.send_keys(acc["password"])
        print(f"[{now_str()}] Пароль введён")

        login_btn = driver.find_element(By.XPATH, "//input[@type='submit' or @value='შესვლა' or @id='wp-submit']")
        driver.execute_script("arguments[0].click();", login_btn)
        print(f"[{now_str()}] Кнопка входа нажата")
        time.sleep(8 + random.uniform(0, 3))

    except TimeoutException:
        print(f"[{now_str()}] Форма логина не найдена — возможно, уже залогинен")


def do_up(driver, acc):
    selectors = [
        "a.k-up.send",
        "a[class*='k-up'][class*='send']",
        "a.up-btn",
        "a[href*='?up=1']",
        "//a[contains(@class, 'up') or contains(text(), 'UP') or contains(text(), 'ქართული')]",
    ]

    for sel in selectors:
        try:
            if sel.startswith("//"):
                up_link = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, sel)))
            else:
                up_link = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))

            up_url = up_link.get_attribute("href")
            if not up_url:
                continue

            print(f"[{now_str()}] UP найден — переходим по ссылке")
            driver.get(up_url)
            print(f"[{now_str()}] UP УСПЕШНО: {acc['login']} 🎉")
            time.sleep(5 + random.uniform(0, 2))
            return True

        except TimeoutException:
            continue

    print(f"[{now_str()}] UP не найден — возможно, уже апнуто")
    return False


def do_logout(driver):
    try:
        logout_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(text(), 'LogOut') or contains(text(), 'გამოსვლა') or contains(@href, 'logout')]")
            )
        )
        driver.execute_script("arguments[0].click();", logout_btn)
        time.sleep(4)
        print(f"[{now_str()}] Logout выполнен кнопкой")
        return True
    except TimeoutException:
        pass

    print(f"[{now_str()}] Logout кнопкой не сработал — пробуем URL")
    driver.get("https://43xgeorgia.me/wp-login.php?action=logout")
    time.sleep(5)

    try:
        confirm_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href, 'action=logout') and contains(text(), 'log out')]")
            )
        )
        driver.execute_script("arguments[0].click();", confirm_link)
        time.sleep(4)
        print(f"[{now_str()}] Logout подтверждён")
        return True
    except TimeoutException:
        print(f"[{now_str()}] Подтверждение logout не найдено")
        return False


def process_account(acc):
    print(f"\n[{now_str()}] === Подъём: {acc['login']} ===")

    driver = None
    try:
        driver = build_driver()
        do_login(driver, acc)

        # UP
        do_up(driver, acc)

        # Защита после UP (как в исходном скрипте)
        clicked = pass_18plus(driver)
        if clicked:
            try:
                up_link = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.k-up.send"))
                )
                href = up_link.get_attribute("href")
                if href:
                    driver.get(href)
                    print(f"[{now_str()}] Повторный UP после защиты: {acc['login']} 🎉")
                    time.sleep(5)
            except TimeoutException:
                print(f"[{now_str()}] Повторный UP не найден")

        do_logout(driver)

    except Exception as e:
        print(f"[{now_str()}] КРИТИЧЕСКАЯ ОШИБКА у {acc['login']}: {e}")

    finally:
        # ВАЖНО: закрываем браузер, чтобы процессы не копились
        if driver:
            try:
                driver.quit()
                print(f"[{now_str()}] driver.quit() выполнен")
            except Exception:
                print(f"[{now_str()}] driver.quit() не сработал (редко)")

        pause = random.randint(PAUSE_MIN, PAUSE_MAX)
        print(f"[{now_str()}] Пауза {pause} сек...")
        time.sleep(pause)


def acquire_lock():
    if LOCK_FILE.exists():
        return False
    LOCK_FILE.write_text(str(time.time()), encoding="utf-8")
    return True


def release_lock():
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def run_round():
    accounts = load_accounts()
    print(f"\n[{now_str()}] === КРУГ: {len(accounts)} аккаунтов ===")
    for acc in accounts:
        process_account(acc)
    print(f"[{now_str()}] === КРУГ ЗАВЕРШЁН ===\n")


def main():
    if not acquire_lock():
        print(f"[{now_str()}] Уже запущен другой экземпляр UPBOT. Выходим.")
        return

    print(f"[{now_str()}] UPBOT запущен. Headless={HEADLESS}. Окно работы: 16:00–03:30 (Тбилиси)")

    try:
        while True:
            if is_working_time():
                start = time.time()
                run_round()
                elapsed = int(time.time() - start)

                pause = random.randint(0, ROUND_PAUSE_MAX)
                print(f"[{now_str()}] Круг занял ~{elapsed} сек. Пауза между кругами {pause} сек...\n")
                time.sleep(pause)
            else:
                # Вне окна работы — не запускаем Chrome вообще
                print(f"[{now_str()}] Вне окна 16:00–03:30 — сон 60 сек")
                time.sleep(60)

    finally:
        release_lock()


if __name__ == "__main__":
    main()
