#!/usr/bin/env python3
"""
WebRTC Video Viewer for YOLO Camera Stream
Clean and simple implementation
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

class WebRTCVideoViewer:
    def __init__(self, port: int = 8083):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/status', self.status_handler)
        self.app.router.add_get('/frame', self.frame_handler)
        
        # Add CORS middleware
        self.app.middlewares.append(self.cors_middleware)
        
    async def cors_middleware(self, request, handler):
        """CORS middleware for cross-origin requests"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_content = self.get_html_content()
        response = web.Response(text=html_content, content_type='text/html')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    async def status_handler(self, request):
        """Return current status"""
        status = {
            'status': 'Running',
            'timestamp': time.time(),
            'latest_frame': self.get_latest_frame_number()
        }
        
        response = web.json_response(status)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    async def frame_handler(self, request):
        """Return the latest processed frame"""
        frame_path = self.get_latest_frame_path()
        if frame_path and frame_path.exists():
            try:
                with open(frame_path, 'rb') as f:
                    frame_data = f.read()
                
                response = web.Response(body=frame_data, content_type='image/jpeg')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return response
            except Exception as e:
                logger.error(f"Error reading frame: {e}")
                return web.Response(status=500, text="Error reading frame")
        else:
            return web.Response(status=404, text="No frame available")
            
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
        
    def get_html_content(self) -> str:
        """Generate the HTML content for the viewer"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>YOLO Video Stream</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { text-align: center; }
        .video-container { text-align: center; margin: 20px 0; }
        #videoCanvas { border: 2px solid #333; background: #000; }
        .controls { text-align: center; margin: 20px 0; }
        .btn { padding: 10px 20px; margin: 0 10px; font-size: 16px; cursor: pointer; }
        .btn-primary { background: #007bff; color: white; border: none; border-radius: 5px; }
        .btn-secondary { background: #6c757d; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>YOLO Video Stream - WebRTC</h1>
        
        <div class="video-container">
            <canvas id="videoCanvas" width="640" height="480"></canvas>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" id="startBtn" onclick="startStreaming()">Start Streaming</button>
            <button class="btn btn-secondary" id="stopBtn" onclick="stopStreaming()" disabled>Stop Streaming</button>
        </div>
        
        <div id="status" style="text-align: center; margin: 20px 0;">Ready to connect</div>
    </div>

    <script>
        const canvas = document.getElementById('videoCanvas');
        const ctx = canvas.getContext('2d');
        let isStreaming = false;
        let streamInterval = null;
        
        function startStreaming() {
            if (isStreaming) return;
            
            isStreaming = true;
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('status').textContent = 'Streaming...';
            
            streamInterval = setInterval(streamFrame, 33);
        }
        
        function stopStreaming() {
            if (!isStreaming) return;
            
            isStreaming = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('status').textContent = 'Stopped';
            
            if (streamInterval) {
                clearInterval(streamInterval);
                streamInterval = null;
            }
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        
        async function streamFrame() {
            try {
                const response = await fetch('/frame?' + Date.now(), { cache: 'no-cache' });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const imageUrl = URL.createObjectURL(blob);
                    
                    const img = new Image();
                    img.onload = () => {
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        URL.revokeObjectURL(imageUrl);
                    };
                    
                    img.src = imageUrl;
                }
            } catch (error) {
                console.error('Frame streaming error:', error);
            }
        }
        
        // Auto-start streaming after page load
        window.addEventListener('load', () => {
            setTimeout(startStreaming, 1000);
        });
    </script>
</body>
</html>"""
        
    async def run(self):
        """Run the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"WebRTC Video Viewer started on http://0.0.0.0:{self.port}")
        logger.info(f"Access from other devices using: http://<CM5_IP>:{self.port}")
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()

if __name__ == "__main__":
    viewer = WebRTCVideoViewer()
    asyncio.run(viewer.run()) 