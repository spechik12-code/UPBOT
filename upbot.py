import os
import time
import random
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =========================
# ENV / CONFIG
# =========================
load_dotenv()

TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))

SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Время работы (можно менять в .env):
# WORK_START=16:00
# WORK_END=03:30
def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        s = (s or "").strip()
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except Exception:
        return default


WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
DEBUG_DUMP = os.getenv("DEBUG_DUMP", "true").lower() in ("1", "true", "yes")

PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "5"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "12"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "30"))

# Если нужно явно указать бинарник chromium (snap):
# CHROME_BINARY=/snap/bin/chromium
CHROME_BINARY = os.getenv("CHROME_BINARY", "").strip() or None


# =========================
# Helpers
# =========================
def now_str() -> str:
    return datetime.now(TBILISI_TZ).strftime("%H:%M:%S")


def is_working_time() -> bool:
    """Работаем только в окне WORK_START–WORK_END по Тбилиси (включая переход через полночь)."""
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
            accounts.append({"login": login.strip(), "password": password.strip()})
            i += 1
        else:
            break
    if not accounts:
        raise RuntimeError("Нет аккаунтов в .env. Ожидаю ACC1_LOGIN/ACC1_PASS и т.д.")
    return accounts


def safe_name(s: str) -> str:
    s = (s or "acc").strip()
    s = s.replace("@", "_at_").replace("/", "_").replace("\\", "_").replace(":", "_")
    return s[:80]


def debug_dump(driver, tag: str, acc_login: str):
    """Сохраняет PNG + HTML, чтобы понять, что реально показал сайт на сервере."""
    if not DEBUG_DUMP:
        return
    try:
        os.makedirs("debug", exist_ok=True)
        ts = int(time.time())
        sn = safe_name(acc_login)
        driver.save_screenshot(f"debug/{tag}_{sn}_{ts}.png")
        with open(f"debug/{tag}_{sn}_{ts}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source or "")
        print(f"[{now_str()}] DEBUG сохранён: debug/{tag}_{sn}_{ts}.(png|html)")
        print(f"[{now_str()}] DEBUG URL: {driver.current_url}")
    except Exception as e:
        print(f"[{now_str()}] DEBUG не удалось сохранить ({e})")


def build_driver():
    options = uc.ChromeOptions()

    if CHROME_BINARY:
        options.binary_location = CHROME_BINARY

    if HEADLESS:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    return uc.Chrome(options=options, use_subprocess=True)


def pass_18plus(driver):
    """Пытаемся пройти 18+ / антибот-плашку, если она есть."""
    try:
        # часто там кнопка/ссылка с текстом "Click" / "Нажмите" и т.п.
        for elem in driver.find_elements(By.XPATH, "//button | //a | //div[contains(@style,'cursor')]"):
            text = (elem.text or "").strip().lower()
            if any(w in text for w in ("click", "наж", "enter", "ok", "continue", "продолж")):
                driver.execute_script("arguments[0].click();", elem)
                print(f"[{now_str()}] 18+ защита пройдена")
                time.sleep(2 + random.uniform(0, 2))
                return True
    except Exception:
        pass
    return False


def is_logged_in(driver) -> bool:
    """Грубая проверка: если видим logout/wp-admin — считаем, что залогинены."""
    try:
        links = driver.find_elements(By.XPATH, "//a[@href]")
        for a in links:
            href = (a.get_attribute("href") or "").lower()
            if "wp-login.php?action=logout" in href or "wp-admin" in href or "logout" in href:
                return True
    except Exception:
        pass
    return False


def do_login(driver, acc):
    """
    Надёжнее всего идти напрямую на wp-login.
    Если уже залогинен — не пытаемся вводить форму.
    """
    # 1) Открываем сайт (чтобы пройти плашки)
    driver.get(SITE_URL)
    time.sleep(3 + random.uniform(0, 2))
    pass_18plus(driver)

    # 2) Идём на логин
    driver.get("https://43xgeorgia.me/wp-login.php")
    time.sleep(3 + random.uniform(0, 2))

    # 3) Если уже залогинен — ок
    if is_logged_in(driver):
        print(f"[{now_str()}] Уже залогинен (по ссылкам logout/wp-admin)")
        return

    # 4) Пробуем найти форму и залогиниться
    try:
        login_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @name='log' or @id='user_login']"))
        )
        login_field.clear()
        login_field.send_keys(acc["login"])
        print(f"[{now_str()}] Логин введён: {acc['login']}")

        pass_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='pwd' or @id='user_pass']"))
        )
        pass_field.clear()
        pass_field.send_keys(acc["password"])
        print(f"[{now_str()}] Пароль введён")

        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' or @id='wp-submit']"))
        )
        driver.execute_script("arguments[0].click();", login_btn)
        print(f"[{now_str()}] Кнопка входа нажата")

        time.sleep(6 + random.uniform(0, 3))

        # Иногда после логина снова вылезает плашка
        pass_18plus(driver)

    except TimeoutException:
        print(f"[{now_str()}] Форма логина не найдена — сохраняю debug")
        debug_dump(driver, "login_not_found", acc["login"])
        # Это не фатально — возможно сайт уже залогинил/редиректнул.
        return


