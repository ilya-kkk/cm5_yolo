#!/usr/bin/env python3
"""
Video Web Service for YOLO Camera Stream
Simple MJPEG streaming service
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoWebService:
    def __init__(self, port: int = 8084):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
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
            max-width: 800px; 
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
        }
        .status { 
            text-align: center; 
            margin: 20px 0; 
            padding: 10px; 
            background: #e8f5e8; 
            border-radius: 5px; 
            color: #2d5a2d; 
        }
        .controls { 
            text-align: center; 
            margin: 20px 0; 
        }
        button { 
            background: #007bff; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            margin: 0 10px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
        }
        button:hover { 
            background: #0056b3; 
        }
        button:disabled { 
            background: #ccc; 
            cursor: not-allowed; 
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 YOLO Video Stream</h1>
        
        <div class="status" id="status">
            📡 Подключение к камере...
        </div>
        
        <div class="video-container">
            <img id="videoStream" class="video-stream" src="/video_feed" alt="Video Stream">
        </div>
        
        <div class="controls">
            <button onclick="startStream()" id="startBtn">▶️ Запустить</button>
            <button onclick="stopStream()" id="stopBtn" disabled>⏹️ Остановить</button>
            <button onclick="refreshStream()" id="refreshBtn">🔄 Обновить</button>
        </div>
    </div>

    <script>
        let streamActive = false;
        let statusInterval;
        
        function updateStatus(message, isError = false) {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.style.background = isError ? '#ffe8e8' : '#e8f5e8';
            statusEl.style.color = isError ? '#5a2d2d' : '#2d5a2d';
        }
        
        function startStream() {
            if (streamActive) return;
            
            const videoEl = document.getElementById('videoStream');
            videoEl.src = '/video_feed?' + new Date().getTime();
            
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            
            streamActive = true;
            updateStatus('✅ Стрим запущен');
            
            // Start status monitoring
            statusInterval = setInterval(checkStatus, 5000);
        }
        
        function stopStream() {
            if (!streamActive) return;
            
            const videoEl = document.getElementById('videoStream');
            videoEl.src = '';
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            
            streamActive = false;
            updateStatus('⏹️ Стрим остановлен');
            
            if (statusInterval) {
                clearInterval(statusInterval);
                statusInterval = null;
            }
        }
        
        function refreshStream() {
            if (streamActive) {
                stopStream();
                setTimeout(startStream, 100);
            } else {
                startStream();
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/status');
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'Running') {
                        updateStatus(`✅ Стрим активен | Кадр: ${data.latest_frame}`);
                    } else {
                        updateStatus('⚠️ Стрим не активен', true);
                    }
                } else {
                    updateStatus('❌ Ошибка получения статуса', true);
                }
            } catch (error) {
                updateStatus('❌ Ошибка подключения', true);
            }
        }
        
        // Auto-start stream
        window.onload = function() {
            setTimeout(startStream, 1000);
        };
        
        // Handle video errors
        document.getElementById('videoStream').onerror = function() {
            updateStatus('❌ Ошибка загрузки видео', true);
        };
        
        document.getElementById('videoStream').onload = function() {
            updateStatus('✅ Видео загружено');
        };
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
                frame_path = self.get_latest_frame_path()
                if frame_path and frame_path.exists():
                    try:
                        with open(frame_path, 'rb') as f:
                            frame_data = f.read()
                        
                        # Send frame as MJPEG
                        frame_header = f'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame_data)}\r\n\r\n'
                        await response.write(frame_header.encode())
                        await response.write(frame_data)
                        await response.write(b'\r\n')
                        
                        # Small delay between frames
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"Error reading frame: {e}")
                        break
                else:
                    # No frame available, wait a bit
                    await asyncio.sleep(0.5)
                    
        except asyncio.CancelledError:
            logger.info("Video stream cancelled")
        except Exception as e:
            logger.error(f"Video stream error: {e}")
        finally:
            await response.write_eof()
            
    async def status_handler(self, request):
        """Return current status"""
        status = {
            'status': 'Running',
            'timestamp': time.time(),
            'latest_frame': self.get_latest_frame_number(),
            'frames_available': self.count_available_frames()
        }
        return web.json_response(status)
        
    def get_latest_frame_path(self) -> Optional[Path]:
        """Get the path to the latest processed frame"""
        try:
            frame_files = list(Path('/tmp').glob('processed_frame_*.jpg'))
            if frame_files:
                latest_frame = max(frame_files, key=lambda x: x.stat().st_mtime)
                return latest_frame
        except Exception as e:
            logger.error(f"Error getting latest frame: {e}")
        return None
        
    def get_latest_frame_number(self) -> int:
        """Get the number of the latest frame"""
        frame_path = self.get_latest_frame_path()
        if frame_path:
            try:
                frame_name = frame_path.stem
                frame_num = int(frame_name.split('_')[-1])
                return frame_num
            except (ValueError, IndexError):
                pass
        return 0
        
    def count_available_frames(self) -> int:
        """Count available frames in /tmp"""
        try:
            frame_files = list(Path('/tmp').glob('processed_frame_*.jpg'))
            return len(frame_files)
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