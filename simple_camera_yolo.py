#!/usr/bin/env python3
"""
Simple YOLOv8 Camera Stream with Hailo 8L
Simplified version for testing and debugging
"""

import cv2
import numpy as np
import time
import threading
import queue
import subprocess
import signal
import sys
import os
from hailo_platform import HailoPlatform

class SimpleYOLOCamera:
    def __init__(self, hef_path, camera_index=0, width=1920, height=1080, fps=30):
        self.hef_path = hef_path
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        
        # Initialize Hailo platform
        try:
            self.hailo_platform = HailoPlatform()
            self.hailo_platform.load_model(hef_path)
            print(f"Model loaded successfully: {hef_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.hailo_platform = None
        
        # Video processing variables
        self.frame_queue = queue.Queue(maxsize=5)
        self.running = False
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        # YOLO classes (COCO dataset)
        self.classes = [
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
        
        # Colors for bounding boxes
        np.random.seed(42)
        self.colors = np.random.randint(0, 255, size=(len(self.classes), 3), dtype=np.uint8)
        
        # libcamera-vid process
        self.libcamera_process = None
        
    def start_camera(self):
        """Start CSI camera capture"""
        try:
            # Try different camera backends
            camera_backends = [
                f"libcamera://{self.camera_index}",
                f"v4l2:///dev/video{self.camera_index}",
                f"/dev/video{self.camera_index}"
            ]
            
            for backend in camera_backends:
                try:
                    print(f"Trying camera backend: {backend}")
                    self.camera = cv2.VideoCapture(backend)
                    
                    if self.camera.isOpened():
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                        
                        # Test frame capture
                        ret, test_frame = self.camera.read()
                        if ret:
                            print(f"Camera started successfully: {self.width}x{self.height} @ {self.fps}fps")
                            print(f"Test frame shape: {test_frame.shape}")
                            return True
                        else:
                            print(f"Failed to capture test frame from {backend}")
                            self.camera.release()
                    else:
                        print(f"Failed to open camera with {backend}")
                        
                except Exception as e:
                    print(f"Error with {backend}: {e}")
                    if hasattr(self, 'camera'):
                        self.camera.release()
            
            print("All camera backends failed")
            return False
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def process_frame(self, frame):
        """Process frame with YOLOv8 on Hailo"""
        if not self.hailo_platform:
            return frame
            
        try:
            # Preprocess frame for YOLO
            input_data = self.preprocess_frame(frame)
            
            # Run inference on Hailo
            outputs = self.hailo_platform.infer(input_data)
            
            # Postprocess results
            detections = self.postprocess_outputs(outputs, frame.shape)
            
            # Draw detections on frame
            processed_frame = self.draw_detections(frame, detections)
            
            # Add FPS counter
            processed_frame = self.add_fps_counter(processed_frame)
            
            return processed_frame
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return frame
    
    def preprocess_frame(self, frame):
        """Preprocess frame for YOLO input"""
        # Resize to YOLO input size (assuming 640x640)
        input_size = (640, 640)
        resized = cv2.resize(frame, input_size)
        
        # Convert to RGB and normalize
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        
        # Add batch dimension and transpose to NCHW format
        input_data = np.expand_dims(normalized.transpose(2, 0, 1), axis=0)
        
        return input_data
    
    def postprocess_outputs(self, outputs, original_shape):
        """Postprocess YOLO outputs to get detections"""
        detections = []
        
        try:
            # Get the detection output (assuming it's the first output)
            detection_output = outputs[0] if isinstance(outputs, list) else outputs
            
            # Parse YOLO output format
            if hasattr(detection_output, 'shape'):
                # Assuming output format: [batch, num_detections, 85] (80 classes + 5 bbox coords)
                if len(detection_output.shape) == 3:
                    for detection in detection_output[0]:  # First batch
                        if detection[4] > 0.5:  # Confidence threshold
                            x, y, w, h = detection[0:4]
                            confidence = detection[4]
                            class_id = int(detection[5])
                            
                            # Convert to original image coordinates
                            orig_h, orig_w = original_shape[:2]
                            x1 = int(x * orig_w)
                            y1 = int(y * orig_h)
                            x2 = int((x + w) * orig_w)
                            y2 = int((y + h) * orig_h)
                            
                            detections.append({
                                'bbox': [x1, y1, x2, y2],
                                'confidence': float(confidence),
                                'class_id': class_id,
                                'class_name': self.classes[class_id] if class_id < len(self.classes) else f'class_{class_id}'
                            })
            
        except Exception as e:
            print(f"Error postprocessing outputs: {e}")
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw bounding boxes and labels on frame"""
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection['class_name']
            class_id = detection['class_id']
            
            # Get color for this class
            color = tuple(map(int, self.colors[class_id % len(self.colors)]))
            
            # Draw bounding box
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label background
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (bbox[0], bbox[1] - label_size[1] - 10), 
                         (bbox[0] + label_size[0], bbox[1]), color, -1)
            
            # Draw label text
            cv2.putText(frame, label, (bbox[0], bbox[1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame
    
    def add_fps_counter(self, frame):
        """Add FPS counter to frame"""
        # Update FPS calculation
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
        
        # Draw FPS on frame
        fps_text = f"FPS: {self.current_fps:.1f}"
        cv2.putText(frame, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return frame
    
    def start_libcamera_stream(self):
        """Start libcamera-vid streaming process"""
        try:
            # libcamera-vid command with the specified pipeline
            libcamera_cmd = [
                'libcamera-vid',
                '-t', '0',  # Continuous recording
                '--codec', 'h264',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--inline',
                '-o', 'udp://192.168.0.173:5000'
            ]
            
            print(f"Starting libcamera-vid: {' '.join(libcamera_cmd)}")
            
            # Start libcamera-vid process
            self.libcamera_process = subprocess.Popen(
                libcamera_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            print("libcamera-vid streaming started")
            return True
            
        except Exception as e:
            print(f"Error starting libcamera-vid: {e}")
            return False
    
    def main_loop(self):
        """Main processing loop"""
        if not self.start_camera():
            print("Failed to start camera")
            return False
        
        # Start libcamera-vid streaming
        if not self.start_libcamera_stream():
            print("Failed to start libcamera-vid streaming")
            return False
        
        print("Starting main processing loop...")
        print("Press 'q' to quit, 's' to save frame")
        
        self.running = True
        
        while self.running:
            try:
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    print("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Process frame with YOLO
                processed_frame = self.process_frame(frame)
                
                # Display frame (for debugging)
                cv2.imshow('YOLO Camera Stream', processed_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quit requested")
                    break
                elif key == ord('s'):
                    timestamp = int(time.time())
                    filename = f"frame_{timestamp}.jpg"
                    cv2.imwrite(filename, processed_frame)
                    print(f"Frame saved as {filename}")
                
                # Maintain frame rate
                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(0.1)
        
        return True
    
    def stop(self):
        """Stop the camera stream processing"""
        self.running = False
        
        # Stop camera
        if hasattr(self, 'camera') and self.camera.isOpened():
            self.camera.release()
        
        # Stop libcamera-vid process
        if self.libcamera_process:
            self.libcamera_process.terminate()
            self.libcamera_process.wait()
        
        # Close OpenCV windows
        cv2.destroyAllWindows()
        
        print("Camera stream stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nStopping...")
    if hasattr(signal_handler, 'camera'):
        signal_handler.camera.stop()
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize camera
    camera = SimpleYOLOCamera(
        hef_path="yolov8n.hef",
        camera_index=0,
        width=1920,
        height=1080,
        fps=30
    )
    
    # Store reference for signal handler
    signal_handler.camera = camera
    
    try:
        # Start main loop
        if camera.main_loop():
            print("Camera stream completed successfully")
        else:
            print("Camera stream failed")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        camera.stop()

if __name__ == "__main__":
    main() 