def do_up(driver, acc):
    """
    Пытаемся найти и нажать/открыть UP.
    Если не нашли — сохраняем debug, чтобы понять, что именно показал сайт.
    """
    selectors = [
        "a.k-up.send",
        "a[class*='k-up'][class*='send']",
        "a.up-btn",
        "a[href*='?up=1']",
        "//a[contains(@class,'up') or contains(translate(text(),'up','UP'),'UP')]",
    ]

    for sel in selectors:
        try:
            if sel.startswith("//"):
                up_link = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, sel)))
            else:
                up_link = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))

            href = up_link.get_attribute("href")
            if href:
                print(f"[{now_str()}] UP найден — переходим по ссылке")
                driver.get(href)
                time.sleep(3 + random.uniform(0, 2))
                print(f"[{now_str()}] UP УСПЕШНО: {acc['login']} 🎉")
                return True

            # если href нет — пробуем клик
            driver.execute_script("arguments[0].click();", up_link)
            time.sleep(3 + random.uniform(0, 2))
            print(f"[{now_str()}] UP кликнут: {acc['login']} 🎉")
            return True

        except TimeoutException:
            continue
        except Exception:
            continue

    print(f"[{now_str()}] UP не найден — сохраняю debug")
    debug_dump(driver, "up_not_found", acc["login"])
    print(f"[{now_str()}] UP не найден — возможно уже апнуто/страница другая/антибот")
    return False


def do_logout(driver):
    """
    Логаут делаем максимально терпимо:
    - если ссылка logout есть — кликаем
    - если не нашли — просто идём на wp-login logout
    - подтверждение может не появляться — это ок
    """
    try:
        logout_link = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href,'action=logout') or contains(text(),'Logout') or contains(text(),'გამოსვლა')]"))
        )
        driver.execute_script("arguments[0].click();", logout_link)
        time.sleep(3)
        print(f"[{now_str()}] Logout выполнен ссылкой")
        return True
    except TimeoutException:
        pass
    except Exception:
        pass

    print(f"[{now_str()}] Logout ссылкой не сработал — пробуем URL")
    try:
        driver.get("https://43xgeorgia.me/wp-login.php?action=logout")
        time.sleep(3)

        # Иногда wordpress просит подтвердить logout
        try:
            confirm = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'action=logout') and (contains(text(),'log out') or contains(text(),'Log Out'))]"))
            )
            driver.execute_script("arguments[0].click();", confirm)
            time.sleep(2)
            print(f"[{now_str()}] Logout подтверждён")
            return True
        except TimeoutException:
            # подтверждения нет — бывает; считаем не критично
            print(f"[{now_str()}] Подтверждение logout не найдено (не критично)")
            return False

    except Exception as e:
        print(f"[{now_str()}] Logout URL ошибка: {e}")
        return False


def process_account(acc):
    print(f"\n[{now_str()}] === Подъём: {acc['login']} ===")

    driver = None
    try:
        driver = build_driver()
        do_login(driver, acc)

        # На всякий случай ещё раз пробуем пройти плашку (после логина)
        pass_18plus(driver)

        do_up(driver, acc)
        do_logout(driver)

    except Exception as e:
        print(f"[{now_str()}] КРИТИЧЕСКАЯ ОШИБКА у {acc['login']}: {e}")
        if driver:
            debug_dump(driver, "exception", acc["login"])

    finally:
        if driver:
            try:
                driver.quit()
                print(f"[{now_str()}] driver.quit() выполнен")
            except Exception:
                print(f"[{now_str()}] driver.quit() не сработал (редко)")

        pause = random.randint(PAUSE_MIN, PAUSE_MAX)
        print(f"[{now_str()}] Пауза {pause} сек...")
        time.sleep(pause)


def run_round():
    accounts = load_accounts()
    print(f"\n[{now_str()}] === КРУГ: {len(accounts)} аккаунтов ===")
    for acc in accounts:
        process_account(acc)
    print(f"[{now_str()}] === КРУГ ЗАВЕРШЁН ===\n")


def main():
    print(f"[{now_str()}] UPBOT запущен. Headless={HEADLESS}. Окно: {WORK_START.strftime('%H:%M')}–{WORK_END.strftime('%H:%M')} (Тбилиси)")

    while True:
        if is_working_time():
            start = time.time()
            run_round()
            elapsed = int(time.time() - start)

            pause = random.randint(0, ROUND_PAUSE_MAX)
            print(f"[{now_str()}] Круг занял ~{elapsed} сек. Пауза между кругами {pause} сек...\n")
            time.sleep(pause)
        else:
            print(f"[{now_str()}] Вне окна {WORK_START.strftime('%H:%M')}–{WORK_END.strftime('%H:%M')} — сон 60 сек")
            time.sleep(60)


if __name__ == "__main__":
    main()
