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
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/':
            # Serve main page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>YOLO Processed Video Viewer</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .frame-info { background: #f0f0f0; padding: 10px; margin: 10px 0; }
                    .controls { margin: 20px 0; }
                    button { padding: 10px 20px; margin: 5px; font-size: 16px; }
                    #frameDisplay { margin: 20px 0; }
                    img { max-width: 100%; height: auto; }
                </style>
            </head>
            <body>
                <h1>YOLO Processed Video Viewer</h1>
                <div class="frame-info">
                    <h3>Status: <span id="status">Checking...</span></h3>
                    <p>Latest Frame: <span id="latestFrame">-</span></p>
                    <p>Total Frames: <span id="totalFrames">-</span></p>
                </div>
                
                <div class="controls">
                    <button onclick="startViewing()">Start Viewing</button>
                    <button onclick="stopViewing()">Stop Viewing</button>
                    <button onclick="refreshFrame()">Refresh Frame</button>
                </div>
                
                <div id="frameDisplay">
                    <img id="currentFrame" src="" alt="No frame available" style="display: none;">
                </div>
                
                <script>
                    let viewingInterval;
                    let isViewing = false;
                    
                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('status').textContent = data.status);
                                document.getElementById('latestFrame').textContent = data.latest_frame;
                                document.getElementById('totalFrames').textContent = data.total_frames;
                            });
                    }
                    
                    function refreshFrame() {
                        fetch('/frame')
                            .then(response => response.blob())
                            .then(blob => {
                                const img = document.getElementById('currentFrame');
                                img.src = URL.createObjectURL(blob);
                                img.style.display = 'block';
                            })
                            .catch(error => {
                                console.error('Error loading frame:', error);
                                document.getElementById('currentFrame').style.display = 'none';
                            });
                    }
                    
                    function startViewing() {
                        if (isViewing) return;
                        isViewing = true;
                        viewingInterval = setInterval(refreshFrame, 100); // 10 FPS
                        document.getElementById('status').textContent = 'Viewing...';
                    }
                    
                    function stopViewing() {
                        if (!isViewing) return;
                        isViewing = false;
                        clearInterval(viewingInterval);
                        document.getElementById('status').textContent = 'Stopped';
                    }
                    
                    // Update status every 2 seconds
                    setInterval(updateStatus, 2000);
                    updateStatus();
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif path == '/status':
            # Return status as JSON
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
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
                            self.send_header('Cache-Control', 'no-cache')
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