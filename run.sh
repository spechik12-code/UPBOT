#!/bin/bash
# Скрипт запуска бота

cd "$(dirname "$0")" || exit 1

echo "=== ЗАПУСК UPBOT ==="
echo "Время: $(date)"
echo ""

echo "1. Проверка FlareSolverr..."
if curl -s http://localhost:8191 > /dev/null; then
    echo "✅ FlareSolverr работает"
else
    echo "⚠️  FlareSolverr не отвечает, запускаем..."
    docker-compose up -d flaresolverr
    sleep 10
fi

echo "2. Проверка прокси..."
python3 -c "
from proxy_utils import health_check_proxies
working = health_check_proxies()
print(f'Найдено рабочих прокси: {len(working)}')
"

echo "3. Активация Python окружения..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Виртуальное окружение не найдено, создаем..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo "4. Запуск бота..."
echo ""
python3 upbot.py

echo ""
echo "=== БОТ ЗАВЕРШИЛ РАБОТУ ==="
