#!/usr/bin/env python3
"""
Video Web Service for YOLO Camera Stream
Simple MJPEG streaming service with test frame generator
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
        self.start_test_frame_generator()
        
    def start_test_frame_generator(self):
        """Start generating test frames in background"""
        def generate_frames():
            frame_num = 0
            while True:
                try:
                    # Create a simple test frame using basic Python
                    frame_path = f"/tmp/processed_frame_{frame_num}.jpg"
                    
                    # Create a simple colored frame (640x480)
                    # Using basic file operations to avoid PIL issues
                    self.create_simple_frame(frame_path, frame_num)
                    
                    # Keep only last 50 frames to avoid disk space issues
                    old_frames = [f for f in Path('/tmp').glob('processed_frame_*.jpg')]
                    if len(old_frames) > 50:
                        for old_frame in sorted(old_frames)[:-50]:
                            try:
                                old_frame.unlink()
                            except:
                                pass
                    
                    frame_num += 1
                    time.sleep(0.2)  # 5 FPS - slower to avoid crashes
                    
                except Exception as e:
                    logger.error(f"Error generating test frame: {e}")
                    time.sleep(2)  # Wait longer on error
        
        # Start frame generator in background thread
        frame_thread = threading.Thread(target=generate_frames, daemon=True)
        frame_thread.start()
        logger.info("Test frame generator started")
        
    def create_simple_frame(self, frame_path: str, frame_num: int):
        """Create a simple test frame without PIL"""
        try:
            # Create a simple colored frame using basic operations
            # This is a fallback when PIL is not working properly
            
            # For now, just create an empty file to avoid errors
            # The video feed will show a placeholder
            with open(frame_path, 'w') as f:
                f.write(f"Test Frame {frame_num}")
                
        except Exception as e:
            logger.error(f"Error creating simple frame: {e}")
            # Create a minimal file to prevent crashes
            try:
                with open(frame_path, 'w') as f:
                    f.write("frame")
            except:
                pass
        
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
            📡 Запуск стрима...
        </div>
        
        <div class="video-container">
            <img id="videoStream" class="video-stream" src="/video_feed" alt="Video Stream">
        </div>
        
        <div class="controls">
            <button onclick="refreshStream()" id="refreshBtn">🔄 Обновить</button>
        </div>
    </div>

    <script>
        function refreshStream() {
            const videoEl = document.getElementById('videoStream');
            videoEl.src = '/video_feed?' + new Date().getTime();
            document.getElementById('status').textContent = '✅ Стрим обновлен';
        }
        
        // Auto-start stream
        window.onload = function() {
            document.getElementById('status').textContent = '✅ Стрим запущен';
        };
        
        // Handle video errors
        document.getElementById('videoStream').onerror = function() {
            document.getElementById('status').textContent = '❌ Ошибка загрузки видео';
        };
        
        document.getElementById('videoStream').onload = function() {
            document.getElementById('status').textContent = '✅ Видео загружено';
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
                        
                        # Slower frame rate for stability
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Error reading frame: {e}")
                        # Send a simple error frame
                        error_frame = b'--frame\r\nContent-Type: text/plain\r\nContent-Length: 5\r\n\r\nError\r\n'
                        await response.write(error_frame)
                        await asyncio.sleep(1)
                else:
                    # No frame available, send placeholder
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