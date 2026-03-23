#!/bin/bash
# migrate.sh — скрипт миграции на новую структуру
# Запускать из /root/bot/

set -e

echo "=== Миграция ad_bot → модульная структура ==="

# 1. Бэкап
echo "[1/5] Создаю бэкап..."
cp ad_bot.py ad_bot_backup_$(date +%Y%m%d_%H%M%S).py
echo "  ✅ Бэкап создан"

# 2. Создаём директории
echo "[2/5] Создаю структуру директорий..."
mkdir -p services handlers utils data
touch services/__init__.py handlers/__init__.py utils/__init__.py
echo "  ✅ Директории созданы"

# 3. Копируем новые файлы (предполагается что они уже есть)
echo "[3/5] Проверяю наличие файлов..."
for f in config.py database.py sessions.py main.py \
          services/ai_service.py services/tiktok_api.py services/facebook_api.py \
          handlers/settings.py utils/helpers.py; do
    if [ -f "$f" ]; then
        echo "  ✅ $f"
    else
        echo "  ❌ $f — ОТСУТСТВУЕТ!"
    fi
done

# 4. Переносим данные
echo "[4/5] Переношу данные в /root/bot/data/..."
for f in user_data.json products.json reminders.json sessions.json; do
    if [ -f "$f" ]; then
        cp "$f" "data/$f"
        echo "  ✅ $f → data/$f"
    fi
done

# 5. Создаём .env с ключами
echo "[5/5] Создаю .env шаблон..."
if [ ! -f ".env" ]; then
cat > .env << 'EOF'
# Заполни чтобы не хранить ключи в коде
BOT_TOKEN=
DEEPSEEK_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
FB_ACCESS_TOKEN=
FB_AD_ACCOUNT_ID=
TT_APP_ID=
TT_APP_SECRET=
TT_ADVERTISER_ID=
TT_ACCESS_TOKEN=
DATA_DIR=/root/bot/data
EOF
    echo "  ✅ .env создан — заполни ключи"
else
    echo "  ⬜ .env уже существует"
fi

echo ""
echo "=== Готово! ==="
echo ""
echo "Дальнейшие шаги:"
echo "  1. Переименуй ad_bot.py → ad_bot_legacy.py"
echo "     mv ad_bot.py ad_bot_legacy.py"
echo ""
echo "  2. Запусти нового бота:"
echo "     pkill -f ad_bot_legacy.py"
echo "     nohup python3 main.py > bot.log 2>&1 &"
echo ""
echo "  3. Проверь логи:"
echo "     tail -f bot.log"
echo ""
echo "  4. После проверки — постепенно переноси хендлеры из"
echo "     ad_bot_legacy.py в handlers/*.py"
