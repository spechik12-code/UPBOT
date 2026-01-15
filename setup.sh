#!/bin/bash
# install.sh

echo "=== Установка UPBOT с FlareSolverr ==="

# 1. Обновление системы
echo "1. Обновление системы..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git nano python3-pip python3-venv

# 2. Установка Docker
echo "2. Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo usermod -aG docker $USER
else
    echo "Docker уже установлен"
fi

# 3. Клонирование/создание проекта
echo "3. Подготовка проекта..."
PROJECT_DIR="$HOME/upbot-flaresolverr"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 4. Создание виртуального окружения Python
echo "4. Создание Python окружения..."
python3 -m venv venv
source venv/bin/activate

# 5. Установка зависимостей Python
echo "5. Установка Python зависимостей..."
pip install --upgrade pip
pip install undetected-chromedriver selenium python-dotenv requests

# 6. Установка Chrome для Selenium
echo "6. Установка Chrome..."
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# 7. Создание файлов
echo "7. Создание конфигурационных файлов..."
# (файлы создаются вручную или копируются)

# 8. Запуск FlareSolverr
echo "8. Запуск FlareSolverr..."
docker-compose up -d

# 9. Проверка
echo "9. Проверка установки..."
sleep 10
docker ps
curl -s http://localhost:8191 | grep -q "FlareSolverr" && echo "✅ FlareSolverr работает" || echo "❌ FlareSolverr не отвечает"

echo ""
echo "=== УСТАНОВКА ЗАВЕРШЕНА ==="
echo ""
echo "Следующие шаги:"
echo "1. Отредактируйте файл .env: nano $PROJECT_DIR/.env"
echo "2. Добавьте ваши аккаунты в .env"
echo "3. Запустите бота: cd $PROJECT_DIR && source venv/bin/activate && python3 upbot.py"
echo ""
echo "Для управления Docker:"
echo "  Запуск: docker-compose up -d"
echo "  Остановка: docker-compose down"
echo "  Логи: docker-compose logs -f"