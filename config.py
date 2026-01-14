import os
import random
from datetime import time as dtime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# FlareSolverr
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://localhost:8191/v1")
FLARESOLVERR_ENABLED = os.getenv("FLARESOLVERR_ENABLED", "true").lower() in ("1", "true", "yes")
USE_FLARESOLVERR_SESSIONS = os.getenv("USE_FLARESOLVERR_SESSIONS", "true").lower() in ("1", "true", "yes")

# Настройки сайта
TBILISI_TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tbilisi"))
SITE_URL = os.getenv("SITE_URL", "https://43xgeorgia.me/ru").strip()

# Паузы
PAUSE_MIN = int(os.getenv("PAUSE_MIN_SECONDS", "10"))
PAUSE_MAX = int(os.getenv("PAUSE_MAX_SECONDS", "20"))
ROUND_PAUSE_MAX = int(os.getenv("ROUND_PAUSE_MAX_SECONDS", "60"))

# Прокси
PROXY_TYPE = os.getenv("PROXY_TYPE", "http").lower()
PROXY_ROTATION = os.getenv("PROXY_ROTATION", "true").lower() in ("1", "true", "yes")
PROXY_TIMEOUT = int(os.getenv("PROXY_TIMEOUT", "30"))

# Собираем список прокси из .env
PROXY_LIST = []
for i in range(1, 20):  # Проверяем PROXY_1..PROXY_19
    proxy = os.getenv(f"PROXY_{i}")
    if proxy:
        PROXY_LIST.append(proxy.strip())

# User-Agent
CUSTOM_USER_AGENT = os.getenv("CUSTOM_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

def get_proxy():
    """Получить случайный прокси или None если нет прокси"""
    if not PROXY_LIST:
        return None
    
    if PROXY_ROTATION:
        return random.choice(PROXY_LIST)
    else:
        return random.choice(PROXY_LIST)

def get_proxies_dict(proxy_url=None):
    """Получить словарь прокси для requests"""
    if not proxy_url:
        proxy_url = get_proxy()
    
    if not proxy_url:
        return None
    
    if PROXY_TYPE == "socks5":
        return {
            "http": f"socks5://{proxy_url}",
            "https": f"socks5://{proxy_url}"
        }
    else:
        return {
            "http": proxy_url,
            "https": proxy_url
        }

def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except:
        return default

WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
