#!/usr/bin/env python3
"""
MJPEG Video Streamer for YOLO Camera
Provides continuous video stream with minimal latency
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

import aiohttp
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MJPEGVideoViewer:
    def __init__(self, port: int = 8084):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.frame_buffer = []
        self.max_buffer_size = 10
        self.is_streaming = False
        
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/video_feed', self.video_feed_handler)
        self.app.router.add_get('/status', self.status_handler)
        self.app.router.add_options('/{path:.*}', self.options_handler)
        
        # Add CORS middleware
        self.app.middlewares.append(self.cors_middleware)
        
    async def cors_middleware(self, request, handler):
        """CORS middleware for cross-origin requests"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
        
    async def options_handler(self, request):
        """Handle OPTIONS requests for CORS"""
        response = web.Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
        
    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_content = self.get_html_content()
        response = web.Response(text=html_content, content_type='text/html')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    async def video_feed_handler(self, request):
        """Handle MJPEG video stream"""
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        
        await response.prepare(request)
        
        logger.info(f"MJPEG stream started for {request.remote}")
        
        try:
            while True:
                # Get latest frame
                frame_data = await self.get_latest_frame_data()
                if frame_data:
                    # Send frame boundary
                    await response.write(b'--frame\r\n')
                    
                    # Send frame headers
                    headers = f'Content-Type: image/jpeg\r\nContent-Length: {len(frame_data)}\r\n\r\n'
                    await response.write(headers.encode())
                    
                    # Send frame data
                    await response.write(frame_data)
                    await response.write(b'\r\n')
                    
                    # Flush to ensure immediate transmission
                    await response.drain()
                    
                    # Control frame rate
                    await asyncio.sleep(0.033)  # ~30 FPS
                else:
                    # Send placeholder frame if no data available
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info(f"MJPEG stream cancelled for {request.remote}")
        except Exception as e:
            logger.error(f"MJPEG stream error: {e}")
        finally:
            logger.info(f"MJPEG stream ended for {request.remote}")
            
        return response
        
    async def status_handler(self, request):
        """Return current status"""
        status = {
            'status': 'Running',
            'timestamp': time.time(),
            'latest_frame': self.get_latest_frame_number(),
            'streaming': self.is_streaming
        }
        
        response = web.json_response(status)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    async def get_latest_frame_data(self) -> Optional[bytes]:
        """Get the latest frame data as bytes"""
        try:
            frame_path = self.get_latest_frame_path()
            if frame_path and frame_path.exists():
                with open(frame_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
        return None
        
    def get_latest_frame_path(self) -> Optional[Path]:
        """Get the path to the latest processed frame"""
        try:
            frame_files = list(Path('/tmp').glob('processed_frame_*.jpg'))
            if frame_files:
                # Sort by modification time and get the latest
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
                # Extract frame number from filename
                frame_name = frame_path.stem
                frame_num = int(frame_name.split('_')[-1])
                return frame_num
            except (ValueError, IndexError):
                pass
        return 0
        
    def get_html_content(self) -> str:
        """Generate the HTML content for the viewer"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YOLO Video Stream - MJPEG</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
            max-width: 900px;
            width: 100%;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 700;
        }
        
        .video-container {
            position: relative;
            width: 100%;
            max-width: 800px;
            margin: 0 auto 20px;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            background: #000;
        }
        
        #videoStream {
            width: 100%;
            height: auto;
            display: block;
            border-radius: 15px;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
            transform: translateY(-2px);
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
            transform: translateY(-2px);
        }
        
        .btn-success {
            background: #28a745;
            color: white;
        }
        
        .btn-success:hover {
            background: #218838;
            transform: translateY(-2px);
        }
        
        .status {
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #e9ecef;
        }
        
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            color: #667eea;
        }
        
        .stat-label {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .connection-status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .connected { background: #28a745; }
        .disconnected { background: #dc3545; }
        .connecting { background: #ffc107; }
        
        .quality-controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        
        .quality-btn {
            padding: 8px 16px;
            border: 2px solid #667eea;
            border-radius: 20px;
            background: transparent;
            color: #667eea;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .quality-btn.active {
            background: #667eea;
            color: white;
        }
        
        .quality-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
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
            
            .quality-controls {
                flex-direction: column;
                align-items: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 YOLO Video Stream - MJPEG</h1>
        
        <div class="status">
            <span class="connection-status" id="connectionStatus"></span>
            <span id="statusText">Ready to connect</span>
        </div>
        
        <div class="video-container">
            <img id="videoStream" alt="YOLO Video Stream" style="display: none;">
            <div id="loadingMessage" style="text-align: center; padding: 50px; color: #666;">
                <h3>Loading video stream...</h3>
                <p>Click "Start Streaming" to begin</p>
            </div>
        </div>
        
        <div class="quality-controls">
            <button class="quality-btn active" onclick="setQuality('hd')">HD (640x480)</button>
            <button class="quality-btn" onclick="setQuality('sd')">SD (320x240)</button>
            <button class="quality-btn" onclick="setQuality('ld')">LD (160x120)</button>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" id="startBtn" onclick="startStreaming()">
                🚀 Start Streaming
            </button>
            <button class="btn btn-secondary" id="stopBtn" onclick="stopStreaming()" disabled>
                ⏹️ Stop Streaming
            </button>
            <button class="btn btn-success" id="fullscreenBtn" onclick="toggleFullscreen()">
                📱 Fullscreen
            </button>
            <button class="btn btn-danger" id="snapshotBtn" onclick="takeSnapshot()" disabled>
                📸 Snapshot
            </button>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="fpsValue">0</div>
                <div class="stat-label">FPS</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="latencyValue">0ms</div>
                <div class="stat-label">Latency</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="frameCountValue">0</div>
                <div class="stat-label">Frames</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="qualityValue">HD</div>
                <div class="stat-label">Quality</div>
            </div>
        </div>
    </div>

    <script>
        class MJPEGVideoStreamer {
            constructor() {
                this.videoElement = document.getElementById('videoStream');
                this.loadingMessage = document.getElementById('loadingMessage');
                this.isStreaming = false;
                this.streamUrl = '/video_feed';
                this.frameCount = 0;
                this.lastFrameTime = 0;
                this.fps = 0;
                this.latency = 0;
                this.quality = 'hd';
                
                this.setupEventListeners();
                this.updateConnectionStatus('disconnected');
            }
            
            setupEventListeners() {
                // Monitor frame updates
                this.videoElement.addEventListener('load', () => {
                    this.onFrameUpdate();
                });
                
                // Monitor stream start/stop
                this.videoElement.addEventListener('loadstart', () => {
                    this.updateConnectionStatus('connecting');
                });
                
                this.videoElement.addEventListener('canplay', () => {
                    this.updateConnectionStatus('connected');
                    this.loadingMessage.style.display = 'none';
                    this.videoElement.style.display = 'block';
                });
                
                this.videoElement.addEventListener('error', () => {
                    this.updateConnectionStatus('disconnected');
                    this.loadingMessage.style.display = 'block';
                    this.videoElement.style.display = 'none';
                    this.loadingMessage.innerHTML = '<h3>Stream Error</h3><p>Failed to load video stream</p>';
                });
            }
            
            startStreaming() {
                if (this.isStreaming) return;
                
                this.isStreaming = true;
                this.updateButtons(true);
                this.updateStatus('Starting stream...');
                
                // Set stream source
                this.videoElement.src = this.streamUrl + '?quality=' + this.quality + '&t=' + Date.now();
                
                // Start FPS monitoring
                this.startFPSMonitoring();
            }
            
            stopStreaming() {
                if (!this.isStreaming) return;
                
                this.isStreaming = false;
                this.updateConnectionStatus('disconnected');
                this.updateButtons(false);
                this.updateStatus('Stream stopped');
                
                // Clear video source
                this.videoElement.src = '';
                this.videoElement.style.display = 'none';
                this.loadingMessage.style.display = 'block';
                this.loadingMessage.innerHTML = '<h3>Stream Stopped</h3><p>Click "Start Streaming" to resume</p>';
                
                // Stop FPS monitoring
                this.stopFPSMonitoring();
            }
            
            startFPSMonitoring() {
                this.fpsInterval = setInterval(() => {
                    this.updateStats();
                }, 1000);
            }
            
            stopFPSMonitoring() {
                if (this.fpsInterval) {
                    clearInterval(this.fpsInterval);
                    this.fpsInterval = null;
                }
            }
            
            onFrameUpdate() {
                const now = performance.now();
                this.frameCount++;
                
                // Calculate FPS
                if (this.lastFrameTime > 0) {
                    const deltaTime = now - this.lastFrameTime;
                    this.fps = Math.round(1000 / deltaTime);
                }
                this.lastFrameTime = now;
            }
            
            updateStats() {
                document.getElementById('fpsValue').textContent = this.fps;
                document.getElementById('frameCountValue').textContent = this.frameCount;
                document.getElementById('qualityValue').textContent = this.quality.toUpperCase();
            }
            
            updateButtons(streaming) {
                document.getElementById('startBtn').disabled = streaming;
                document.getElementById('stopBtn').disabled = !streaming;
                document.getElementById('snapshotBtn').disabled = !streaming;
            }
            
            updateConnectionStatus(status) {
                const statusElement = document.getElementById('connectionStatus');
                statusElement.className = 'connection-status ' + status;
                
                const statusText = document.getElementById('statusText');
                switch (status) {
                    case 'connected':
                        statusText.textContent = 'Connected - Streaming';
                        break;
                    case 'connecting':
                        statusText.textContent = 'Connecting...';
                        break;
                    case 'disconnected':
                        statusText.textContent = 'Disconnected';
                        break;
                }
            }
            
            updateStatus(message) {
                console.log(message);
            }
            
            setQuality(quality) {
                this.quality = quality;
                
                // Update quality button states
                document.querySelectorAll('.quality-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Update quality display
                document.getElementById('qualityValue').textContent = quality.toUpperCase();
                
                // Restart stream with new quality if currently streaming
                if (this.isStreaming) {
                    this.stopStreaming();
                    setTimeout(() => this.startStreaming(), 100);
                }
            }
            
            takeSnapshot() {
                if (!this.isStreaming) return;
                
                // Create canvas to capture current frame
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                canvas.width = this.videoElement.videoWidth || 640;
                canvas.height = this.videoElement.videoHeight || 480;
                
                // Draw current video frame
                ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
                
                // Convert to blob and download
                canvas.toBlob((blob) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `yolo_snapshot_${Date.now()}.png`;
                    a.click();
                    URL.revokeObjectURL(url);
                }, 'image/png');
            }
        }
        
        // Initialize the streamer
        const streamer = new MJPEGVideoStreamer();
        
        // Global functions for buttons
        function startStreaming() {
            streamer.startStreaming();
        }
        
        function stopStreaming() {
            streamer.stopStreaming();
        }
        
        function toggleFullscreen() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.error('Error attempting to enable fullscreen:', err);
                });
            } else {
                document.exitFullscreen();
            }
        }
        
        function takeSnapshot() {
            streamer.takeSnapshot();
        }
        
        function setQuality(quality) {
            streamer.setQuality(quality);
        }
        
        // Auto-start streaming after page load
        window.addEventListener('load', () => {
            setTimeout(() => {
                streamer.startStreaming();
            }, 1000);
        });
    </script>
</body>
</html>
        """
        
    async def run(self):
        """Run the web server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"MJPEG Video Viewer started on http://0.0.0.0:{self.port}")
        logger.info(f"Access from other devices using: http://<CM5_IP>:{self.port}")
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()

def main():
    """Main function"""
    viewer = MJPEGVideoViewer(port=8084)
    
    try:
        asyncio.run(viewer.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")

if __name__ == "__main__":
    main() 