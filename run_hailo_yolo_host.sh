#!/bin/bash
# Script to run Hailo YOLO directly on CM5 host (without Docker)

echo "🚀 Starting Hailo YOLO directly on CM5 host..."

# Check if we're on CM5
if ! grep -q "Raspberry Pi Compute Module 5" /proc/device-tree/model 2>/dev/null; then
    echo "❌ This script must run on Raspberry Pi CM5"
    exit 1
fi

# Check if Hailo device is available
if ! lspci | grep -i hailo > /dev/null; then
    echo "❌ Hailo device not found in PCI"
    echo "PCI devices:"
    lspci | head -10
    exit 1
fi

echo "✅ Hailo device found in PCI"

# Check if Hailo Platform is installed
if ! python3 -c "import hailo_platform" 2>/dev/null; then
    echo "❌ Hailo Platform not installed"
    echo "Please install Hailo Platform first:"
    echo "  sudo apt update"
    echo "  sudo apt install hailo-platform"
    exit 1
fi

echo "✅ Hailo Platform installed"

# Check if HEF file exists
if [ ! -f "yolov8n.hef" ]; then
    echo "❌ HEF file not found"
    echo "Please ensure yolov8n.hef is in the current directory"
    exit 1
fi

echo "✅ HEF file found"

# Check if camera is available
if ! v4l2-ctl --list-devices | grep -q "ov5647"; then
    echo "⚠️ OV5647 camera not detected, trying to enable it..."
    
    # Try to enable camera
    sudo v4l2-ctl --device /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=MJPG 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Camera enabled"
    else
        echo "❌ Failed to enable camera"
        exit 1
    fi
fi

echo "✅ Camera available"

# Set camera parameters
echo "📷 Configuring camera..."
v4l2-ctl --device /dev/video0 \
    --set-fmt-video=width=640,height=480,pixelformat=MJPG \
    --set-ctrl=exposure_auto=1 \
    --set-ctrl=exposure_time_absolute=1000 \
    --set-ctrl=gain=100 2>/dev/null

# Create output directory
mkdir -p /tmp/yolo_frames

# Start Hailo YOLO processor
echo "🚀 Starting Hailo YOLO processor..."
python3 hailo_yolo_main.py

echo "✅ Hailo YOLO processor started"
echo "💡 Check /tmp/yolo_frames/ for processed images"
echo "🔄 Press Ctrl+C to stop" 