#!/usr/bin/env python3
"""
Video Web Service for YOLO Camera Stream
Real-time MJPEG streaming of processed video frames
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional
import threading

import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoWebService:
    def __init__(self, port: int = 8085):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.last_frame_time = 0
        self.frame_cache = {}
        
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/video_feed', self.video_feed_handler)
        self.app.router.add_get('/status', self.status_handler)
        
    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>YOLO Video Stream</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: #f0f0f0; 
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        h1 { 
            color: #333; 
            text-align: center; 
            margin-bottom: 30px; 
        }
        .video-container { 
            text-align: center; 
            margin: 20px 0; 
        }
        .video-stream { 
            max-width: 100%; 
            height: auto; 
            border: 2px solid #ddd; 
            border-radius: 8px; 
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .status { 
            text-align: center; 
            margin: 20px 0; 
            padding: 15px; 
            background: #e8f5e8; 
            border-radius: 5px; 
            color: #2d5a2d; 
            font-weight: bold;
        }
        .controls { 
            text-align: center; 
            margin: 20px 0; 
        }
        button { 
            background: #007bff; 
            color: white; 
            border: none; 
            padding: 12px 24px; 
            margin: 0 10px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
            transition: background 0.3s;
        }
        button:hover { 
            background: #0056b3; 
        }
        button:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
        }
        .info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #007bff;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #dc3545;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 YOLO Video Stream - Raspberry Pi CM5</h1>
        
        <div class="info">
            <strong>📡 Статус:</strong> <span id="status">Запуск стрима...</span><br>
            <strong>📊 FPS:</strong> <span id="fps">-</span><br>
            <strong>🖼️ Кадров доступно:</strong> <span id="frameCount">-</span>
        </div>
        
        <div class="video-container">
            <img id="videoStream" class="video-stream" src="/video_feed" alt="YOLO Video Stream">
        </div>
        
        <div class="controls">
            <button onclick="refreshStream()" id="refreshBtn">🔄 Обновить стрим</button>
            <button onclick="checkStatus()" id="statusBtn">📊 Проверить статус</button>
        </div>
        
        <div class="info">
            <strong>ℹ️ Информация:</strong><br>
            • Видео обрабатывается в реальном времени с помощью YOLOv8<br>
            • Камера CSI подключена через MIPI интерфейс<br>
            • Обработанные кадры сохраняются в /tmp/processed_frame_*.jpg<br>
            • Веб-интерфейс обновляется автоматически
        </div>
    </div>

    <script>
        let frameCount = 0;
        let lastFrameTime = Date.now();
        
        function refreshStream() {
            const videoEl = document.getElementById('videoStream');
            const timestamp = new Date().getTime();
            videoEl.src = '/video_feed?' + timestamp;
            document.getElementById('status').textContent = '✅ Стрим обновлен';
            updateFPS();
        }
        
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('frameCount').textContent = data.frames_available;
                    document.getElementById('status').textContent = '✅ Статус обновлен';
                })
                .catch(error => {
                    document.getElementById('status').textContent = '❌ Ошибка получения статуса';
                    console.error('Error:', error);
                });
        }
        
        function updateFPS() {
            const now = Date.now();
            const delta = now - lastFrameTime;
            if (delta > 0) {
                const fps = Math.round(1000 / delta);
                document.getElementById('fps').textContent = fps + ' FPS';
            }
            lastFrameTime = now;
            frameCount++;
        }
        
        // Auto-start stream
        window.onload = function() {
            document.getElementById('status').textContent = '✅ Стрим запущен';
            checkStatus();
            // Update status every 5 seconds
            setInterval(checkStatus, 5000);
        };
        
        // Handle video events
        document.getElementById('videoStream').onerror = function() {
            document.getElementById('status').textContent = '❌ Ошибка загрузки видео';
        };
        
        document.getElementById('videoStream').onload = function() {
            updateFPS();
        };
        
        // Auto-refresh stream every 30 seconds to prevent timeouts
        setInterval(refreshStream, 30000);
    </script>
</body>
</html>
        """
        return web.Response(text=html_content, content_type='text/html')
        
    async def video_feed_handler(self, request):
        """Stream video frames as MJPEG"""
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
        await response.prepare(request)
        
        try:
            while True:
                frame_path = self.get_latest_valid_frame_path()
                if frame_path and frame_path.exists():
                    try:
                        # Check if file is valid JPEG (size > 1KB)
                        file_size = frame_path.stat().st_size
                        if file_size < 1024:
                            logger.warning(f"Frame {frame_path} too small ({file_size} bytes), skipping")
                            await asyncio.sleep(0.1)
                            continue
                        
                        with open(frame_path, 'rb') as f:
                            frame_data = f.read()
                        
                        # Verify frame data is not empty
                        if len(frame_data) == 0:
                            logger.warning(f"Frame {frame_path} is empty, skipping")
                            await asyncio.sleep(0.1)
                            continue
                        
                        # Send frame as MJPEG
                        frame_header = f'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame_data)}\r\n\r\n'
                        await response.write(frame_header.encode())
                        await response.write(frame_data)
                        await response.write(b'\r\n')
                        
                        # Update last frame time
                        self.last_frame_time = time.time()
                        
                        # Adaptive frame rate based on available frames
                        await asyncio.sleep(0.1)  # 10 FPS for smooth streaming
                        
                    except Exception as e:
                        logger.error(f"Error reading frame {frame_path}: {e}")
                        await asyncio.sleep(0.5)
                else:
                    # No valid frame available, send placeholder
                    logger.info("No valid frames available, sending placeholder")
                    placeholder = b'--frame\r\nContent-Type: text/plain\r\nContent-Length: 8\r\n\r\nNo Frame\r\n'
                    await response.write(placeholder)
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Video stream cancelled")
        except Exception as e:
            logger.error(f"Video stream error: {e}")
        finally:
            try:
                await response.write_eof()
            except:
                pass
            
    async def status_handler(self, request):
        """Return current status"""
        status = {
            'status': 'Running',
            'timestamp': time.time(),
            'latest_frame': self.get_latest_frame_number(),
            'frames_available': self.count_valid_frames(),
            'last_frame_time': self.last_frame_time,
            'uptime': time.time() - self.last_frame_time if self.last_frame_time > 0 else 0
        }
        return web.json_response(status)
        
    def get_latest_valid_frame_path(self) -> Optional[Path]:
        """Get the path to the latest valid processed frame"""
        try:
            frame_files = list(Path('/tmp').glob('processed_frame_*.jpg'))
            if frame_files:
                # Filter valid frames (size > 1KB)
                valid_frames = [f for f in frame_files if f.stat().st_size > 1024]
                if valid_frames:
                    latest_frame = max(valid_frames, key=lambda x: x.stat().st_mtime)
                    return latest_frame
        except Exception as e:
            logger.error(f"Error getting latest frame: {e}")
        return None
        
    def get_latest_frame_number(self) -> int:
        """Get the number of the latest frame"""
        frame_path = self.get_latest_valid_frame_path()
        if frame_path:
            try:
                frame_name = frame_path.stem
                frame_num = int(frame_name.split('_')[-1])
                return frame_num
            except (ValueError, IndexError):
                pass
        return 0
        
    def count_valid_frames(self) -> int:
        """Count valid frames in /tmp (size > 1KB)"""
        try:
            frame_files = list(Path('/tmp').glob('processed_frame_*.jpg'))
            valid_frames = [f for f in frame_files if f.stat().st_size > 1024]
            return len(valid_frames)
        except Exception:
            return 0
        
    async def run(self):
        """Run the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Video Web Service started on http://0.0.0.0:{self.port}")
        logger.info(f"Access from other devices using: http://<CM5_IP>:{self.port}")
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()

if __name__ == "__main__":
    service = VideoWebService()
    asyncio.run(service.run()) 