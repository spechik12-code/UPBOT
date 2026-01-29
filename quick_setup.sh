#!/bin/bash
# quick_setup.sh - Быстрая установка зависимостей на сервере

echo "=========================================="
echo "🚀 Быстрая установка UPBOT"
echo "=========================================="
echo ""

# Проверка что мы в правильной папке
if [ ! -f "upbot.py" ]; then
    echo "❌ Ошибка: файл upbot.py не найден!"
    echo "Запустите этот скрипт из папки /opt/bots/doska-new"
    exit 1
fi

# 1. Обновление системы
echo "1️⃣  Обновление системы..."
sudo apt update

# 2. Установка Python зависимостей
echo ""
echo "2️⃣  Установка Python зависимостей..."
sudo apt install -y python3 python3-pip python3-venv

# 3. Создание виртуального окружения
echo ""
echo "3️⃣  Создание виртуального окружения..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
else
    echo "ℹ️  Виртуальное окружение уже существует"
fi

# 4. Активация venv и установка пакетов
echo ""
echo "4️⃣  Установка Python пакетов..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Установка Docker (если не установлен)
echo ""
echo "5️⃣  Проверка Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker не найден, устанавливаем..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен"
fi

# 6. Установка Google Chrome
echo ""
echo "6️⃣  Проверка Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    echo "Chrome не найден, устанавливаем..."
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
    echo "✅ Chrome установлен"
else
    CHROME_VERSION=$(google-chrome --version)
    echo "✅ Chrome уже установлен: $CHROME_VERSION"
fi

# 7. Создание .env если не существует
echo ""
echo "7️⃣  Проверка .env файла..."
if [ ! -f ".env" ]; then
    echo "Создаем .env из шаблона..."
    cp .env.example .env
    echo "⚠️  ВАЖНО: Отредактируйте .env и добавьте ваши логины/пароли!"
    echo "   Используйте: nano .env"
else
    echo "✅ .env уже существует"
fi

# 8. Запуск FlareSolverr
echo ""
echo "8️⃣  Запуск FlareSolverr..."
if docker ps | grep -q flaresolverr; then
    echo "✅ FlareSolverr уже запущен"
else
    docker-compose up -d
    echo "⏳ Ждем 10 секунд..."
    sleep 10
    
    if curl -s http://localhost:8191 | grep -q "FlareSolverr"; then
        echo "✅ FlareSolverr успешно запущен"
    else
        echo "⚠️  FlareSolverr не отвечает, проверьте: docker logs flaresolverr"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Установка завершена!"
echo "=========================================="
echo ""
echo "📝 Следующие шаги:"
echo ""
echo "1. Отредактируйте .env файл:"
echo "   nano .env"
echo ""
echo "2. Добавьте ваши аккаунты (ACC1_LOGIN, ACC1_PASS и т.д.)"
echo ""
echo "3. Запустите бота для теста:"
echo "   source venv/bin/activate"
echo "   python3 upbot.py"
echo ""
echo "4. Если все работает, настройте автозапуск через systemd"
echo "   (см. COMPLETE_SETUP_GUIDE.md)"
echo ""
echo "=========================================="
