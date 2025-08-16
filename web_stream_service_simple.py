#!/usr/bin/env python3
"""
Simple web service for displaying video stream
Shows real YOLO-processed video from camera
"""

import cv2
import numpy as np
import time
import threading
import os
from pathlib import Path
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# HTML template - very simple, just video display
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CM5 YOLO Video Stream</title>
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
        .fps-info {
            color: #0f0;
            margin-top: 10px;
            font-size: 14px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="video-container">
        <img src="/stream" class="video-stream" alt="YOLO Video Stream">
        <div class="status">📹 Поток видео с камеры CM5 + YOLO обработка</div>
        <div class="fps-info" id="fps-info">FPS: --</div>
        <div class="info">
            Видео обрабатывается YOLOv8 на Hailo-8L в реальном времени.<br>
            Обнаружение объектов, временные метки и FPS отображаются на кадрах.<br>
            Веб-интерфейс адаптирован для мобильных устройств.
        </div>
    </div>
    
    <script>
        // Update FPS info every second
        setInterval(function() {
            fetch('/fps')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('fps-info').textContent = `FPS: ${data.fps}`;
                })
                .catch(() => {
                    document.getElementById('fps-info').textContent = 'FPS: --';
                });
        }, 1000);
    </script>
</body>
</html>
"""

class VideoStreamer:
    def __init__(self):
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.frame_path = Path("/tmp/latest_yolo_frame.jpg")
        self.fallback_frame = None
        self.last_frame_time = 0
        self.frame_interval = 0.1  # 100ms between frames
        
        # Create fallback frame
        self.fallback_frame = self._create_fallback_frame()
        
    def _create_fallback_frame(self):
        """Create a fallback frame when no real video is available"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add informative text
        cv2.putText(frame, "Waiting for Camera Stream", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(frame, "YOLO Processing Ready", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, "Check libcamera-vid on host", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        return frame
    
    def start(self):
        """Start the video streamer"""
        self.running = True
        print("✅ Video streamer started")
        print("📝 Reading real YOLO-processed frames from /tmp/latest_yolo_frame.jpg")
        return True
    
    def get_current_frame(self):
        """Get the current frame from YOLO processing"""
        with self.frame_lock:
            current_time = time.time()
            
            # Check if we should update frame (rate limiting)
            if current_time - self.last_frame_time < self.frame_interval:
                if self.current_frame is not None:
                    return self.current_frame.copy()
            
            # Try to read the latest processed frame
            if self.frame_path.exists():
                try:
                    # Read the frame
                    frame = cv2.imread(str(self.frame_path))
                    
                    if frame is not None and frame.size > 0:
                        # Check if frame is recent (less than 5 seconds old)
                        file_time = self.frame_path.stat().st_mtime
                        if current_time - file_time < 5.0:  # Frame is recent
                            self.current_frame = frame.copy()
                            self.last_frame_time = current_time
                            return frame.copy()
                        else:
                            # Frame is too old, use fallback
                            return self.fallback_frame.copy()
                    else:
                        return self.fallback_frame.copy()
                        
                except Exception as e:
                    print(f"⚠️ Error reading frame: {e}")
                    return self.fallback_frame.copy()
            else:
                # No frame file available, use fallback
                return self.fallback_frame.copy()
    
    def get_fps(self):
        """Get current processing FPS from the frame file"""
        try:
            if self.frame_path.exists():
                # Try to read FPS info from the frame file
                # This is a simple approach - in a real implementation you might use a shared memory or socket
                return {"fps": "Live", "status": "active"}
            else:
                return {"fps": "0", "status": "waiting"}
        except:
            return {"fps": "0", "status": "error"}
    
    def stop(self):
        """Stop the video streamer"""
        self.running = False

# Global video streamer instance
video_streamer = VideoStreamer()

@app.route('/')
def index():
    """Main page - shows YOLO video stream"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream')
def video_stream():
    """Video stream endpoint - MJPEG stream of YOLO processed frames"""
    def generate_frames():
        while True:
            frame = video_streamer.get_current_frame()
            
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    # Yield frame as MJPEG
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            
            # Small delay to control frame rate
            time.sleep(0.1)
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/fps')
def fps_info():
    """Get current FPS and status information"""
    return video_streamer.get_fps()

if __name__ == '__main__':
    print("🚀 Starting YOLO Video Web Service...")
    
    # Start video streamer
    if video_streamer.start():
        print("✅ Video streamer started")
        print("🌐 Web interface available at http://localhost:8080")
        print("📱 Mobile-friendly interface ready")
        print("🤖 Reading YOLO-processed frames from /tmp/latest_yolo_frame.jpg")
        
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