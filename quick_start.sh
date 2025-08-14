#!/bin/bash

# Quick Start Script for YOLO Camera Stream
# Minimal checks and fast startup

echo "🚀 Quick Start: YOLO Camera Stream"
echo "==================================="

# Check essential files
if [ ! -f "yolov8n.hef" ]; then
    echo "❌ Error: yolov8n.hef file not found!"
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found!"
    exit 1
fi

# Build and run
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting YOLO camera stream..."
echo "📡 Stream: udp://192.168.0.173:5000"
echo "⏹️  Press Ctrl+C to stop"
echo

docker-compose up 