#!/bin/bash

echo "🚀 Starting Metastream V2..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "📝 Please copy env.template.v2 to .env and fill in the values"
    exit 1
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p data/pgdata data/media data/uploads data/backups logs
chmod -R 755 data/

# Build prep and stream worker images (if not exist)
echo "🔨 Building Docker images..."
if ! docker images | grep -q "metastream/prep-worker"; then
    echo "   Building prep-worker..."
    docker build -t metastream/prep-worker:stable -f Dockerfile.prep .
fi

if ! docker images | grep -q "metastream/stream-worker"; then
    echo "   Building stream-worker..."
    docker build -t metastream/stream-worker:stable -f Dockerfile.stream .
fi

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 10

# Check services
echo "🔍 Checking services..."
docker compose ps

echo ""
echo "✅ Services started!"
echo ""
echo "📊 Service Status:"
echo "   - Database: http://localhost:5432"
echo "   - Redis: http://localhost:6379"
echo "   - FastAPI: http://localhost:8000"
echo "   - Go Service: http://localhost:9000"
echo "   - Flower: http://localhost:5555"
echo ""
echo "📝 Next steps:"
echo "   1. Setup Nginx Reverse Proxy Manager (see NGINX-RPM-SETUP.md)"
echo "   2. Configure SSL certificates"
echo "   3. Test all endpoints"
echo ""
echo "📋 View logs: docker compose logs -f"
echo "🛑 Stop services: docker compose down"

