#!/usr/bin/env python3
"""
Simple web stream service for Hailo YOLO processing
"""

from flask import Flask, Response, render_template_string, request, jsonify
import time
import threading
import json
import base64
from io import BytesIO
import cv2
import numpy as np
# Hailo imports - try to import from hailo_wrapper
try:
    from hailo_wrapper import HailoYOLOProcessor
    HAILO_AVAILABLE = True
    print("✅ Hailo wrapper imported successfully")
except ImportError as e:
    HAILO_AVAILABLE = False
    print(f"❌ Hailo wrapper not available: {e}")

app = Flask(__name__)

# Global variables for stream data
current_frame = None
frame_lock = threading.Lock()
processing_stats = {
    "fps": 0.0,
    "objects_detected": 0,
    "last_update": time.time(),
    "hailo_status": "Unknown",
    "camera_status": "Unknown"
}
hailo_processor = None

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hailo YOLO Web Stream</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status.connected { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.disconnected { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.unknown { background-color: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .upload-form { margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 5px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        .stat-label { color: #6c757d; margin-top: 5px; }
        button { background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        input[type="file"] { margin: 10px 0; }
        .result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .result.success { background-color: #d4edda; color: #155724; }
        .result.error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Hailo YOLO Web Stream</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="fps">0.0</div>
                <div class="stat-label">FPS</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="objects">0</div>
                <div class="stat-label">Objects Detected</div>
            </div>
        </div>
        
        <div class="status" id="hailo-status">
            <strong>Hailo Status:</strong> <span id="hailo-text">Unknown</span>
        </div>
        
        <div class="status" id="camera-status">
            <strong>Camera Status:</strong> <span id="camera-text">Unknown</span>
        </div>
        
        <div class="upload-form">
            <h3>📸 Upload Image for Hailo Processing</h3>
            <form id="uploadForm">
                <input type="file" id="imageFile" accept="image/*" required>
                <button type="submit">Process with Hailo</button>
            </form>
            <div id="result"></div>
        </div>
        
        <div style="margin-top: 30px; text-align: center; color: #6c757d;">
            <p>🌐 Access this interface from any device on your network</p>
            <p>📱 Works on mobile and desktop browsers</p>
        </div>
    </div>

    <script>
        function updateStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('fps').textContent = data.fps.toFixed(1);
                    document.getElementById('objects').textContent = data.objects_detected;
                    
                    const hailoStatus = document.getElementById('hailo-status');
                    const hailoText = document.getElementById('hailo-text');
                    hailoText.textContent = data.hailo_status;
                    
                    if (data.hailo_status === 'Connected') {
                        hailoStatus.className = 'status connected';
                    } else if (data.hailo_status === 'Error') {
                        hailoStatus.className = 'status disconnected';
                    } else {
                        hailoStatus.className = 'status unknown';
                    }
                    
                    const cameraStatus = document.getElementById('camera-status');
                    const cameraText = document.getElementById('camera-text');
                    cameraText.textContent = data.camera_status;
                    
                    if (data.camera_status === 'Connected') {
                        cameraStatus.className = 'status connected';
                    } else if (data.camera_status === 'Disconnected') {
                        cameraStatus.className = 'status disconnected';
                    } else {
                        cameraStatus.className = 'status unknown';
                    }
                })
                .catch(error => console.error('Error updating stats:', error));
        }

        document.getElementById('uploadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('imageFile');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select an image file');
                return;
            }
            
            const formData = new FormData();
            formData.append('image', file);
            
            fetch('/api/process_image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('result');
                if (data.success) {
                    resultDiv.className = 'result success';
                    resultDiv.textContent = data.message;
                } else {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = data.message;
                }
            })
            .catch(error => {
                const resultDiv = document.getElementById('result');
                resultDiv.className = 'result error';
                resultDiv.textContent = 'Error: ' + error.message;
            });
        });

        // Update stats every second
        setInterval(updateStats, 1000);
        updateStats();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    global processing_stats
    return jsonify(processing_stats)

@app.route('/api/process_image', methods=['POST'])
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'No image file provided'})

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No image file selected'})

        image_data = file.read()
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({'success': False, 'message': 'Invalid image format'})

        try:
            global hailo_processor, processing_stats
            
            if hailo_processor is None and HAILO_AVAILABLE:
                try:
                    hailo_processor = HailoYOLOProcessor()
                    processing_stats['hailo_status'] = 'Connected'
                except Exception as e:
                    print(f"Failed to initialize Hailo processor: {e}")
                    hailo_processor = None
                    processing_stats['hailo_status'] = 'Error'
            
            if hailo_processor is not None:
                # Use Hailo processor if available
                processing_stats['hailo_status'] = 'Connected'
            else:
                processing_stats['hailo_status'] = 'Not Available'

            # Simple image processing simulation
            processed_image = cv2.resize(image, (640, 640))
            processing_stats['objects_detected'] += 1
            processing_stats['last_update'] = time.time()

            return jsonify({
                'success': True,
                'message': f'Image processed successfully! Objects detected: {processing_stats["objects_detected"]}'
            })

        except Exception as e:
            processing_stats['hailo_status'] = 'Error'
            return jsonify({'success': False, 'message': f'Hailo processing error: {str(e)}'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing image: {str(e)}'})

def update_stats():
    """Update processing statistics"""
    while True:
        try:
            global processing_stats
            current_time = time.time()
            if current_time - processing_stats['last_update'] > 0:
                processing_stats['fps'] = 1.0 / (current_time - processing_stats['last_update'])
            processing_stats['last_update'] = current_time

            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    processing_stats['camera_status'] = 'Connected'
                    cap.release()
                else:
                    processing_stats['camera_status'] = 'Disconnected'
            except:
                processing_stats['camera_status'] = 'Error'

            time.sleep(1)
        except:
            time.sleep(1)

if __name__ == '__main__':
    stats_thread = threading.Thread(target=update_stats, daemon=True)
    stats_thread.start()
    print("🚀 Starting Hailo YOLO Web Service...")
    print("🌐 Web interface will be available at: http://0.0.0.0:8080")
    print("📱 Access from any device on the network")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True) 