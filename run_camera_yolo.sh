#!/bin/bash

# YOLO Camera Stream Runner Script
# This script runs the YOLO camera stream with Hailo 8L

echo "Starting YOLO Camera Stream with Hailo 8L..."

# Check if HEF file exists
if [ ! -f "yolov8n.hef" ]; then
    echo "Error: yolov8n.hef file not found!"
    echo "Please ensure the HEF file is in the current directory."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

# Build and run the container
echo "Building Docker container..."
docker-compose build

echo "Starting YOLO camera stream..."
echo "Stream will be available at: udp://192.168.0.173:5000"
echo "Press Ctrl+C to stop the stream"

# Run the container
docker-compose up

echo "YOLO camera stream stopped." 