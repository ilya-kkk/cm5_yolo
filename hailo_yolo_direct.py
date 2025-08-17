#!/usr/bin/env python3
"""
Direct Hailo YOLO processing using working Python API
"""

import sys
import os

print("=== Hailo YOLO Direct Test ===")
print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)
print("PYTHONPATH env:", os.environ.get('PYTHONPATH', 'Not set'))

# Try to import OpenCV
try:
    import cv2
    print("✅ OpenCV imported successfully")
    print("OpenCV version:", cv2.__version__)
    print("OpenCV path:", cv2.__file__)
except ImportError as e:
    print(f"❌ Failed to import OpenCV: {e}")
    print("Available paths:", sys.path)
    sys.exit(1)

import numpy as np
import time
import signal
import socket
import threading
import tempfile
import subprocess
import json
from pathlib import Path

# Hailo imports - enabled for Hailo-8L
try:
    import hailo_platform
    HAILO_AVAILABLE = True
    print("✅ Hailo platform available")
except ImportError as e:
    HAILO_AVAILABLE = False
    print(f"❌ Hailo not available: {e}")

class HailoYOLOProcessor:
    def __init__(self):
        self.udp_socket = None
        self.running = False
        self.frame_buffer = []
        self.buffer_size = 1024 * 1024  # 1MB buffer
        self.mjpeg_buffer = b''
        self.frame_lock = threading.Lock()
        self.latest_processed_frame = None
        
        # YOLO processing variables
        self.frame_counter = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
        # Hailo variables
        self.hailo_device = None
        self.yolo_model = None
        self.model_loaded = False
        
        # Output directory
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Hailo
        self.init_hailo()
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def init_hailo(self):
        """Initialize Hailo device and model"""
        try:
            print("🔧 Initializing Hailo YOLO...")
            
            if not HAILO_AVAILABLE:
                print("⚠️ Hailo not available - running in test mode")
                return
            
            # Initialize Hailo device using hailo_platform
            try:
                print("🔍 Scanning for Hailo devices...")
                devices = hailo_platform.Device.scan()
                if devices:
                    self.hailo_device = devices[0]
                    print(f"✅ Found Hailo device: {self.hailo_device}")
                else:
                    print("❌ No Hailo devices found")
                    return
            except Exception as e:
                print(f"❌ Failed to scan Hailo devices: {e}")
                return
            
            # Load YOLOv8n model
            try:
                print("📦 Loading YOLOv8n model...")
                hef_path = self.find_hef_file()
                
                if not hef_path:
                    print("❌ No valid HEF file found")
                    return
                
                # Load HEF file using hailo_platform
                self.yolo_model = hailo_platform.HEF(hef_path)
                print(f"✅ YOLOv8n model loaded: {self.yolo_model}")
                
                # Configure model for inference
                self.configure_model = self.yolo_model.configure(self.hailo_device)
                print(f"✅ Model configured for device: {self.configure_model}")
                
                # Create input and output VStreams
                self.input_vstream_info = self.configure_model.get_input_vstream_infos()
                self.output_vstream_info = self.configure_model.get_output_vstream_infos()
                
                print(f"📥 Input streams: {len(self.input_vstream_info)}")
                print(f"📤 Output streams: {len(self.output_vstream_info)}")
                
                for i, info in enumerate(self.input_vstream_info):
                    print(f"  Input {i}: {info.shape}, {info.format}")
                
                for i, info in enumerate(self.output_vstream_info):
                    print(f"  Output {i}: {info.shape}, {info.format}")
                
                self.model_loaded = True
                print("🎯 YOLOv8n model ready for inference!")
                
            except Exception as e:
                print(f"❌ Failed to load YOLOv8n model: {e}")
                return
                
        except Exception as e:
            print(f"❌ Hailo initialization failed: {e}")
            return
    
    def find_hef_file(self):
        """Find HEF model file"""
        possible_paths = [
            "/workspace/yolov8n.hef",
            "/home/cm5/cm5_yolo/yolov8n.hef",
            "/usr/share/hailo/models/yolov8n.hef",
            "/opt/hailo/models/yolov8n.hef"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                file_size = os.path.getsize(path)
                if file_size > 1000000:  # More than 1MB
                    print(f"✅ Found HEF file: {path} ({file_size} bytes)")
                    return path
                else:
                    print(f"⚠️ HEF file too small: {path} ({file_size} bytes)")
        
        print("❌ No valid HEF file found")
        return None
    
    def run_hailo_inference(self, frame):
        """Run YOLO inference using Hailo device"""
        try:
            if not self.model_loaded or not self.hailo_device:
                print("⚠️ Hailo not available, using simulation")
                return self.simulate_yolo_detection(frame)
            
            print("🚀 Running Hailo YOLO inference...")
            
            # Preprocess frame for YOLOv8n (640x640)
            input_height, input_width = 640, 640
            frame_height, frame_width = frame.shape[:2]
            
            # Resize and normalize frame
            resized_frame = cv2.resize(frame, (input_width, input_height))
            input_data = resized_frame.astype(np.float32) / 255.0
            
            # Convert to NCHW format (batch, channels, height, width)
            input_data = np.transpose(input_data, (2, 0, 1))
            input_data = np.expand_dims(input_data, axis=0)
            
            try:
                # Create input and output VStreams for inference using hailo_platform
                input_vstreams = self.configure_model.create_input_vstreams()
                output_vstreams = self.configure_model.create_output_vstreams()
                
                # Send input data to Hailo
                input_vstreams[0].write(input_data)
                
                # Get inference results
                output_data = output_vstreams[0].read()
                
                # Process YOLOv8n output
                detections = self.process_yolov8n_output(output_data, frame_width, frame_height)
                
                # Draw detections on frame
                processed_frame = self.draw_detections(frame, detections)
                
                print(f"✅ Hailo inference completed, found {len(detections)} objects")
                return processed_frame
                
            except Exception as e:
                print(f"❌ Hailo inference error: {e}")
                return self.simulate_yolo_detection(frame)
                
        except Exception as e:
            print(f"❌ Hailo inference failed: {e}")
            return self.simulate_yolo_detection(frame)
    
    def process_yolov8n_output(self, output_data, frame_width, frame_height):
        """Process YOLOv8n output to extract detections"""
        try:
            # YOLOv8n output format: [batch, 84, 8400] where 84 = 4 (bbox) + 80 (classes)
            # Reshape output to [8400, 84]
            output = output_data.reshape(-1, 84)
            
            # Extract bounding boxes and class probabilities
            boxes = output[:, :4]  # x1, y1, x2, y2
            scores = output[:, 4:]
            
            # Get class with highest probability for each detection
            class_ids = np.argmax(scores, axis=1)
            confidences = np.max(scores, axis=1)
            
            # Filter detections by confidence threshold
            confidence_threshold = 0.5
            mask = confidences > confidence_threshold
            
            filtered_boxes = boxes[mask]
            filtered_class_ids = class_ids[mask]
            filtered_confidences = confidences[mask]
            
            # Convert normalized coordinates to pixel coordinates
            detections = []
            for i in range(len(filtered_boxes)):
                x1, y1, x2, y2 = filtered_boxes[i]
                
                # Scale to frame dimensions
                x1 = int(x1 * frame_width)
                y1 = int(y1 * frame_height)
                x2 = int(x2 * frame_width)
                y2 = int(y2 * frame_height)
                
                # Get class name
                class_name = self.get_class_name(filtered_class_ids[i])
                
                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'class': class_name,
                    'confidence': float(filtered_confidences[i]),
                    'color': self.get_class_color(filtered_class_ids[i])
                })
            
            return detections
            
        except Exception as e:
            print(f"❌ Error processing YOLOv8n output: {e}")
            return []
    
    def get_class_name(self, class_id):
        """Get COCO class name from class ID"""
        coco_classes = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        if 0 <= class_id < len(coco_classes):
            return coco_classes[class_id]
        return f"class_{class_id}"
    
    def get_class_color(self, class_id):
        """Get color for class visualization"""
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255),
            (0, 255, 255), (128, 0, 0), (0, 128, 0), (0, 0, 128), (128, 128, 0),
            (128, 0, 128), (0, 128, 128), (64, 0, 0), (0, 64, 0), (0, 0, 64)
        ]
        return colors[class_id % len(colors)]
    
    def draw_detections(self, frame, detections):
        """Draw detections on frame"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(processed_frame, "YOLO Processing Active (Real Hailo-8L)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(processed_frame, f"Frame: {self.frame_counter}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(processed_frame, f"Detections: {len(detections)}", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw detections
        for detection in detections:
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            color = detection['color']
            
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), color, 2)
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(processed_frame, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return processed_frame
    
    def simulate_yolo_detection(self, frame):
        """Simulate YOLO detection for fallback"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(processed_frame, "YOLO Processing Active (Simulation)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(processed_frame, f"Frame: {self.frame_counter}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        return processed_frame
    
    def decode_mjpeg_frame(self, data):
        """Decode MJPEG frame from UDP data"""
        try:
            # Find JPEG start marker
            start_marker = b'\xff\xd8'
            end_marker = b'\xff\xd9'
            
            start_pos = data.find(start_marker)
            if start_pos == -1:
                return None
            
            end_pos = data.find(end_marker, start_pos)
            if end_pos == -1:
                return None
            
            # Extract JPEG data
            jpeg_data = data[start_pos:end_pos + 2]
            
            # Decode using OpenCV
            nparr = np.frombuffer(jpeg_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                return frame
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ MJPEG decode error: {e}")
            return None
    
    def setup_udp_receiver(self):
        """Setup UDP receiver for MJPEG stream"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            print("✅ UDP receiver setup on port 5000")
            print("📝 Note: libcamera-vid must be started manually on the host")
            print("📝 Command: libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
            return True
        except Exception as e:
            print(f"❌ UDP setup error: {e}")
            return False
    
    def process_mjpeg_stream(self):
        """Process MJPEG stream from UDP"""
        print("📹 Starting MJPEG stream processing...")
        print("⏳ Waiting for libcamera-vid MJPEG stream from host...")
        print("🔧 MJPEG is much easier to decode than H.264")
        
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                if data:
                    print(f"📦 Received {len(data)} bytes, total buffer: {len(data)} bytes")
                    
                    # Decode MJPEG frame
                    print("🔧 Attempting to decode MJPEG frame...")
                    frame = self.decode_mjpeg_frame(data)
                    
                    if frame is not None:
                        print(f"🎯 SUCCESS! Decoded real camera frame: {frame.shape}")
                        
                        # Update frame counter
                        self.frame_counter += 1
                        
                        # Run YOLO inference
                        processed_frame = self.run_hailo_inference(frame)
                        
                        # Save processed frame
                        if self.save_processed_frame(processed_frame):
                            # Update FPS counter
                            self.fps_counter += 1
                            current_time = time.time()
                            
                            # Calculate FPS every second
                            if current_time - self.fps_start_time >= 1.0:
                                self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
                                print(f"🔄 Hailo YOLO Processing FPS: {self.current_fps:.1f}")
                                self.fps_counter = 0
                                self.fps_start_time = current_time
                    else:
                        print("⚠️ Failed to decode MJPEG frame")
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"⚠️ Stream processing error: {e}")
                continue
    
    def save_processed_frame(self, frame):
        """Save processed frame to shared directory"""
        try:
            output_path = "/tmp/latest_yolo_frame.jpg"
            success = cv2.imwrite(output_path, frame)
            if success:
                return True
            else:
                print("⚠️ Failed to save processed frame")
                return False
        except Exception as e:
            print(f"⚠️ Save error: {e}")
            return False
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        if self.udp_socket:
            self.udp_socket.close()
        sys.exit(0)
    
    def run(self):
        """Main run loop"""
        print("🎯 Starting Hailo YOLO Processor (Direct API)...")
        print("📋 This service listens for UDP stream from libcamera-vid on the host")
        print("🤖 Real YOLO processing with Hailo-8L accelerator")
        print("🔧 Now using MJPEG instead of problematic H.264")
        
        # Setup UDP receiver
        if not self.setup_udp_receiver():
            print("❌ Failed to setup UDP receiver")
            return
        
        self.running = True
        
        # Start stream processing in separate thread
        stream_thread = threading.Thread(target=self.process_mjpeg_stream)
        stream_thread.daemon = True
        stream_thread.start()
        
        print("✅ Hailo YOLO Processor is running")
        print("📱 Video stream available at UDP://127.0.0.1:5000")
        print("🌐 Web interface available at http://localhost:8080")
        print("💾 Processed frames saved to /tmp/latest_yolo_frame.jpg")
        print()
        print("🔧 To start video stream, run on the host:")
        print("   libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    processor = HailoYOLOProcessor()
    processor.run() 