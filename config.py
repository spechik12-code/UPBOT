import os
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

def parse_hhmm(s: str, default: dtime) -> dtime:
    try:
        hh, mm = s.split(":")
        return dtime(int(hh), int(mm))
    except:
        return default

WORK_START = parse_hhmm(os.getenv("WORK_START", "16:00"), dtime(16, 0))
WORK_END = parse_hhmm(os.getenv("WORK_END", "03:30"), dtime(3, 30))

HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")