#!/usr/bin/env python3
"""
Simple HTTP server to view processed video frames
"""

import http.server
import socketserver
import os
import glob
import time
import json
from urllib.parse import urlparse, parse_qs

class ProcessedVideoHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        # Add CORS headers for mobile browsers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/':
            # Serve main page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>YOLO Processed Video Viewer</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 10px; 
                        background: #f5f5f5;
                    }
                    .frame-info { 
                        background: #ffffff; 
                        padding: 15px; 
                        margin: 10px 0; 
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .controls { 
                        margin: 15px 0; 
                        text-align: center;
                    }
                    button { 
                        padding: 12px 24px; 
                        margin: 5px; 
                        font-size: 16px; 
                        border: none;
                        border-radius: 6px;
                        background: #007bff;
                        color: white;
                        cursor: pointer;
                    }
                    button:hover { background: #0056b3; }
                    button:active { background: #004085; }
                    #frameDisplay { 
                        margin: 20px 0; 
                        text-align: center;
                        background: #ffffff;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    img { 
                        max-width: 100%; 
                        height: auto; 
                        border-radius: 8px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    }
                    .error { 
                        color: #dc3545; 
                        background: #f8d7da; 
                        padding: 10px; 
                        border-radius: 4px; 
                        margin: 10px 0;
                    }
                    .success { 
                        color: #155724; 
                        background: #d4edda; 
                        padding: 10px; 
                        border-radius: 4px; 
                        margin: 10px 0;
                    }
                    .loading { 
                        color: #856404; 
                        background: #fff3cd; 
                        padding: 10px; 
                        border-radius: 4px; 
                        margin: 10px 0;
                    }
                </style>
            </head>
            <body>
                <h1>YOLO Processed Video Viewer</h1>
                
                <div class="frame-info">
                    <h3>Status: <span id="status">Checking...</span></h3>
                    <p>Latest Frame: <span id="latestFrame">-</span></p>
                    <p>Total Frames: <span id="totalFrames">-</span></p>
                    <p>Connection: <span id="connection">-</span></p>
                </div>
                
                <div class="controls">
                    <button onclick="startViewing()">Start Viewing</button>
                    <button onclick="stopViewing()">Stop Viewing</button>
                    <button onclick="refreshFrame()">Refresh Frame</button>
                    <button onclick="testConnection()">Test Connection</button>
                </div>
                
                <div id="frameDisplay">
                    <div id="loadingMessage" class="loading" style="display: none;">
                        Loading frame...
                    </div>
                    <div id="errorMessage" class="error" style="display: none;">
                        Error loading frame
                    </div>
                    <img id="currentFrame" src="" alt="No frame available" style="display: none;">
                </div>
                
                <script>
                    let viewingInterval;
                    let isViewing = false;
                    let frameCount = 0;
                    
                    function showMessage(elementId, message, type) {
                        const element = document.getElementById(elementId);
                        element.textContent = message;
                        element.style.display = 'block';
                        
                        if (type === 'error') {
                            document.getElementById('errorMessage').style.display = 'block';
                            document.getElementById('loadingMessage').style.display = 'none';
                        } else if (type === 'loading') {
                            document.getElementById('loadingMessage').style.display = 'block';
                            document.getElementById('errorMessage').style.display = 'none';
                        } else {
                            document.getElementById('errorMessage').style.display = 'none';
                            document.getElementById('loadingMessage').style.display = 'none';
                        }
                    }
                    
                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('status').textContent = data.status;
                                document.getElementById('latestFrame').textContent = data.latest_frame;
                                document.getElementById('totalFrames').textContent = data.total_frames;
                                document.getElementById('connection').textContent = 'Connected';
                            })
                            .catch(error => {
                                console.error('Status error:', error);
                                document.getElementById('connection').textContent = 'Disconnected';
                            });
                    }
                    
                    function testConnection() {
                        showMessage('loadingMessage', 'Testing connection...', 'loading');
                        
                        fetch('/frame')
                            .then(response => {
                                if (response.ok) {
                                    showMessage('loadingMessage', 'Connection successful!', 'success');
                                    setTimeout(() => {
                                        document.getElementById('loadingMessage').style.display = 'none';
                                    }, 2000);
                                } else {
                                    showMessage('errorMessage', 'Connection failed: ' + response.status, 'error');
                                }
                            })
                            .catch(error => {
                                console.error('Connection test error:', error);
                                showMessage('errorMessage', 'Connection error: ' + error.message, 'error');
                            });
                    }
                    
                    function refreshFrame() {
                        showMessage('loadingMessage', 'Loading frame...', 'loading');
                        
                        fetch('/frame')
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error('HTTP ' + response.status);
                                }
                                return response.blob();
                            })
                            .then(blob => {
                                const img = document.getElementById('currentFrame');
                                const url = URL.createObjectURL(blob);
                                
                                img.onload = function() {
                                    showMessage('loadingMessage', 'Frame loaded successfully!', 'success');
                                    setTimeout(() => {
                                        document.getElementById('loadingMessage').style.display = 'none';
                                    }, 1000);
                                    frameCount++;
                                };
                                
                                img.onerror = function() {
                                    showMessage('errorMessage', 'Failed to load image', 'error');
                                };
                                
                                img.src = url;
                                img.style.display = 'block';
                            })
                            .catch(error => {
                                console.error('Frame loading error:', error);
                                showMessage('errorMessage', 'Error loading frame: ' + error.message, 'error');
                            });
                    }
                    
                    function startViewing() {
                        if (isViewing) return;
                        isViewing = true;
                        viewingInterval = setInterval(refreshFrame, 200); // 5 FPS for mobile
                        document.getElementById('status').textContent = 'Viewing...';
                        showMessage('loadingMessage', 'Started viewing...', 'success');
                        setTimeout(() => {
                            document.getElementById('loadingMessage').style.display = 'none';
                        }, 1000);
                    }
                    
                    function stopViewing() {
                        if (!isViewing) return;
                        isViewing = false;
                        clearInterval(viewingInterval);
                        document.getElementById('status').textContent = 'Stopped';
                        showMessage('loadingMessage', 'Viewing stopped', 'success');
                        setTimeout(() => {
                            document.getElementById('loadingMessage').style.display = 'none';
                        }, 1000);
                    }
                    
                    // Update status every 3 seconds
                    setInterval(updateStatus, 3000);
                    updateStatus();
                    
                    // Test connection on page load
                    window.addEventListener('load', function() {
                        setTimeout(testConnection, 1000);
                    });
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif path == '/status':
            # Return status as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            try:
                frame_files = glob.glob("/tmp/processed_frame_*.jpg")
                total_frames = len(frame_files)
                
                latest_frame = 0
                if frame_files:
                    frame_numbers = []
                    for f in frame_files:
                        try:
                            num = int(f.split('_')[-1].split('.')[0])
                            frame_numbers.append(num)
                        except:
                            continue
                    if frame_numbers:
                        latest_frame = max(frame_numbers)
                
                status = "Running" if total_frames > 0 else "No frames"
                
                response = {
                    "status": status,
                    "latest_frame": latest_frame,
                    "total_frames": total_frames
                }
                
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode())
                
        elif path == '/frame':
            # Return the latest processed frame
            try:
                frame_files = glob.glob("/tmp/processed_frame_*.jpg")
                if frame_files:
                    # Get the latest frame by number
                    frame_numbers = []
                    for f in frame_files:
                        try:
                            num = int(f.split('_')[-1].split('.')[0])
                            frame_numbers.append(num)
                        except:
                            continue
                    
                    if frame_numbers:
                        latest_num = max(frame_numbers)
                        latest_frame_path = f"/tmp/processed_frame_{latest_num}.jpg"
                        
                        if os.path.exists(latest_frame_path):
                            with open(latest_frame_path, 'rb') as f:
                                frame_data = f.read()
                            
                            self.send_response(200)
                            self.send_header('Content-type', 'image/jpeg')
                            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(frame_data)
                            return
                
                # No frame available
                self.send_response(404)
                self.end_headers()
                
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8080):
    """Run the HTTP server"""
    with socketserver.TCPServer(("0.0.0.0", port), ProcessedVideoHandler) as httpd:
        print(f"Server running on http://0.0.0.0:{port}")
        print(f"Access from other devices using: http://<CM5_IP>:{port}")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")

if __name__ == "__main__":
    run_server() 