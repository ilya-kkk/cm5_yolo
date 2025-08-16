#!/bin/bash
# Stop Web Service for YOLO Camera Stream

echo "🛑 Stopping YOLO Camera Web Service..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    exit 1
fi

# Stop web service
echo "📡 Stopping web service container..."
docker-compose stop web-stream-service

# Check if service was stopped
if docker-compose ps web-stream-service | grep -q "Up"; then
    echo "❌ Failed to stop web service"
    echo "Try forcing stop with: docker-compose kill web-stream-service"
    exit 1
else
    echo "✅ Web service stopped successfully!"
    echo ""
    echo "To start again:"
    echo "   ./start_web_service.sh"
fi 