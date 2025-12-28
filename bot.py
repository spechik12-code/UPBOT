import time
import random
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
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

print(f"Загружено {len(accounts)} аккаунтов. Бот на Playwright — стабильный на сервере.")

TBILISI_TZ = ZoneInfo('Asia/Tbilisi')

def is_working_time():
    now = datetime.now(TBILISI_TZ)
    start = dtime(15, 0)
    end = dtime(3, 30)
    if start <= end:
        return start <= now.time() <= end
    else:
        return now.time() >= start or now.time() <= end

def run_cycle():
    if not is_working_time():
        print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Вне времени — спим")
        return

    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] === Цикл по {len(accounts)} аккаунтам ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            for idx, acc in enumerate(accounts):
                print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Подъём: {acc['login']}")
                page.goto(SITE_URL)
                time.sleep(5)

                # Защита 18+
                if page.locator("//button | //div[contains(@style, 'cursor: pointer')]").count() > 0:
                    page.locator("//button | //div[contains(@style, 'cursor: pointer')]").first.click()
                    print("Защита пройдена")
                    time.sleep(3)

                # После защиты — на логин
                if "online-escorts" in page.url:
                    page.goto("https://43xgeorgia.me/wp-login.php")
                    time.sleep(5)

                # Логин
                page.fill("//input[@name='log' or @id='user_login']", acc['login'])
                page.fill("//input[@name='pwd' or @id='user_pass']", acc['pass'])
                page.click("//input[@type='submit' or @id='wp-submit']")
                print("Логин выполнен")
                time.sleep(8)

                # UP
                up_link = page.locator("a.k-up.send").first
                if up_link.count() > 0:
                    up_url = up_link.get_attribute("href")
                    print(f"UP по {up_url}")
                    page.goto(up_url)
                    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] UP УСПЕШНО: {acc['login']} 🎉")
                    time.sleep(5)

                # Защита после UP
                if page.locator("//button | //div[contains(@style, 'cursor: pointer')]").count() > 0:
                    page.locator("//button | //div[contains(@style, 'cursor: pointer')]").first.click()
                    print("Защита после UP пройдена")
                    time.sleep(3)
                    # Повторный UP
                    up_link = page.locator("a.k-up.send").first
                    if up_link.count() > 0:
                        page.goto(up_link.get_attribute("href"))
                        print(f"Повторный UP: {acc['login']} 🎉")

                # Логаут
                logout_link = page.locator("//a[contains(text(), 'LogOut') or contains(text(), 'გამოსვლა') or contains(@href, 'logout')]").first
                if logout_link.count() > 0:
                    page.goto(logout_link.get_attribute("href"))
                    print("Логаут выполнен")
                    time.sleep(4)
                else:
                    print("LogOut не найден — прямой URL")
                    page.goto("https://43xgeorgia.me/wp-login.php?action=logout")
                    time.sleep(5)
                    try:
                        page.click("//a[contains(@href, 'action=logout') and contains(text(), 'log out')]")
                    except:
                        pass

                if idx < len(accounts) - 1:
                    pause = random.randint(5, 15)
                    print(f"Пауза {pause} сек...")
                    time.sleep(pause)
        except Exception as e:
            print(f"Ошибка в цикле: {str(e)}")
        finally:
            context.close()
            browser.close()
    print(f"[{datetime.now(TBILISI_TZ).strftime('%H:%M')}] Цикл завершён\n")

run_cycle()

schedule.every(1).minutes.do(run_cycle)

print("БОТ НА PLAYWRIGHT ЗАПУЩЕН! Стабильный на сервере.")
while True:
    schedule.run_pending()
    time.sleep(1)
