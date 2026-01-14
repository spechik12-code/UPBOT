#!/bin/bash
# Скрипт обновления проекта через Git

set -e

echo "=== ОБНОВЛЕНИЕ UPBOT ==="
echo "Время: $(date)"
echo ""

cd "$(dirname "$0")" || { echo "❌ Ошибка перехода в директорию"; exit 1; }

if ! command -v git &> /dev/null; then
    echo "❌ Git не установлен"
    echo "Установите: apt-get install git"
    exit 1
fi

if [ -f .env ]; then
    echo "📋 Сохраняем текущий .env файл..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Резервная копия создана"
else
    echo "⚠️  .env файл не найден"
fi

echo "🧹 Очистка старых файлов..."
git clean -fd

echo "⬇️  Получение обновлений..."
git pull origin main

if [ $? -eq 0 ]; then
    echo "✅ Код успешно обновлен"
    
    echo "📦 Обновление зависимостей Python..."
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install -r requirements.txt --upgrade
        echo "✅ Зависимости обновлены"
    fi
    
    echo "🐳 Перезапуск FlareSolverr..."
    docker-compose down
    docker-compose up -d
    
    echo ""
    echo "🎉 ОБНОВЛЕНИЕ УСПЕШНО ЗАВЕРШЕНО!"
    echo ""
    echo "Следующие шаги:"
    echo "1. Проверьте .env файл (если нужно восстановите из backup)"
    echo "2. Запустите бота: ./run.sh"
else
    echo "❌ Ошибка при обновлении кода"
    exit 1
fi
