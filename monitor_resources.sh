#!/bin/bash
# monitor_resources.sh

echo "=== Мониторинг ресурсов сервера ==="
echo "Дата: $(date)"
echo ""

# Память
echo "📊 ПАМЯТЬ:"
free -h
echo ""

# Диск
echo "💿 ДИСК:"
df -h /
echo ""

# Docker
echo "🐳 DOCKER:"
docker stats --no-stream
echo ""

# Процессы Python
echo "🐍 PYTHON ПРОЦЕССЫ:"
ps aux | grep python | grep -v grep
echo ""

# Процессы Chrome
echo "🌐 CHROME ПРОЦЕССЫ:"
ps aux | grep chrome | grep -v grep | wc -l | xargs echo "Количество процессов Chrome:"
echo ""

# FlareSolverr
echo "🛡️ FLARESOLVERR:"
curl -s http://localhost:8191 | head -20
echo ""