#!/usr/bin/env python3
"""
Fixed Web Service for YOLO Camera Stream
Properly handles H.264 UDP stream from libcamera-vid
"""

from flask import Flask, render_template_string, Response, jsonify
import cv2
import numpy as np
import threading
import time
import socket
import subprocess
import tempfile
import os

app = Flask(__name__)

class H264StreamReceiver:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # H.264 stream buffer
        self.h264_buffer = b''
        self.frame_ready = threading.Event()
        
    def start(self):
        """Start H.264 stream receiver"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            print(f"H.264 Stream Receiver started on {self.host}:{self.port}")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
        except Exception as e:
            print(f"Failed to start H.264 receiver: {e}")
            self.running = False
    
    def _receive_loop(self):
        """Main receiving loop for H.264 stream"""
        while self.running:
            try:
                # Receive UDP packet
                data, addr = self.socket.recvfrom(65536)
                
                if data:
                    # Add to H.264 buffer
                    self.h264_buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(self.h264_buffer) > 1000:  # Minimum size for a frame
                        self._try_decode_frame()
                        
                    # Limit buffer size
                    if len(self.h264_buffer) > 1024 * 1024:  # 1MB limit
                        self.h264_buffer = self.h264_buffer[-512 * 1024:]  # Keep last 512KB
                        
            except Exception as e:
                if self.running:
                    print(f"Error receiving H.264 data: {e}")
                time.sleep(0.01)
    
    def _try_decode_frame(self):
        """Try to decode H.264 frame from buffer"""
        try:
            # Create temporary H.264 file
            with tempfile.NamedTemporaryFile(suffix='.h264', delete=False) as temp_file:
                temp_file.write(self.h264_buffer)
                temp_file_path = temp_file.name
            
            # Use ffmpeg to decode H.264 to raw video
            try:
                # Try to decode with ffmpeg
                cmd = [
                    'ffmpeg',
                    '-f', 'h264',
                    '-i', temp_file_path,
                    '-f', 'rawvideo',
                    '-pix_fmt', 'bgr24',
                    '-s', '640x480',
                    '-vframes', '1',
                    '-y',  # Overwrite output
                    '/tmp/decoded_frame.raw'
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                
                if result.returncode == 0 and os.path.exists('/tmp/decoded_frame.raw'):
                    # Read decoded frame
                    with open('/tmp/decoded_frame.raw', 'rb') as f:
                        raw_data = f.read()
                    
                    if len(raw_data) == 640 * 480 * 3:  # BGR24 format
                        # Convert to numpy array
                        frame = np.frombuffer(raw_data, dtype=np.uint8).reshape(480, 640, 3)
                        
                        with self.frame_lock:
                            self.latest_frame = frame
                            
                            # Update FPS counter
                            self.fps_counter += 1
                            current_time = time.time()
                            if current_time - self.last_fps_time >= 1.0:
                                self.current_fps = self.fps_counter
                                self.fps_counter = 0
                                self.last_fps_time = current_time
                        
                        # Signal that frame is ready
                        self.frame_ready.set()
                        
                        # Clear buffer after successful decode
                        self.h264_buffer = b''
                        
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # ffmpeg not available, try alternative method
                pass
            
            # Clean up temp files
            try:
                os.unlink(temp_file_path)
                if os.path.exists('/tmp/decoded_frame.raw'):
                    os.unlink('/tmp/decoded_frame.raw')
            except:
                pass
                
        except Exception as e:
            # Ignore decode errors
            pass
    
    def get_latest_frame(self):
        """Get the latest received frame"""
        with self.frame_lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
        return None
    
    def get_fps(self):
        """Get current FPS"""
        return self.current_fps
    
    def wait_for_frame(self, timeout=1.0):
        """Wait for a new frame to be available"""
        return self.frame_ready.wait(timeout)
    
    def stop(self):
        """Stop H.264 receiver"""
        self.running = False
        if self.socket:
            self.socket.close()

# Global H.264 receiver instance
h264_receiver = H264StreamReceiver()

def generate_frames():
    """Generate video frames for streaming"""
    while True:
        # Wait for new frame
        if h264_receiver.wait_for_frame(1.0):
            frame = h264_receiver.get_latest_frame()
            
            if frame is not None:
                # Encode frame as JPEG
                ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.033)  # ~30 FPS

@app.route('/')
def index():
    """Main page with video stream"""
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YOLO Camera Stream</title>
        <style>
            body {
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                max-width: 800px;
                width: 100%;
                text-align: center;
            }
            
            h1 {
                color: #333;
                margin-bottom: 30px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .video-container {
                position: relative;
                margin: 20px 0;
                border-radius: 15px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
                background: #000;
                min-height: 400px;
            }
            
            .video-stream {
                width: 100%;
                max-width: 640px;
                height: auto;
                border-radius: 15px;
                display: block;
            }
            
            .status {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 4px solid #28a745;
            }
            
            .controls {
                display: flex;
                gap: 15px;
                justify-content: center;
                flex-wrap: wrap;
                margin: 20px 0;
            }
            
            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 25px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                font-size: 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
            }
            
            .btn-secondary {
                background: linear-gradient(45deg, #6c757d, #495057);
            }
            
            .btn-success {
                background: linear-gradient(45deg, #28a745, #20c997);
            }
            
            .info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 4px solid #2196f3;
            }
            
            .fps-counter {
                position: absolute;
                top: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
                backdrop-filter: blur(10px);
            }
            
            .connection-status {
                position: absolute;
                top: 10px;
                left: 10px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                backdrop-filter: blur(10px);
            }
            
            .status-online {
                background: rgba(40, 167, 69, 0.9);
            }
            
            .status-offline {
                background: rgba(220, 53, 69, 0.9);
            }
            
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #666;
            }
            
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .no-stream {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 400px;
                color: #666;
                font-size: 18px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎥 YOLO Camera Stream</h1>
            
            <div class="status">
                <strong>Статус:</strong> 
                <span id="status-text">Подключение...</span>
            </div>
            
            <div class="video-container">
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <div>Загрузка видео потока...</div>
                </div>
                <div class="no-stream" id="no-stream">
                    <div>
                        <div style="font-size: 48px; margin-bottom: 20px;">📹</div>
                        <div>Ожидание видео потока...</div>
                        <div style="font-size: 14px; margin-top: 10px; color: #999;">
                            Убедитесь, что YOLO сервис запущен и стримит на UDP порт 5000
                        </div>
                    </div>
                </div>
                <img id="video-stream" class="video-stream" alt="Video Stream" style="display: none;">
                <div class="fps-counter" id="fps-counter">0 FPS</div>
                <div class="connection-status status-offline" id="connection-status">ОФФЛАЙН</div>
            </div>
            
            <div class="controls">
                <button class="btn" onclick="refreshStream()">🔄 Обновить</button>
                <button class="btn btn-secondary" onclick="toggleFullscreen()">⛶ Полный экран</button>
                <button class="btn btn-success" onclick="toggleAutoRefresh()">🔄 Автообновление</button>
                <a href="/stream" class="btn" target="_blank">📱 Новое окно</a>
            </div>
            
            <div class="info">
                <strong>Информация:</strong><br>
                • Поток обрабатывается YOLOv8 на Hailo-8L<br>
                • Камера OV5647 на MIPI0 интерфейсе<br>
                • Разрешение: 640x480, 30 FPS<br>
                • Обнаружение объектов в реальном времени<br>
                • Веб-интерфейс для мобильных устройств
            </div>
        </div>
        
        <script>
            let frameCount = 0;
            let lastTime = Date.now();
            let fps = 0;
            let autoRefresh = true;
            let refreshInterval;
            let streamActive = false;
            
            function updateFPS() {
                frameCount++;
                const currentTime = Date.now();
                
                if (currentTime - lastTime >= 1000) {
                    fps = frameCount;
                    frameCount = 0;
                    lastTime = currentTime;
                    document.getElementById('fps-counter').textContent = fps + ' FPS';
                }
            }
            
            function updateConnectionStatus(online) {
                const statusElement = document.getElementById('connection-status');
                if (online) {
                    statusElement.textContent = 'ОНЛАЙН';
                    statusElement.className = 'connection-status status-online';
                } else {
                    statusElement.textContent = 'ОФФЛАЙН';
                    statusElement.className = 'connection-status status-offline';
                }
            }
            
            function showStream() {
                const img = document.getElementById('video-stream');
                const loading = document.getElementById('loading');
                const noStream = document.getElementById('no-stream');
                
                loading.style.display = 'none';
                noStream.style.display = 'none';
                img.style.display = 'block';
                
                streamActive = true;
                updateConnectionStatus(true);
                document.getElementById('status-text').textContent = 'Поток активен';
            }
            
            function hideStream() {
                const img = document.getElementById('video-stream');
                const noStream = document.getElementById('no-stream');
                
                img.style.display = 'none';
                noStream.style.display = 'flex';
                
                streamActive = false;
                updateConnectionStatus(false);
                document.getElementById('status-text').textContent = 'Поток неактивен';
            }
            
            function refreshStream() {
                const loading = document.getElementById('loading');
                
                loading.style.display = 'block';
                hideStream();
                
                document.getElementById('status-text').textContent = 'Обновление потока...';
                
                // Check if stream is available
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        if (data.frame_available) {
                            showStream();
                        } else {
                            hideStream();
                        }
                    })
                    .catch(() => {
                        hideStream();
                    });
            }
            
            function toggleFullscreen() {
                const videoContainer = document.querySelector('.video-container');
                
                if (!document.fullscreenElement) {
                    videoContainer.requestFullscreen().catch(err => {
                        console.log('Ошибка полноэкранного режима:', err);
                    });
                } else {
                    document.exitFullscreen();
                }
            }
            
            function toggleAutoRefresh() {
                autoRefresh = !autoRefresh;
                const btn = event.target;
                
                if (autoRefresh) {
                    btn.textContent = '🔄 Автообновление ВКЛ';
                    btn.className = 'btn btn-success';
                    startAutoRefresh();
                } else {
                    btn.textContent = '🔄 Автообновление ВЫКЛ';
                    btn.className = 'btn btn-secondary';
                    stopAutoRefresh();
                }
            }
            
            function startAutoRefresh() {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
                refreshInterval = setInterval(refreshStream, 5000);
            }
            
            function stopAutoRefresh() {
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
            }
            
            function checkHealth() {
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        if (data.frame_available && !streamActive) {
                            showStream();
                        } else if (!data.frame_available && streamActive) {
                            hideStream();
                        }
                    })
                    .catch(() => {
                        hideStream();
                    });
            }
            
            // Initial setup
            refreshStream();
            startAutoRefresh();
            
            // Update FPS counter
            setInterval(updateFPS, 100);
            
            // Health check every 5 seconds
            setInterval(checkHealth, 5000);
            
            // Check health on page load
            setTimeout(checkHealth, 2000);
        </script>
    </body>
    </html>
    """
    return html_template

