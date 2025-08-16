#!/usr/bin/env python3
"""
Web Service for YOLO Camera Stream
Provides a web interface to view the processed video stream from mobile devices
"""

from flask import Flask, render_template_string, Response, jsonify
import cv2
import numpy as np
import threading
import time
import socket
import struct
import os
import subprocess
import tempfile

# Import configuration
try:
    from web_service_config import get_config, get_web_service_config, get_h264_config
    CONFIG = get_config()
    WEB_CONFIG = get_web_service_config()
    H264_CONFIG = get_h264_config()
except ImportError:
    # Default configuration if config file is not available
    CONFIG = {
        'web_service': {
            'host': '0.0.0.0',
            'port': 8080,
            'debug': False,
            'threaded': True,
        },
        'h264': {
            'udp_host': '0.0.0.0',
            'udp_port': 5000,
            'max_buffer_size': 1024 * 1024,
            'keep_buffer_size': 512 * 1024,
        }
    }
    WEB_CONFIG = CONFIG['web_service']
    H264_CONFIG = CONFIG['h264']

app = Flask(__name__)

class H264VideoReceiver:
    def __init__(self, host=None, port=None):
        self.host = host or H264_CONFIG.get('udp_host', '0.0.0.0')
        self.port = port or H264_CONFIG.get('udp_port', 5000)
        self.socket = None
        self.running = False
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Configuration
        self.max_buffer_size = H264_CONFIG.get('max_buffer_size', 1024 * 1024)
        self.keep_buffer_size = H264_CONFIG.get('keep_buffer_size', 512 * 1024)
        self.nal_start_codes = H264_CONFIG.get('nal_unit_start_codes', [
            b'\x00\x00\x00\x01',  # 4-byte start code
            b'\x00\x00\x01',      # 3-byte start code
        ])
        
    def start(self):
        """Start H.264 video receiver"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.socket.bind((self.host, self.port))
            self.running = True
            
            print(f"H.264 Video Receiver started on {self.host}:{self.port}")
            
            # Start receiving thread
            receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            receive_thread.start()
            
        except Exception as e:
            print(f"Failed to start H.264 receiver: {e}")
            self.running = False
    
    def _receive_loop(self):
        """Main receiving loop for H.264 packets"""
        buffer = b''
        
        while self.running:
            try:
                # Receive UDP packet
                data, addr = self.socket.recvfrom(65536)
                
                if data:
                    buffer += data
                    
                    # Look for H.264 NAL unit start codes
                    while True:
                        # Find start code
                        start_pos = -1
                        for start_code in self.nal_start_codes:
                            pos = buffer.find(start_code)
                            if pos != -1:
                                start_pos = pos
                                break
                        
                        if start_pos == -1:
                            # No complete NAL unit found, keep buffer
                            break
                        
                        # Extract NAL unit
                        if start_pos > 0:
                            nal_unit = buffer[:start_pos]
                            buffer = buffer[start_pos:]
                            
                            # Process NAL unit
                            self._process_nal_unit(nal_unit)
                        else:
                            # Start code at beginning, wait for more data
                            break
                    
                    # Limit buffer size
                    if len(buffer) > self.max_buffer_size:
                        buffer = buffer[-self.keep_buffer_size:]
                        
            except Exception as e:
                if self.running:
                    print(f"Error receiving H.264 data: {e}")
                time.sleep(0.01)
    
    def _process_nal_unit(self, nal_unit):
        """Process H.264 NAL unit"""
        try:
            # Try to decode with OpenCV
            nparr = np.frombuffer(nal_unit, np.uint8)
            
            # Use VideoCapture to decode H.264
            temp_file = tempfile.NamedTemporaryFile(suffix='.h264', delete=False)
            temp_file.write(nal_unit)
            temp_file.close()
            
            cap = cv2.VideoCapture(temp_file.name)
            ret, frame = cap.read()
            cap.release()
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            if ret and frame is not None:
                with self.frame_lock:
                    self.latest_frame = frame
                    
                    # Update FPS counter
                    self.fps_counter += 1
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        self.current_fps = self.fps_counter
                        self.fps_counter = 0
                        self.last_fps_time = current_time
                        
        except Exception as e:
            # Ignore decode errors for individual NAL units
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
    
    def stop(self):
        """Stop H.264 receiver"""
        self.running = False
        if self.socket:
            self.socket.close()

# Global H.264 receiver instance
h264_receiver = H264VideoReceiver()

def generate_frames():
    """Generate video frames for streaming"""
    target_width = WEB_CONFIG.get('target_width', 640)
    target_height = WEB_CONFIG.get('target_height', 480)
    jpeg_quality = WEB_CONFIG.get('jpeg_quality', 85)
    target_fps = WEB_CONFIG.get('target_fps', 30)
    frame_interval = 1.0 / target_fps
    
    while True:
        frame = h264_receiver.get_latest_frame()
        
        if frame is not None:
            # Resize frame for web display
            frame = cv2.resize(frame, (target_width, target_height))
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
            
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(frame_interval)

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
            
            @media (max-width: 768px) {
                .container {
                    padding: 20px;
                    margin: 10px;
                }
                
                h1 {
                    font-size: 2em;
                }
                
                .controls {
                    flex-direction: column;
                    align-items: center;
                }
                
                .btn {
                    width: 100%;
                    max-width: 300px;
                }
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
            
            function refreshStream() {
                const img = document.getElementById('video-stream');
                const loading = document.getElementById('loading');
                
                loading.style.display = 'block';
                img.style.display = 'none';
                
                document.getElementById('status-text').textContent = 'Обновление потока...';
                
                // Add timestamp to prevent caching
                img.src = '/stream?' + new Date().getTime();
                
                img.onload = function() {
                    loading.style.display = 'none';
                    img.style.display = 'block';
                    document.getElementById('status-text').textContent = 'Поток активен';
                    updateConnectionStatus(true);
                };
                
                img.onerror = function() {
                    loading.style.display = 'none';
                    img.style.display = 'none';
                    document.getElementById('status-text').textContent = 'Ошибка загрузки потока';
                    updateConnectionStatus(false);
                };
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
                        if (data.status === 'healthy') {
                            updateConnectionStatus(true);
                        } else {
                            updateConnectionStatus(false);
                        }
                    })
                    .catch(() => {
                        updateConnectionStatus(false);
                    });
            }
            
            // Initial setup
            refreshStream();
            startAutoRefresh();
            
            // Update FPS counter
            setInterval(updateFPS, 100);
            
            // Health check every 10 seconds
            setInterval(checkHealth, 10000);
            
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
        host = WEB_CONFIG.get('host', '0.0.0.0')
        port = WEB_CONFIG.get('port', 8080)
        debug = WEB_CONFIG.get('debug', False)
        threaded = WEB_CONFIG.get('threaded', True)
        
        print("Starting web service...")
        print(f"Configuration: {CONFIG}")
        print(f"Web service will be available at: http://{host}:{port}")
        print("Access the stream at: http://<CM5_IP>:8080")
        
        app.run(host=host, port=port, debug=debug, threaded=threaded)
        
    except KeyboardInterrupt:
        print("Stopping web service...")
        h264_receiver.stop()
    except Exception as e:
        print(f"Error starting web service: {e}")
        h264_receiver.stop()

if __name__ == '__main__':
    start_web_service() 