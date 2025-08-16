#!/bin/bash

# YOLO Camera Stream Starter Script
# This script tests components and starts the YOLO camera stream

set -e  # Exit on any error

echo "🚀 YOLO Camera Stream Starter"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_status "WARN" "Running as root - this may cause permission issues"
fi

# Check if HEF file exists
if [ ! -f "yolov8n.hef" ]; then
    print_status "ERROR" "yolov8n.hef file not found!"
    echo "Please ensure the HEF file is in the current directory."
    exit 1
fi

print_status "OK" "HEF file found: yolov8n.hef"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_status "ERROR" "Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

print_status "OK" "Docker is running"

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_status "ERROR" "Docker Compose is not installed!"
    echo "Please install Docker Compose and try again."
    exit 1
fi

print_status "OK" "Docker Compose is available"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ]; then
    print_status "ERROR" "Docker files not found!"
    echo "Please run this script from the project root directory."
    exit 1
fi

print_status "OK" "Project files found"

# Test camera (optional)
read -p "Do you want to test the camera first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "INFO" "Testing camera..."
    if python3 test_camera.py; then
        print_status "OK" "Camera test passed"
    else
        print_status "WARN" "Camera test failed - continuing anyway"
    fi
fi

# Test Hailo (optional)
read -p "Do you want to test Hailo 8L first? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "INFO" "Testing Hailo 8L..."
    if python3 test_hailo.py; then
        print_status "OK" "Hailo test passed"
    else
        print_status "WARN" "Hailo test failed - continuing anyway"
    fi
fi

# Build Docker image
print_status "INFO" "Building Docker image..."
if docker-compose build; then
    print_status "OK" "Docker image built successfully"
else
    print_status "ERROR" "Failed to build Docker image"
    exit 1
fi

# Start the service
print_status "INFO" "Starting YOLO camera stream..."
echo
echo "Stream will be available at: udp://192.168.0.173:5000"
echo "Press Ctrl+C to stop the stream"
echo

# Run the container
if docker-compose up; then
    print_status "OK" "YOLO camera stream completed successfully"
else
    print_status "ERROR" "YOLO camera stream failed"
    exit 1
fi

echo
print_status "INFO" "YOLO camera stream stopped" 