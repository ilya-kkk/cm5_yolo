#!/bin/bash
# Start All Services for YOLO Camera Stream
# This script starts both the YOLO camera stream and web service

echo "🚀 Starting All YOLO Camera Services..."

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found in current directory"
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

echo "🔨 Building Docker images..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "❌ Failed to build Docker images"
    exit 1
fi

echo "📡 Starting all services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose ps

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ All services started successfully!"
    echo ""
    echo "🌐 Access your video stream at:"
    echo "   Web Interface: http://$(hostname -I | awk '{print $1}'):8080"
    echo "   UDP Stream: udp://$(hostname -I | awk '{print $1}'):5000"
    echo ""
    echo "📱 Mobile-friendly web interface available"
    echo "🔄 Auto-refresh enabled for continuous streaming"
    echo ""
    echo "To stop all services:"
    echo "   docker-compose down"
    echo ""
    echo "To view logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "To view specific service logs:"
    echo "   docker-compose logs -f yolo-camera-stream"
    echo "   docker-compose logs -f web-stream-service"
else
    echo "❌ Failed to start services"
    echo "Check logs with: docker-compose logs"
    exit 1
fi 