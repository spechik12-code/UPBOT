#!/bin/bash
# Мониторинг системы

cd "$(dirname "$0")" || exit 1

echo "=== МОНИТОРИНГ UPBOT ==="
echo "Время: $(date)"
echo ""

echo "1. Docker контейнеры:"
docker-compose ps
echo ""

echo "2. Логи FlareSolverr (последние 10 строк):"
docker-compose logs --tail=10 flaresolverr 2>/dev/null || echo "FlareSolverr не запущен"
echo ""

echo "3. Использование ресурсов:"
free -h | head -2
df -h / | tail -1
echo ""

echo "4. Лог бота (последние 10 строк):"
tail -10 bot.log 2>/dev/null || echo "Лог не найден"
echo ""

echo "5. Быстрая проверка прокси:"
python3 -c "
import requests
from config import PROXY_LIST
import time

if PROXY_LIST:
    print(f'Всего прокси: {len(PROXY_LIST)}')
    for i, proxy in enumerate(PROXY_LIST[:3], 1):
        print(f'{i}. {proxy[:60]}...')
        try:
            start = time.time()
            resp = requests.get('https://httpbin.org/ip', 
                              proxies={'http': proxy, 'https': proxy},
                              timeout=5)
            print(f'   ✅ {time.time()-start:.2f}с - IP: {resp.json().get(\"origin\")}')
        except Exception as e:
            print(f'   ❌ Ошибка: {type(e).__name__}')
else:
    print('Прокси не настроены')
"
