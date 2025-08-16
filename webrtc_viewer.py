#!/usr/bin/env python3
"""
WebRTC Video Viewer for YOLO Camera Stream
Provides real-time video streaming with minimal latency
"""

import asyncio
import json
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

class WebRTCVideoViewer:
    def __init__(self, port: int = 8083):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.frame_buffer = []
        self.max_buffer_size = 30  # Keep last 30 frames
        self.last_frame_time = 0
        self.frame_interval = 1.0 / 30.0  # 30 FPS target
        
        # Start frame generator in background
        self.start_frame_generator()
        
    def start_frame_generator(self):
        """Start frame generator in background thread"""
        def generate_frames():
            import cv2
            import numpy as np
            
            frame_count = 0
            while True:
                try:
                    # Create a test frame
                    img = np.zeros((480, 640, 3), dtype=np.uint8)
                    
                    # Add visual elements
                    cv2.rectangle(img, (50, 50), (590, 430), (0, 255, 0), 3)
                    cv2.putText(img, f'WebRTC Frame {frame_count}', (100, 100), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    
                    # Add timestamp
                    timestamp = time.strftime("%H:%M:%S")
                    cv2.putText(img, timestamp, (100, 150), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # Add moving object
                    x = int(100 + 50 * np.sin(frame_count * 0.1))
                    y = int(200 + 30 * np.cos(frame_count * 0.15))
                    cv2.circle(img, (x, y), 20, (0, 0, 255), -1)
                    
                    # Save frame
                    filename = f"/tmp/processed_frame_{frame_count}.jpg"
                    cv2.imwrite(filename, img)
                    
                    logger.info(f"Generated frame {frame_count}: {filename}")
                    frame_count += 1
                    
                    # Clean up old frames
                    if frame_count > 10:
                        old_file = f"/tmp/processed_frame_{frame_count - 10}.jpg"
                        if os.path.exists(old_file):
                            os.remove(old_file)
                    
                    time.sleep(0.1)  # 10 FPS
                    
                except Exception as e:
                    logger.error(f"Frame generation error: {e}")
                    time.sleep(1)
        
        # Start in background thread
        thread = threading.Thread(target=generate_frames, daemon=True)
        thread.start()
        logger.info("Frame generator started in background")
        
    def setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/stream', self.stream_handler)
        self.app.router.add_get('/status', self.status_handler)
        self.app.router.add_get('/frame', self.frame_handler)
        self.app.router.add_options('/{path:.*}', self.options_handler)
        
        # Add CORS middleware
        self.app.middlewares.append(self.cors_middleware)
        
    async def cors_middleware(self, request, handler):
        """CORS middleware for cross-origin requests"""
        response = await handler(request)
        
        # Set CORS headers for all responses
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Range'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range'
        
        return response
        
    async def options_handler(self, request):
        """Handle OPTIONS requests for CORS"""
        response = web.Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, Range'
        response.headers['Access-Control-Max-Age'] = '86400'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Length, Content-Range'
        return response
        
    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_content = self.get_html_content()
        response = web.Response(text=html_content, content_type='text/html')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
        
    async def stream_handler(self, request):
        """Handle WebSocket streaming connection"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info(f"WebSocket connection established from {request.remote}")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == 'ping':
                        await ws.send_str('pong')
                    elif msg.data == 'get_frame':
                        # Send latest frame data
                        frame_data = await self.get_latest_frame_data()
                        if frame_data:
                            await ws.send_bytes(frame_data)
                        else:
                            await ws.send_str('no_frame')
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            logger.info(f"WebSocket connection closed from {request.remote}")
            
        return ws
        
    async def status_handler(self, request):
        """Return current status"""
        status = {
            'status': 'Running',
            'timestamp': time.time(),
            'frame_count': len(self.frame_buffer),
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
            
    async def get_latest_frame_data(self) -> Optional[bytes]:
        """Get the latest frame data as bytes"""
        try:
            frame_path = self.get_latest_frame_path()
            if frame_path and frame_path.exists():
                # Check if file is readable and not empty
                if os.access(frame_path, os.R_OK) and frame_path.stat().st_size > 0:
                    with open(frame_path, 'rb') as f:
                        frame_data = f.read()
                        if len(frame_data) > 0:
                            logger.debug(f"Successfully read frame: {frame_path} ({len(frame_data)} bytes)")
                            return frame_data
                        else:
                            logger.warning(f"Frame file is empty: {frame_path}")
                else:
                    logger.warning(f"Frame file not accessible: {frame_path}")
            else:
                logger.debug("No frame path available")
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
                logger.debug(f"Found latest frame: {latest_frame} (size: {latest_frame.stat().st_size} bytes)")
                return latest_frame
            else:
                logger.debug("No frame files found in /tmp")
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
    <title>YOLO Video Stream - WebRTC</title>
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
            max-width: 800px;
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
            max-width: 640px;
            margin: 0 auto 20px;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        #videoCanvas {
            width: 100%;
            height: auto;
            border-radius: 15px;
            background: #000;
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
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            border: 1px solid #f5c6cb;
            display: none;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 YOLO Video Stream - WebRTC</h1>
        
        <div class="status">
            <span class="connection-status" id="connectionStatus"></span>
            <span id="statusText">Ready to connect</span>
        </div>
        
        <div class="error-message" id="errorMessage">
            <strong>Error:</strong> <span id="errorText"></span>
        </div>
        
        <div class="video-container">
            <canvas id="videoCanvas" width="640" height="480"></canvas>
        </div>
        
        <div class="controls">
            <button class="btn btn-primary" id="startBtn" onclick="startStreaming()">
                🚀 Start Streaming
            </button>
            <button class="btn btn-secondary" id="stopBtn" onclick="stopStreaming()" disabled>
                ⏹️ Stop Streaming
            </button>
            <button class="btn btn-danger" id="fullscreenBtn" onclick="toggleFullscreen()">
                📱 Fullscreen
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
        class YOLOVideoStreamer {
            constructor() {
                this.canvas = document.getElementById('videoCanvas');
                this.ctx = this.canvas.getContext('2d');
                this.isStreaming = false;
                this.streamInterval = null;
                this.frameCount = 0;
                this.lastFrameTime = 0;
                this.fps = 0;
                this.latency = 0;
                this.ws = null;
                
                this.setupCanvas();
                this.updateConnectionStatus('disconnected');
            }
            
            setupCanvas() {
                // Make canvas responsive
                const resizeCanvas = () => {
                    const container = this.canvas.parentElement;
                    const containerWidth = container.clientWidth;
                    const aspectRatio = 4/3;
                    
                    if (containerWidth < 640) {
                        this.canvas.style.width = containerWidth + 'px';
                        this.canvas.style.height = (containerWidth / aspectRatio) + 'px';
                    } else {
                        this.canvas.style.width = '640px';
                        this.canvas.style.height = '480px';
                    }
                };
                
                window.addEventListener('resize', resizeCanvas);
                resizeCanvas();
            }
            
            async startStreaming() {
                if (this.isStreaming) return;
                
                this.isStreaming = true;
                this.updateConnectionStatus('connecting');
                this.updateButtons(true);
                this.hideError();
                
                try {
                    // Start frame streaming using HTTP requests (more reliable than WebSocket for now)
                    this.streamInterval = setInterval(() => {
                        this.streamFrame();
                    }, 33); // ~30 FPS
                    
                    this.updateConnectionStatus('connected');
                    this.updateStatus('Streaming started successfully');
                    
                } catch (error) {
                    console.error('Failed to start streaming:', error);
                    this.showError('Failed to start streaming: ' + error.message);
                    this.updateConnectionStatus('disconnected');
                    this.stopStreaming();
                }
            }
            
            async streamFrame() {
                const startTime = performance.now();
                
                try {
                    const response = await fetch('/frame?' + Date.now(), {
                        cache: 'no-cache',
                        headers: {
                            'Accept': 'image/jpeg'
                        }
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const imageUrl = URL.createObjectURL(blob);
                        
                        const img = new Image();
                        img.onload = () => {
                            // Clear canvas and draw new frame
                            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                            this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
                            
                            // Update stats
                            this.updateStats(startTime);
                            
                            // Clean up
                            URL.revokeObjectURL(imageUrl);
                        };
                        
                        img.onerror = () => {
                            console.error('Failed to load frame image');
                            this.showError('Failed to load frame image');
                        };
                        
                        img.src = imageUrl;
                    } else {
                        console.error('Frame request failed:', response.status);
                        this.showError('Frame request failed: ' + response.status);
                    }
                } catch (error) {
                    console.error('Frame streaming error:', error);
                    this.showError('Frame streaming error: ' + error.message);
                }
            }
            
            updateStats(startTime) {
                const now = performance.now();
                this.latency = Math.round(now - startTime);
                this.frameCount++;
                
                // Calculate FPS
                if (this.lastFrameTime > 0) {
                    const deltaTime = now - this.lastFrameTime;
                    this.fps = Math.round(1000 / deltaTime);
                }
                this.lastFrameTime = now;
                
                // Update UI
                document.getElementById('fpsValue').textContent = this.fps;
                document.getElementById('latencyValue').textContent = this.latency + 'ms';
                document.getElementById('frameCountValue').textContent = this.frameCount;
            }
            
            stopStreaming() {
                if (!this.isStreaming) return;
                
                this.isStreaming = false;
                this.updateConnectionStatus('disconnected');
                this.updateButtons(false);
                
                if (this.streamInterval) {
                    clearInterval(this.streamInterval);
                    this.streamInterval = null;
                }
                
                // Clear canvas
                this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                
                this.updateStatus('Streaming stopped');
                this.hideError();
            }
            
            updateButtons(streaming) {
                document.getElementById('startBtn').disabled = streaming;
                document.getElementById('stopBtn').disabled = !streaming;
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
            
            showError(message) {
                const errorElement = document.getElementById('errorMessage');
                const errorText = document.getElementById('errorText');
                errorText.textContent = message;
                errorElement.style.display = 'block';
            }
            
            hideError() {
                const errorElement = document.getElementById('errorMessage');
                errorElement.style.display = 'none';
            }
        }
        
        // Initialize the streamer
        const streamer = new YOLOVideoStreamer();
        
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
        
        logger.info(f"WebRTC Video Viewer started on http://0.0.0.0:{self.port}")
        logger.info(f"Access from other devices using: http://<CM5_IP>:{self.port}")
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()

def main():
    """Main function"""
    viewer = WebRTCVideoViewer(port=8083)
    
    try:
        asyncio.run(viewer.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")

if __name__ == "__main__":
    main() 