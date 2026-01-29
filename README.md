# UPBOT - Автоматизация UP для доски объявлений

Бот для автоматического поднятия объявлений на сайте с защитой от CloudFlare через FlareSolverr.

## Особенности

- ✅ Обход CloudFlare защиты через FlareSolverr
- ✅ Автоматическое определение версии Chrome (версия ChromeDriver подбирается автоматически)
- ✅ Имитация человеческого поведения (случайные паузы, движения мыши)
- ✅ Поддержка множества аккаунтов
- ✅ Работа по расписанию
- ✅ Headless режим для работы на сервере

## Требования

- Ubuntu/Debian сервер
- Python 3.8+
- Docker и Docker Compose
- Google Chrome

## Быстрая установка

### 1. Клонируйте репозиторий

```bash
sudo mkdir -p /opt/bots/doska-new
sudo chown -R $USER:$USER /opt/bots/doska-new
cd /opt/bots/doska-new
git clone <ваш-репозиторий> .
```

### 2. Установите зависимости

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python и Docker
sudo apt install -y python3 python3-pip python3-venv docker.io docker-compose

# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Установите Google Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
```

### 3. Настройте Python окружение

```bash
cd /opt/bots/doska-new

# Создайте виртуальное окружение
python3 -m venv venv

# Активируйте
source venv/bin/activate

# Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Запустите FlareSolverr

```bash
docker-compose up -d

# Проверьте что запущен
docker ps
curl http://localhost:8191
```

### 5. Настройте конфигурацию

```bash
# Создайте .env из шаблона
cp .env.example .env

# Отредактируйте и добавьте ваши аккаунты
nano .env
```

### 6. Запустите бота

```bash
# Тестовый запуск
python3 upbot.py

# Для запуска в фоне используйте systemd (см. ниже)
```

## Настройка systemd для автозапуска

Создайте сервис:

```bash
sudo nano /etc/systemd/system/upbot.service
```

Содержимое (замените YOUR_USERNAME):

```ini
[Unit]
Description=UPBOT Service
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/bots/doska-new
Environment="PATH=/opt/bots/doska-new/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/bots/doska-new/venv/bin/python3 /opt/bots/doska-new/upbot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable upbot
sudo systemctl start upbot
sudo systemctl status upbot
```

## Управление ботом

```bash
# Запустить
sudo systemctl start upbot

# Остановить
sudo systemctl stop upbot

# Перезапустить
sudo systemctl restart upbot

# Посмотреть логи
sudo journalctl -u upbot -f
```

## Обновление

```bash
cd /opt/bots/doska-new
sudo systemctl stop upbot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start upbot
```

## Структура файлов

```
/opt/bots/doska-new/
├── upbot.py              # Основной скрипт бота
├── config.py             # Конфигурация (не используется, настройки в .env)
├── requirements.txt      # Python зависимости
├── docker-compose.yml    # FlareSolverr настройки
├── .env                  # Ваши настройки (не в git!)
├── .env.example          # Пример настроек
└── venv/                 # Виртуальное окружение
```

## Настройки в .env

- `FLARESOLVERR_URL` - URL FlareSolverr (по умолчанию http://localhost:8191/v1)
- `FLARESOLVERR_ENABLED` - Включить/выключить FlareSolverr (true/false)
- `SITE_URL` - URL сайта
- `PAUSE_MIN_SECONDS` / `PAUSE_MAX_SECONDS` - Паузы между действиями
- `WORK_START` / `WORK_END` - Время работы бота
- `HEADLESS` - Запуск без GUI (true/false)
- `ACC1_LOGIN` / `ACC1_PASS` - Данные аккаунтов

## Решение проблем

### Бот не запускается

```bash
# Смотрите логи
sudo journalctl -u upbot -n 50

# Проверьте .env
cat .env

# Тестовый запуск
cd /opt/bots/doska-new
source venv/bin/activate
python3 upbot.py
```

### Ошибка версии Chrome

```bash
# Обновите Chrome
sudo apt update
sudo apt install --only-upgrade google-chrome-stable -y

# Переустановите драйвер
source venv/bin/activate
pip uninstall -y undetected-chromedriver
pip install undetected-chromedriver
```

### FlareSolverr не работает

```bash
# Перезапустите
docker-compose restart

# Смотрите логи
docker logs flaresolverr -f
```

## Лицензия

MIT

## Поддержка

Если возникли вопросы - создайте Issue в репозитории.
