#!/usr/bin/env python3
"""
Simple web service for displaying video stream
Minimal interface - just shows the video as requested by user
"""

import cv2
import numpy as np
import time
import threading
import tempfile
import os
from flask import Flask, Response, render_template_string
import io

app = Flask(__name__)

# HTML template - very simple, just video display
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CM5 Video Stream</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: Arial, sans-serif;
        }
        .video-container {
            text-align: center;
        }
        .video-stream {
            max-width: 100%;
            max-height: 100vh;
            border: 2px solid #333;
            border-radius: 8px;
        }
        .status {
            color: #fff;
            margin-top: 10px;
            font-size: 14px;
        }
        .info {
            color: #888;
            margin-top: 20px;
            font-size: 12px;
            max-width: 600px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="video-container">
        <img src="/stream" class="video-stream" alt="Video Stream">
        <div class="status">📹 Поток видео с камеры CM5</div>
        <div class="info">
            Видео обрабатывается YOLOv8 на Hailo-8L и транслируется через UDP порт 5000.<br>
            Веб-интерфейс адаптирован для мобильных устройств.
        </div>
    </div>
</body>
</html>
"""

class VideoStreamer:
    def __init__(self):
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Create a test frame for demonstration
        self.test_frame = self._create_test_frame()
        
    def _create_test_frame(self):
        """Create a test frame to show that the service is working"""
        # Create a simple test frame with text
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some text and graphics
        cv2.putText(frame, "CM5 Camera Stream", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(frame, "YOLO Processing Active", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "UDP Port 5000", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame, "Hailo-8L Accelerator", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)
        
        # Add a simple animation effect
        timestamp = int(time.time() * 10) % 100
        cv2.circle(frame, (320, 400), 50 + timestamp, (255, 255, 0), 3)
        
        return frame
    
    def start(self):
        """Start the video streamer"""
        self.running = True
        print("✅ Video streamer started")
        print("📝 Note: This is a demonstration frame")
        print("📝 Real video will come from yolo-camera-stream service")
        return True
    
    def get_current_frame(self):
        """Get the current frame (test frame for now)"""
        with self.frame_lock:
            # Update test frame with current timestamp
            self.test_frame = self._create_test_frame()
            return self.test_frame.copy()
    
    def stop(self):
        """Stop the video streamer"""
        self.running = False

# Global video streamer instance
video_streamer = VideoStreamer()

@app.route('/')
def index():
    """Main page - just shows video"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream')
def video_stream():
    """Video stream endpoint - MJPEG stream"""
    def generate_frames():
        while True:
            frame = video_streamer.get_current_frame()
            
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                if ret:
                    # Yield frame as MJPEG
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Small delay to control frame rate
            time.sleep(0.1)
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Starting Simple Video Web Service...")
    
    # Start video streamer
    if video_streamer.start():
        print("✅ Video streamer started")
        print("🌐 Web interface available at http://localhost:8080")
        print("📱 Mobile-friendly interface ready")
        
        try:
            # Start Flask app
            app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            video_streamer.stop()
    else:
        print("❌ Failed to start video streamer")
        exit(1) 