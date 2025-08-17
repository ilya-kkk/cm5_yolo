#!/bin/bash
# Script to start camera stream and send to Hailo YOLO processor

echo "🚀 Starting Hailo YOLO camera stream..."

# Check if Hailo YOLO processor is running
if ! pgrep -f "hailo_yolo_main.py" > /dev/null; then
    echo "❌ Hailo YOLO processor not running. Start it first with:"
    echo "   docker compose up yolo-camera-stream"
    exit 1
fi

echo "✅ Hailo YOLO processor is running"

# Check camera availability
if ! v4l2-ctl --list-devices | grep -q "ov5647"; then
    echo "⚠️ OV5647 camera not detected, trying to enable it..."
    
    # Try to enable camera
    sudo v4l2-ctl --device /dev/video0 --set-fmt-video=width=640,height=480,pixelformat=MJPG
    if [ $? -eq 0 ]; then
        echo "✅ Camera enabled"
    else
        echo "❌ Failed to enable camera"
        exit 1
    fi
fi

# Set camera parameters
echo "📷 Configuring camera..."
v4l2-ctl --device /dev/video0 \
    --set-fmt-video=width=640,height=480,pixelformat=MJPG \
    --set-ctrl=exposure_auto=1 \
    --set-ctrl=exposure_time_absolute=1000 \
    --set-ctrl=gain=100

# Start camera stream and send to Hailo YOLO
echo "📺 Starting camera stream to UDP port 5000..."
libcamera-vid \
    --camera 0 \
    --width 640 \
    --height 480 \
    --framerate 30 \
    --codec mjpeg \
    --inline \
    --nopreview \
    --output - | \
    ffmpeg -f mjpeg -i - -f mjpeg - | \
    socat - UDP-SENDTO:127.0.0.1:5000

echo "✅ Camera stream started and sent to Hailo YOLO processor"
echo "💡 Check /tmp/yolo_frames/ for processed images"
echo "🔄 Press Ctrl+C to stop" 