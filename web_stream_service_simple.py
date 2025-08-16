#!/usr/bin/env python3
"""
Simple web service for displaying video stream
Minimal interface - just shows the video as requested by user
"""

import cv2
import numpy as np
import time
import socket
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
    </style>
</head>
<body>
    <div class="video-container">
        <img src="/stream" class="video-stream" alt="Video Stream">
        <div class="status">📹 Поток видео с камеры CM5</div>
    </div>
</body>
</html>
"""

class VideoStreamer:
    def __init__(self):
        self.udp_socket = None
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def start_udp_listener(self):
        """Start listening to UDP stream from libcamera-vid"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            
            self.running = True
            listener_thread = threading.Thread(target=self._udp_listener_loop)
            listener_thread.daemon = True
            listener_thread.start()
            
            print("✅ UDP listener started on port 5000")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start UDP listener: {e}")
            return False
    
    def _udp_listener_loop(self):
        """Main UDP listening loop"""
        buffer = b''
        
        while self.running:
            try:
                # Receive H.264 data
                data, addr = self.udp_socket.recvfrom(65536)
                
                if data:
                    buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(buffer) > 1000:  # Minimum size for H.264 frame
                        frame = self._decode_h264_frame(buffer)
                        if frame is not None:
                            with self.frame_lock:
                                self.current_frame = frame
                            buffer = b''  # Clear buffer after successful decode
                            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ UDP listener error: {e}")
                break
        
        print("🛑 UDP listener stopped")
    
    def _decode_h264_frame(self, h264_data):
        """Decode H.264 data to OpenCV frame"""
        try:
            # Write H.264 data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(h264_data)
                temp_file_path = temp_file.name
            
            # Try to read with OpenCV
            cap = cv2.VideoCapture(temp_file_path)
            
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                
                if ret and frame is not None:
                    return frame
            
            # Clean up temp file if OpenCV failed
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ H.264 decode error: {e}")
        
        return None
    
    def get_current_frame(self):
        """Get the most recent decoded frame"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def stop(self):
        """Stop the video streamer"""
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()

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
    
    # Start UDP listener
    if video_streamer.start_udp_listener():
        print("✅ Video streamer started")
        print("🌐 Web interface available at http://localhost:8080")
        
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