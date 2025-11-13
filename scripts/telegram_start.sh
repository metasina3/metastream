#!/bin/bash
# Script to start and test Telegram bot

echo "🤖 Starting Telegram Bot..."
echo ""

# Check if web service is running
if ! docker compose ps web | grep -q "Up"; then
    echo "❌ Web service is not running. Starting it..."
    docker compose up -d web
    sleep 5
fi

echo "📋 Configuration:"
echo "   - API URL: $(docker compose exec -T web python -c 'from app.core.config import settings; print(settings.API_URL)' 2>/dev/null || echo 'N/A')"
echo "   - Telegram Enabled: $(docker compose exec -T web python -c 'from app.core.config import settings; print(settings.TELEGRAM_ENABLED)' 2>/dev/null || echo 'N/A')"
echo ""

# Initialize bot (set webhook and send test message)
echo "🚀 Initializing bot..."
echo ""

# Option 1: Use API endpoint
API_URL=$(docker compose exec -T web python -c 'from app.core.config import settings; print(settings.API_URL)' 2>/dev/null)

if [ -n "$API_URL" ]; then
    echo "📡 Calling init endpoint: $API_URL/api/telegram/init"
    curl -X POST "$API_URL/api/telegram/init" \
        -H "Content-Type: application/json" \
        -w "\n\n" 2>/dev/null || echo "❌ Failed to call init endpoint"
else
    echo "❌ Could not get API URL"
fi

echo ""
echo "✅ Done! Check your Telegram for the test message."
echo ""
echo "💡 To test again, run:"
echo "   curl -X POST $API_URL/api/telegram/test"