@app.route('/stream')
def video_stream():
    """Video streaming endpoint"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    frame = h264_receiver.get_latest_frame()
    fps = h264_receiver.get_fps()
    status = "healthy" if frame is not None else "no_frame"
    return jsonify({
        "status": status,
        "timestamp": time.time(),
        "frame_available": frame is not None,
        "fps": fps,
        "stream_active": h264_receiver.running
    })

@app.route('/api/stream_info')
def stream_info():
    """Get stream information"""
    frame = h264_receiver.get_latest_frame()
    fps = h264_receiver.get_fps()
    
    return jsonify({
        "fps": fps,
        "frame_size": frame.shape if frame is not None else None,
        "stream_active": h264_receiver.running,
        "uptime": time.time() - h264_receiver.last_fps_time if h264_receiver.last_fps_time > 0 else 0
    })

def start_web_service():
    """Start the web service"""
    try:
        # Start H.264 receiver
        h264_receiver.start()
        
        # Start Flask app
        print("Starting fixed web service...")
        print("Web service will be available at: http://0.0.0.0:8080")
        print("Access the stream at: http://<CM5_IP>:8080")
        
        app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        
    except KeyboardInterrupt:
        print("Stopping web service...")
        h264_receiver.stop()
    except Exception as e:
        print(f"Error starting web service: {e}")
        h264_receiver.stop()

if __name__ == '__main__':
    start_web_service() 