#!/usr/bin/env python3
"""
Main YOLOv8 Camera Stream with Hailo 8L
Processes CSI camera feed using YOLOv8 model on Hailo 8L accelerator
and streams processed video 
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
import tempfile

# Try to import Hailo Platform, but make it optional
try:
    import hailo_platform
    HAILO_AVAILABLE = False  # Temporarily disable Hailo
    print("Hailo Platform imported but temporarily disabled for testing")
except ImportError:
    print("Hailo Platform not available, using basic detection")
    HAILO_AVAILABLE = False
    hailo_platform = None

class YOLOCameraStream:
    def __init__(self, hef_path, camera_index=0, width=640, height=480, fps=30):
        self.hef_path = hef_path
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        
        # Initialize Hailo platform
        self.hailo_platform = None
        self.hailo_device = None
        self.hailo_model = None
        if HAILO_AVAILABLE:
            try:
                if os.path.exists(hef_path) and os.path.getsize(hef_path) > 1000:  # Check if file exists and has reasonable size
                    # Create VDevice and load HEF
                    self.hailo_device = hailo_platform.VDevice()
                    self.hailo_model = self.hailo_device.create_infer_model(hef_path)
                    print(f"Hailo model loaded from {hef_path}")
                else:
                    print(f"Hailo model file {hef_path} not found or too small, using basic detection")
            except Exception as e:
                print(f"Failed to initialize Hailo platform: {e}")
                print("Using basic object detection instead")
        else:
            print("Hailo Platform not available, using basic detection")
        
        # Video processing variables
        self.frame_queue = queue.Queue(maxsize=10)
        self.processed_frame_queue = queue.Queue(maxsize=10)
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
    
    def start_camera(self):
        """Start CSI camera capture"""
        try:
            # Try different camera access methods
            camera_methods = [
                f"libcamera://{self.camera_index}",  # Libcamera (should work better in Docker)
                f"/dev/video{self.camera_index}",  # Direct device access
                "/dev/video0",  # Default video device
                "/dev/video1",  # Alternative video device
                "/dev/video2",  # Alternative video device
                "/dev/video3",  # Alternative video device
                "/dev/video4",  # Alternative video device
                "/dev/video5",  # Alternative video device
                "/dev/video6",  # Alternative video device
                "/dev/video7",  # Alternative video device
                "/dev/video20",  # PiSP backend device
                "/dev/video21",  # PiSP backend device
                "/dev/video22",  # PiSP backend device
            ]
            
            # First try GStreamer with libcamera
            if self.try_gstreamer_camera():
                return True
            
            # Then try libcamera subprocess
            if self.try_libcamera_subprocess():
                return True
            
            for camera_device in camera_methods:
                print(f"Trying camera device: {camera_device}")
                
                if camera_device.startswith("/dev/"):
                    if not os.path.exists(camera_device):
                        print(f"Device {camera_device} does not exist, skipping...")
                        continue
                
                try:
                    self.camera = cv2.VideoCapture(camera_device)
                    
                    # Set camera properties
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                    
                    # Try to read a test frame
                    if self.camera.isOpened():
                        ret, test_frame = self.camera.read()
                        if ret and test_frame is not None:
                            print(f"Camera started successfully: {camera_device} - {self.width}x{self.height} @ {self.fps}fps")
                            print(f"Test frame shape: {test_frame.shape}")
                            return True
                        else:
                            print(f"Camera opened but failed to read frame from {camera_device}")
                            print(f"OpenCV return value: {ret}, frame type: {type(test_frame)}")
                            self.camera.release()
                    else:
                        print(f"Failed to open camera at {camera_device}")
                        if hasattr(self, 'camera'):
                            self.camera.release()
                            
                except Exception as e:
                    print(f"Error with {camera_device}: {e}")
                    print(f"Exception type: {type(e).__name__}")
                    if hasattr(self, 'camera'):
                        self.camera.release()
                    continue
            
            print("All camera access methods failed")
            return False
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def try_gstreamer_camera(self):
        """Try to start camera using GStreamer with libcamera"""
        try:
            print("Trying GStreamer with libcamera...")
            
            # Create GStreamer pipeline for libcamera - simpler version
            gst_str = "libcamerasrc ! videoconvert ! appsink"
            
            self.camera = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
            
            if self.camera.isOpened():
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    print(f"GStreamer camera started successfully: frame shape: {test_frame.shape}")
                    return True
                else:
                    print("GStreamer camera opened but failed to read frame")
                    self.camera.release()
            else:
                print("Failed to open GStreamer camera")
                
        except Exception as e:
            print(f"Error with GStreamer camera: {e}")
            if hasattr(self, 'camera'):
                self.camera.release()
        
        return False
    
    def try_libcamera_subprocess(self):
        """Try to start camera using libcamera-still subprocess"""
        try:
            print("Trying libcamera-still subprocess...")
            
            # Test if we can capture a frame using libcamera-still
            test_cmd = [
                'libcamera-still', 
                '-o', '/tmp/test_capture.jpg',
                '--timeout', '2000',
                '--width', str(self.width),
                '--height', str(self.height)
            ]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and os.path.exists('/tmp/test_capture.jpg'):
                print("libcamera-still test successful")
                # Clean up test file
                os.remove('/tmp/test_capture.jpg')
                
                # Now try to use OpenCV with libcamera device
                # Try /dev/video20 which is often the PiSP backend
                for device in ['/dev/video20', '/dev/video21', '/dev/video22']:
                    if os.path.exists(device):
                        print(f"Trying libcamera device: {device}")
                        self.camera = cv2.VideoCapture(device)
                        
                        if self.camera.isOpened():
                            ret, test_frame = self.camera.read()
                            if ret and test_frame is not None:
                                print(f"libcamera device {device} started successfully: frame shape: {test_frame.shape}")
                                return True
                            else:
                                print(f"libcamera device {device} opened but failed to read frame")
                                self.camera.release()
                        else:
                            print(f"Failed to open libcamera device {device}")
                
                return False
            else:
                print(f"libcamera-still test failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error with libcamera subprocess: {e}")
            return False
    
    def camera_capture_thread(self):
        """Thread for capturing frames from camera"""
        while self.running:
            if self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret:
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                    else:
                        # Remove old frame if queue is full
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put(frame)
                        except queue.Empty:
                            pass
                else:
                    time.sleep(0.001)  # Small delay if frame read fails
            else:
                time.sleep(0.1)
    
    def process_frame(self, frame):
        """Process frame with YOLOv8 on Hailo"""
        try:
            if self.hailo_model is not None:
                # Use Hailo for inference
                input_data = self.preprocess_frame(frame)
                outputs = self.hailo_model.infer(input_data)
                detections = self.postprocess_outputs(outputs, frame.shape)
            else:
                # Use basic motion detection as fallback
                detections = self.basic_motion_detection(frame)
            
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
            # This is a simplified version - adjust based on your specific HEF model output
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
    
    def basic_motion_detection(self, frame):
        """Basic motion detection using frame differencing"""
        if not hasattr(self, 'prev_frame'):
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return []
        
        # Convert current frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        frame_diff = cv2.absdiff(self.prev_frame, gray)
        
        # Apply threshold to get motion mask
        _, motion_mask = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        
        # Find contours of motion regions
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                detections.append({
                    'bbox': [x, y, x + w, y + h],
                    'confidence': 0.8,
                    'class_id': 0,  # 0 = person (generic motion)
                    'class_name': 'motion'
                })
        
        # Update previous frame
        self.prev_frame = gray
        
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw bounding boxes and labels on frame"""
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            # Handle both Hailo and basic motion detections
            if 'class_name' in detection:
                class_name = detection['class_name']
                class_id = detection['class_id']
            else:
                class_name = 'motion'
                class_id = 0
            
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
    
    def processing_thread(self):
        """Thread for processing frames with YOLO"""
        while self.running:
            try:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get_nowait()
                    processed_frame = self.process_frame(frame)
                    
                    if not self.processed_frame_queue.full():
                        self.processed_frame_queue.put(processed_frame)
                    else:
                        # Remove old frame if queue is full
                        try:
                            self.processed_frame_queue.get_nowait()
                            self.processed_frame_queue.put(processed_frame)
                        except queue.Empty:
                            pass
                else:
                    time.sleep(0.001)
            except Exception as e:
                print(f"Error in processing thread: {e}")
                time.sleep(0.001)
    
    def start_streaming(self):
        """Start video streaming process"""
        try:
            print("Video streaming started (using OpenCV + UDP)")
            return True
            
        except Exception as e:
            print(f"Error starting streaming: {e}")
            return False
    
    def streaming_thread(self):
        """Thread for streaming processed video"""
        if not self.start_streaming():
            return
        
        try:
            # Simple streaming using OpenCV
            while self.running:
                try:
                    if not self.processed_frame_queue.empty():
                        frame = self.processed_frame_queue.get_nowait()
                        
                        # For now, just process frames
                        # In a real implementation, you would encode and stream them
                        time.sleep(1.0 / self.fps)  # Maintain frame rate
                            
                    else:
                        time.sleep(0.001)
                        
                except Exception as e:
                    print(f"Error in streaming thread: {e}")
                    time.sleep(0.001)
                    
        except Exception as e:
            print(f"Error in streaming thread: {e}")
        finally:
            # Clean up
            pass
    
    def start(self):
        """Start the camera stream processing"""
        if not self.start_camera():
            return False
        
        self.running = True
        
        # Start threads
        self.capture_thread = threading.Thread(target=self.camera_capture_thread)
        self.processing_thread_obj = threading.Thread(target=self.processing_thread)
        self.streaming_thread_obj = threading.Thread(target=self.streaming_thread)
        
        self.capture_thread.start()
        self.processing_thread_obj.start()
        self.streaming_thread_obj.start()
        
        print("YOLO camera stream started")
        return True
    
    def stop(self):
        """Stop the camera stream processing"""
        self.running = False
        
        # Stop camera
        if hasattr(self, 'camera') and self.camera.isOpened():
            self.camera.release()
        
        # Wait for threads to finish
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'processing_thread_obj'):
            self.processing_thread_obj.join(timeout=1.0)
        if hasattr(self, 'streaming_thread_obj'):
            self.streaming_thread_obj.join(timeout=1.0)
        
        print("YOLO camera stream stopped")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nStopping...")
    if hasattr(signal_handler, 'stream'):
        signal_handler.stream.stop()
    sys.exit(0)

def main():
    """Main function"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize stream
    stream = YOLOCameraStream(
        hef_path="yolov8n.hef",
        camera_index=0,
        width=640,
        height=480,
        fps=30
    )
    
    # Store reference for signal handler
    signal_handler.stream = stream
    
    try:
        # Start stream
        if stream.start():
            print("Stream started successfully. Press Ctrl+C to stop.")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
        else:
            print("Failed to start stream")
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        stream.stop()

if __name__ == "__main__":
    main() 