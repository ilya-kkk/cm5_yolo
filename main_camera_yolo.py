#!/usr/bin/env python3
"""
Main camera YOLO processing script for CM5 with Hailo-8L
This script handles MJPEG stream from libcamera-vid and runs real YOLO inference on Hailo-8L
"""

import cv2
import numpy as np
import time
import signal
import sys
import socket
import threading
import tempfile
import os
import subprocess
import json
from pathlib import Path

# Hailo imports
try:
    import hailo_platform
    from hailo_platform import HailoStreamInterface, HailoROI, HailoDetection
    from hailo_platform import HailoDetection, HailoROI, HailoStreamInterface
    HAILO_AVAILABLE = True
    print("✅ Hailo platform imported successfully")
except ImportError:
    HAILO_AVAILABLE = False
    print("⚠️ Hailo platform not available, will use OpenCV fallback")

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
        self.current_fps = 0
        
        # MJPEG parsing variables
        self.frame_count = 0
        
        # Hailo YOLO variables
        self.hailo_device = None
        self.yolo_model = None
        self.model_loaded = False
        
        # Create output directory for processed frames
        self.output_dir = Path("/tmp/yolo_frames")
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize Hailo YOLO
        self.init_hailo_yolo()
        
    def init_hailo_yolo(self):
        """Initialize Hailo YOLO model for real inference"""
        try:
            if not HAILO_AVAILABLE:
                print("⚠️ Hailo platform not available, using OpenCV fallback")
                self.init_opencv_yolo()
                return
                
            print("🔧 Initializing Hailo YOLO model...")
            
            # Find Hailo device
            self.hailo_device = self.find_hailo_device()
            if not self.hailo_device:
                print("⚠️ No Hailo device found, using OpenCV fallback")
                self.init_opencv_yolo()
                return
            
            # Load YOLO model
            yolo_hef_path = self.find_yolo_hef()
            if yolo_hef_path:
                print(f"🎯 Found YOLO HEF model: {yolo_hef_path}")
                
                # Load model to Hailo device
                self.yolo_model = self.load_hailo_model(yolo_hef_path)
                if self.yolo_model:
                    self.model_loaded = True
                    print("✅ Hailo YOLO model loaded successfully")
                else:
                    print("⚠️ Failed to load Hailo model, using OpenCV fallback")
                    self.init_opencv_yolo()
            else:
                print("⚠️ No YOLO HEF model found, using OpenCV fallback")
                self.init_opencv_yolo()
                
        except Exception as e:
            print(f"⚠️ Hailo YOLO initialization error: {e}")
            print("🔄 Falling back to OpenCV YOLO...")
            self.init_opencv_yolo()
    
    def find_hailo_device(self):
        """Find available Hailo device"""
        try:
            print("🔍 Searching for Hailo device...")
            
            # Check for Hailo device files
            hailo_devices = []
            for i in range(10):  # Check multiple device numbers
                device_path = f"/dev/hailo{i}"
                if os.path.exists(device_path):
                    hailo_devices.append(device_path)
                    print(f"✅ Found Hailo device: {device_path}")
            
            if hailo_devices:
                return hailo_devices[0]  # Use first available device
            else:
                print("❌ No Hailo devices found in /dev/")
                return None
                
        except Exception as e:
            print(f"⚠️ Error finding Hailo device: {e}")
            return None
    
    def find_yolo_hef(self):
        """Find YOLO HEF model file"""
        try:
            print("🔍 Searching for YOLO HEF model...")
            
            # Look for HEF file in project directory
            possible_hef_paths = [
                "/workspace/yolov8n.hef",
                "./yolov8n.hef",
                "yolov8n.hef"
            ]
            
            for hef_path in possible_hef_paths:
                if os.path.exists(hef_path):
                    print(f"✅ Found YOLO HEF model: {hef_path}")
                    return hef_path
            
            print("❌ No YOLO HEF model found")
            return None
            
        except Exception as e:
            print(f"⚠️ Error finding YOLO HEF model: {e}")
            return None
    
    def load_hailo_model(self, hef_path):
        """Load YOLO model to Hailo device"""
        try:
            print(f"🔧 Loading HEF model: {hef_path}")
            
            # Initialize Hailo device
            hailo_platform.initialize()
            
            # Load model
            model = hailo_platform.load_model(hef_path)
            
            print("✅ Hailo model loaded successfully")
            return model
            
        except Exception as e:
            print(f"⚠️ Error loading Hailo model: {e}")
            return None
    
    def init_opencv_yolo(self):
        """Initialize OpenCV YOLO as fallback"""
        try:
            print("🔧 Initializing OpenCV YOLO fallback...")
            
            # Try to load YOLO model from common locations
            yolo_config, weights_path = self.find_opencv_yolo_model()
            if yolo_config:
                print(f"🎯 Found OpenCV YOLO model: {weights_path}")
                
                # Load YOLO model
                self.yolo_net = cv2.dnn.readNet(weights_path, yolo_config)
                
                # Set backend and target
                self.yolo_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.yolo_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                
                # Get output layer names
                layer_names = self.yolo_net.getLayerNames()
                self.output_layers = [layer_names[i - 1] for i in self.yolo_net.getUnconnectedOutLayers()]
                
                # Load COCO class names
                self.classes = self.load_coco_classes()
                
                self.model_loaded = True
                print("✅ OpenCV YOLO model loaded successfully")
            else:
                print("⚠️ No OpenCV YOLO model found, will use simulation")
                
        except Exception as e:
            print(f"⚠️ OpenCV YOLO initialization error: {e}")
            print("🔄 Continuing with simulated YOLO...")
    
    def find_opencv_yolo_model(self):
        """Find available OpenCV YOLO model files"""
        try:
            print("🔍 Searching for OpenCV YOLO model files...")
            
            # Look for common YOLO model locations
            possible_configs = [
                "/usr/share/yolo/yolov3.cfg",
                "/usr/local/share/yolo/yolov3.cfg",
                "/opt/yolo/yolov3.cfg",
                "/usr/share/yolo/yolov4.cfg",
                "/usr/local/share/yolo/yolov4.cfg",
                "/opt/yolo/yolov4.cfg",
                "/home/cm5/yolo_models/yolov3.cfg",  # Home directory
                "/home/cm5/yolo_models/yolov4.cfg",  # Home directory
                "/workspace/yolo_models/yolov3.cfg",  # Workspace directory
                "/workspace/yolo_models/yolov4.cfg"   # Workspace directory
            ]
            
            possible_weights = [
                "/usr/share/yolo/yolov3.weights",
                "/usr/local/share/yolo/yolov3.weights",
                "/opt/yolo/yolov3.weights",
                "/usr/share/yolo/yolov4.weights",
                "/usr/local/share/yolo/yolov4.weights",
                "/opt/yolo/yolov4.weights",
                "/home/cm5/yolo_models/yolov3.weights",  # Home directory
                "/home/cm5/yolo_models/yolov4.weights",  # Home directory
                "/workspace/yolo_models/yolov3.weights",  # Workspace directory
                "/workspace/yolo_models/yolov4.weights"   # Workspace directory
            ]
            
            print("📁 Checking possible config paths:")
            for config_path in possible_configs:
                exists = os.path.exists(config_path)
                print(f"  {config_path}: {'✅' if exists else '❌'}")
            
            print("📁 Checking possible weights paths:")
            for weights_path in possible_weights:
                exists = os.path.exists(weights_path)
                print(f"  {weights_path}: {'✅' if exists else '❌'}")
            
            # Check for config and weights pairs
            for config_path in possible_configs:
                if os.path.exists(config_path):
                    print(f"🎯 Found config file: {config_path}")
                    # Find corresponding weights
                    weights_path = config_path.replace('.cfg', '.weights')
                    if os.path.exists(weights_path):
                        print(f"✅ Found matching weights file: {weights_path}")
                        return config_path, weights_path
                    else:
                        print(f"❌ No matching weights file for: {config_path}")
            
            print("❌ No OpenCV YOLO model found")
            return None, None
            
        except Exception as e:
            print(f"⚠️ Error finding OpenCV YOLO model: {e}")
            return None, None
    
    def load_coco_classes(self):
        """Load COCO class names"""
        try:
            # COCO class names
            classes = [
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
            return classes
        except Exception as e:
            print(f"⚠️ Error loading COCO classes: {e}")
            return []
    
    def setup_udp_receiver(self):
        """Setup UDP socket to receive MJPEG stream from host"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('127.0.0.1', 5000))
            self.udp_socket.settimeout(1.0)
            print("✅ UDP receiver setup on port 5000")
            print("📝 Note: libcamera-vid must be started manually on the host")
            print("📝 Command: libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
            return True
        except Exception as e:
            print(f"❌ Error setting up UDP receiver: {e}")
            return False
    
    def decode_mjpeg_frame(self, mjpeg_data):
        """Decode MJPEG frame from UDP data"""
        try:
            # MJPEG frames start with JPEG start marker
            jpeg_start = b'\xff\xd8'
            jpeg_end = b'\xff\xd9'
            
            # Find JPEG start and end
            start_pos = mjpeg_data.find(jpeg_start)
            if start_pos == -1:
                print("⚠️ No JPEG start marker found")
                return None
            
            end_pos = mjpeg_data.find(jpeg_end, start_pos)
            if end_pos == -1:
                print("⚠️ No JPEG end marker found")
                return None
            
            # Extract complete JPEG frame
            jpeg_frame = mjpeg_data[start_pos:end_pos + 2]
            
            if len(jpeg_frame) < 100:  # Too small to be valid JPEG
                print(f"⚠️ JPEG frame too small: {len(jpeg_frame)} bytes")
                return None
            
            # Decode JPEG using OpenCV
            jpeg_array = np.frombuffer(jpeg_frame, dtype=np.uint8)
            frame = cv2.imdecode(jpeg_array, cv2.IMREAD_COLOR)
            
            if frame is not None and frame.size > 0:
                print(f"✅ Successfully decoded MJPEG frame: {frame.shape}")
                return frame
            else:
                print("⚠️ Failed to decode MJPEG frame")
                return None
                
        except Exception as e:
            print(f"⚠️ MJPEG decode error: {e}")
            return None
    
    def run_yolo_inference(self, frame):
        """Run YOLO inference using loaded Hailo model"""
        try:
            if not self.model_loaded:
                print("⚠️ No YOLO model loaded, using simulation")
                return self.simulate_yolo_detection(frame)
            
            # Check if we have Hailo model
            if self.yolo_model and HAILO_AVAILABLE:
                print("🚀 Running Hailo YOLO inference...")
                return self.run_hailo_inference(frame)
            elif hasattr(self, 'yolo_net') and self.yolo_net is not None:
                print("🔄 Running OpenCV YOLO inference...")
                return self.run_opencv_inference(frame)
            else:
                print("⚠️ No YOLO model available, using simulation")
                return self.simulate_yolo_detection(frame)
            
        except Exception as e:
            print(f"⚠️ YOLO inference error: {e}")
            return self.simulate_yolo_detection(frame)
    
    def run_hailo_inference(self, frame):
        """Run YOLO inference on Hailo device"""
        try:
            # Prepare frame for Hailo
            height, width = frame.shape[:2]
            
            # Convert BGR to RGB (Hailo expects RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to Hailo input size (640x640 for YOLOv8)
            input_size = (640, 640)
            resized_frame = cv2.resize(rgb_frame, input_size)
            
            # Normalize to [0, 1]
            normalized_frame = resized_frame.astype(np.float32) / 255.0
            
            # Run inference on Hailo
            print(f"🔧 Running Hailo inference on frame {self.frame_count}...")
            
            # Create input tensor
            input_tensor = hailo_platform.create_tensor(normalized_frame)
            
            # Run inference
            outputs = self.yolo_model.infer([input_tensor])
            
            # Process Hailo outputs
            detections = self.process_hailo_outputs(outputs, width, height)
            
            # Draw detections on frame
            processed_frame = self.draw_hailo_detections(frame, detections)
            
            print(f"✅ Hailo inference completed, found {len(detections)} detections")
            return processed_frame
            
        except Exception as e:
            print(f"⚠️ Hailo inference error: {e}")
            print("🔄 Falling back to simulation...")
            return self.simulate_yolo_detection(frame)
    
    def run_opencv_inference(self, frame):
        """Run YOLO inference using OpenCV DNN"""
        try:
            # Prepare frame for YOLO
            height, width = frame.shape[:2]
            
            # Create blob from image
            blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
            
            # Set input blob
            self.yolo_net.setInput(blob)
            
            # Run inference
            outputs = self.yolo_net.forward(self.output_layers)
            
            # Process detections
            detections = self.process_opencv_outputs(outputs, width, height)
            
            # Draw detections on frame
            processed_frame = self.draw_opencv_detections(frame, detections)
            
            return processed_frame
            
        except Exception as e:
            print(f"⚠️ OpenCV inference error: {e}")
            return self.simulate_yolo_detection(frame)
    
    def process_hailo_outputs(self, outputs, width, height):
        """Process Hailo YOLO network outputs"""
        detections = []
        
        try:
            # Hailo outputs are typically in format [batch, detections, 6] where 6 = [x, y, w, h, confidence, class]
            for output in outputs:
                if len(output.shape) == 3:  # [batch, detections, 6]
                    detections_data = output[0]  # Take first batch
                    
                    for detection in detections_data:
                        if len(detection) >= 6:
                            x, y, w, h, confidence, class_id = detection[:6]
                            
                            if confidence > 0.5:  # Confidence threshold
                                # Convert normalized coordinates to pixel coordinates
                                x1 = int(x * width)
                                y1 = int(y * height)
                                x2 = int((x + w) * width)
                                y2 = int((y + h) * height)
                                
                                # Get class name
                                class_name = self.get_class_name(int(class_id))
                                
                                detections.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'class': class_name,
                                    'confidence': float(confidence)
                                })
            
            return detections
            
        except Exception as e:
            print(f"⚠️ Error processing Hailo outputs: {e}")
            return []
    
    def process_opencv_outputs(self, outputs, width, height):
        """Process OpenCV YOLO network outputs"""
        detections = []
        
        try:
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    
                    if confidence > 0.5:  # Confidence threshold
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)
                        
                        # Calculate bounding box coordinates
                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)
                        
                        detections.append({
                            'bbox': [x, y, x + w, y + h],
                            'class': self.classes[class_id] if class_id < len(self.classes) else f'Class {class_id}',
                            'confidence': float(confidence)
                        })
            
            return detections
            
        except Exception as e:
            print(f"⚠️ Error processing OpenCV outputs: {e}")
            return []
    
    def get_class_name(self, class_id):
        """Get class name for Hailo YOLO"""
        try:
            # COCO class names for YOLOv8
            classes = [
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
            
            if 0 <= class_id < len(classes):
                return classes[class_id]
            else:
                return f'Class {class_id}'
                
        except Exception as e:
            print(f"⚠️ Error getting class name: {e}")
            return f'Class {class_id}'
    
    def draw_hailo_detections(self, frame, detections):
        """Draw Hailo YOLO detections on frame"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(processed_frame, "YOLO Processing Active (Real Inference)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Add detection count
        cv2.putText(processed_frame, f"Detections: {len(detections)}", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw detections
        for detection in detections:
            bbox = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            
            x1, y1, x2, y2 = bbox
            
            # Draw bounding box
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(processed_frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return processed_frame
    
    def draw_opencv_detections(self, frame, detections):
        """Draw OpenCV YOLO detections on frame"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(processed_frame, "YOLO Processing Active (OpenCV Fallback)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Add detection count
        cv2.putText(processed_frame, f"Detections: {len(detections)}", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw detections
        for detection in detections:
            bbox = detection['bbox']
            class_name = detection['class']
            confidence = detection['confidence']
            
            x1, y1, x2, y2 = bbox
            
            # Draw bounding box
            cv2.rectangle(processed_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(processed_frame, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return processed_frame
    
    def simulate_yolo_detection(self, frame):
        """Simulate YOLO detection when model is not available"""
        processed_frame = frame.copy()
        
        # Add timestamp and FPS
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(processed_frame, f"Time: {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(processed_frame, f"FPS: {self.current_fps:.1f}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Add status
        cv2.putText(processed_frame, "YOLO Processing Active (Simulated)", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Add frame counter
        cv2.putText(processed_frame, f"Frame: {self.frame_count}", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        # Add camera info
        cv2.putText(processed_frame, "Real Camera Stream Active", (10, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        return processed_frame
    
    def save_processed_frame(self, frame):
        """Save processed frame for web service to access"""
        try:
            # Save as JPEG for web service
            frame_path = self.output_dir / "latest_frame.jpg"
            cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Also save a copy for the web service to read
            web_frame_path = Path("/tmp/latest_yolo_frame.jpg")
            cv2.imwrite(str(web_frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Update latest frame reference
            with self.frame_lock:
                self.latest_processed_frame = frame.copy()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error saving processed frame: {e}")
            return False
    
    def process_mjpeg_stream(self):
        """Process incoming MJPEG stream and extract frames"""
        print("📹 Starting MJPEG stream processing...")
        print("⏳ Waiting for libcamera-vid MJPEG stream from host...")
        print("🔧 MJPEG is much easier to decode than H.264")
        
        while self.running:
            try:
                # Receive MJPEG data
                data, addr = self.udp_socket.recvfrom(self.buffer_size)
                
                if data:
                    # Add to MJPEG buffer
                    self.mjpeg_buffer += data
                    
                    # Try to decode frame when we have enough data
                    if len(self.mjpeg_buffer) > 1000:  # Minimum size for MJPEG frame
                        print(f"📦 Received {len(data)} bytes, total buffer: {len(self.mjpeg_buffer)} bytes")
                        print(f"🔧 Attempting to decode MJPEG frame...")
                        
                        # Try to decode MJPEG frame
                        frame = self.decode_mjpeg_frame(self.mjpeg_buffer)
                        
                        if frame is not None:
                            print(f"🎯 SUCCESS! Decoded real camera frame: {frame.shape}")
                            
                            # Update frame counter
                            self.frame_count += 1
                            
                            # Run YOLO inference
                            processed_frame = self.run_yolo_inference(frame)
                            
                            # Save processed frame
                            if self.save_processed_frame(processed_frame):
                                # Update FPS counter
                                self.fps_counter += 1
                                current_time = time.time()
                                
                                if current_time - self.fps_start_time >= 1.0:
                                    self.current_fps = self.fps_counter
                                    self.fps_counter = 0
                                    self.fps_start_time = current_time
                                    
                                    # Show which YOLO engine is being used
                                    if self.yolo_model and HAILO_AVAILABLE:
                                        print(f"🚀 Hailo YOLO Processing FPS: {self.current_fps}")
                                    elif hasattr(self, 'yolo_net') and self.yolo_net is not None:
                                        print(f"🔄 OpenCV YOLO Processing FPS: {self.current_fps}")
                                    else:
                                        print(f"🎯 Real Camera Processing FPS: {self.current_fps}")
                            
                            # Clear buffer after successful decode
                            self.mjpeg_buffer = b''
                        else:
                            print(f"⚠️ Failed to decode MJPEG frame, keeping buffer for next attempt")
                            # Keep some data for next attempt
                            if len(self.mjpeg_buffer) > 1024 * 1024:  # 1MB limit
                                self.mjpeg_buffer = self.mjpeg_buffer[-512 * 1024:]  # Keep last 512KB
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️ Error processing stream: {e}")
                break
        
        print("🛑 MJPEG stream processing stopped")
    
    def run(self):
        """Main run loop"""
        print("🎯 Starting Hailo YOLO Processor...")
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
        print("")
        print("🔧 To start video stream, run on the host:")
        print("   libcamera-vid -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 --inline -o udp://127.0.0.1:5000")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.stop()
    
    def stop(self):
        """Stop the processor and cleanup"""
        print("🧹 Cleaning up...")
        self.running = False
        
        if self.udp_socket:
            self.udp_socket.close()
        
        # Clean up temporary files
        try:
            for file_path in self.output_dir.glob("*.jpg"):
                file_path.unlink()
            self.output_dir.rmdir()
        except:
            pass
        
        print("✅ Cleanup complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n📡 Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run processor
    processor = HailoYOLOProcessor()
    
    try:
        processor.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        processor.stop()
        sys.exit(1) 