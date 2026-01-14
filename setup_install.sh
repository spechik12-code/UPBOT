#!/bin/bash
# Скрипт установки на Ubuntu сервер

set -e

echo "=== УСТАНОВКА UPBOT НА UBUNTU ==="
echo ""

echo "1. Обновление системы..."
sudo apt update
sudo apt upgrade -y

echo "2. Установка базовых пакетов..."
sudo apt install -y curl wget git nano python3 python3-pip python3-venv

echo "3. Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    sudo userm
