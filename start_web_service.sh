#!/bin/bash
# Start Web Service for YOLO Camera Stream
# This script starts the web service that displays the processed video stream

echo "🚀 Starting YOLO Camera Web Service..."

# Check if we're in the right directory
if [ ! -f "web_stream_service.py" ]; then
    echo "❌ Error: web_stream_service.py not found in current directory"
    echo "Please run this script from the cm5_yolo directory"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker first"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: docker-compose not found"
    echo "Please install docker-compose first"
    exit 1
fi

echo "📡 Starting web service container..."
docker-compose up -d web-stream-service

# Wait for service to start
echo "⏳ Waiting for web service to start..."
sleep 5

# Check service status
if docker-compose ps web-stream-service | grep -q "Up"; then
    echo "✅ Web service started successfully!"
    echo ""
    echo "🌐 Access your video stream at:"
    echo "   http://$(hostname -I | awk '{print $1}'):8080"
    echo ""
    echo "📱 Mobile-friendly interface available"
    echo "🔄 Auto-refresh enabled for continuous streaming"
    echo ""
    echo "To stop the service:"
    echo "   docker-compose stop web-stream-service"
    echo ""
    echo "To view logs:"
    echo "   docker-compose logs -f web-stream-service"
else
    echo "❌ Failed to start web service"
    echo "Check logs with: docker-compose logs web-stream-service"
    exit 1
fi 