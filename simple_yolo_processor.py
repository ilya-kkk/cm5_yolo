#!/usr/bin/env python3
"""
Simple YOLO processor that works with existing libcamera-vid stream
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

# Try to import Hailo Platform
try:
    import hailo_platform
    HAILO_AVAILABLE = True
    print("Hailo Platform imported successfully")
except ImportError:
    print("Hailo Platform not available, using basic detection")
    HAILO_AVAILABLE = False
    hailo_platform = None

class SimpleYOLOProcessor:
    def __init__(self, hef_path, width=640, height=480, fps=30):
        self.hef_path = hef_path
        self.width = width
        self.height = height
        self.fps = fps
        
        # Initialize Hailo platform
        self.hailo_device = None
        self.hailo_model = None
        if HAILO_AVAILABLE:
            try:
                if os.path.exists(hef_path) and os.path.getsize(hef_path) > 1000:
                    self.hailo_device = hailo_platform.VDevice()
                    self.hailo_model = self.hailo_device.create_infer_model(hef_path)
                    print(f"Hailo model loaded from {hef_path}")
                else:
                    print(f"Hailo model file {hef_path} not found or too small, using basic detection")
            except Exception as e:
                print(f"Failed to initialize Hailo platform: {e}")
                print("Using basic object detection instead")
        
        # Processing variables
        self.frame_queue = queue.Queue(maxsize=10)
        self.processed_frame_queue = queue.Queue(maxsize=10)
        self.running = False
        
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
    
    def start_input_stream(self):
        """Start receiving input stream from libcamera-vid"""
        try:
            print("Starting input stream receiver...")
            
            # Open UDP stream from libcamera-vid (port 5000)
            gst_str = "udpsrc port=5000 ! h264parse ! avdec_h264 ! videoconvert ! appsink"
            
            self.input_camera = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
            
            if self.input_camera.isOpened():
                ret, test_frame = self.input_camera.read()
                if ret and test_frame is not None:
                    print(f"Input stream opened successfully: frame shape: {test_frame.shape}")
                    return True
                else:
                    print("Input stream opened but failed to read frame")
                    return False
            else:
                print("Failed to open input stream")
                return False
                
        except Exception as e:
            print(f"Error starting input stream: {e}")
            return False
    
    def start_output_stream(self):
        """Start streaming processed video using multifilesrc"""
        try:
            print("Starting output stream with multifilesrc...")
            
            # Create GStreamer pipeline that reads saved frames and streams them
            gst_str = (
                f"multifilesrc location=/tmp/yolo_frame_%04d.jpg loop=true ! "
                f"jpegdec ! videoconvert ! x264enc tune=zerolatency ! "
                f"h264parse ! rtph264pay ! udpsink host=127.0.0.1 port=5001"
            )
            
            print(f"GStreamer command: {gst_str}")
            
            # Start GStreamer process
            self.gst_process = subprocess.Popen([
                'gst-launch-1.0', '-q', gst_str
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for GStreamer to start
            time.sleep(3)
            
            if self.gst_process.poll() is None:
                print("Output streaming started successfully on port 5001")
                return True
            else:
                print("Failed to start output streaming")
                stdout, stderr = self.gst_process.communicate()
                print(f"stdout: {stdout.decode()}")
                print(f"stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"Error starting output stream: {e}")
            return False
    
    def process_frame(self, frame):
        """Process frame with YOLO"""
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
            
            return processed_frame
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return frame
    
    def preprocess_frame(self, frame):
        """Preprocess frame for YOLO input"""
        # Resize to YOLO input size
        input_size = (640, 640)
        resized = cv2.resize(frame, input_size)
        
        # Convert to RGB and normalize
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        
        # Add batch dimension and transpose to NCHW format
        input_data = np.expand_dims(normalized.transpose(2, 0, 1), axis=0)
        
        return input_data
    
    def postprocess_outputs(self, outputs, original_shape):
        """Postprocess YOLO outputs"""
        detections = []
        
        try:
            # Simplified postprocessing
            detection_output = outputs[0] if isinstance(outputs, list) else outputs
            
            if hasattr(detection_output, 'shape'):
                if len(detection_output.shape) == 3:
                    for detection in detection_output[0]:
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
        """Basic motion detection"""
        if not hasattr(self, 'prev_frame'):
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_diff = cv2.absdiff(self.prev_frame, gray)
        _, motion_mask = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                detections.append({
                    'bbox': [x, y, x + w, y + h],
                    'confidence': 0.8,
                    'class_id': 0,
                    'class_name': 'motion'
                })
        
        self.prev_frame = gray
        return detections
    
    def draw_detections(self, frame, detections):
        """Draw bounding boxes and labels"""
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection.get('class_name', 'motion')
            class_id = detection.get('class_id', 0)
            
            color = tuple(map(int, self.colors[class_id % len(self.colors)]))
            
            # Draw bounding box
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (bbox[0], bbox[1] - label_size[1] - 10), 
                         (bbox[0] + label_size[0], bbox[1]), color, -1)
            cv2.putText(frame, label, (bbox[0], bbox[1] - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame
    
    def input_thread(self):
        """Thread for receiving input frames"""
        while self.running:
            if self.input_camera.isOpened():
                ret, frame = self.input_camera.read()
                if ret:
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                    else:
                        try:
                            self.frame_queue.get_nowait()
                            self.frame_queue.put(frame)
                        except queue.Empty:
                            pass
                else:
                    time.sleep(0.001)
            else:
                time.sleep(0.1)
    
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
    
    def output_thread(self):
        """Thread for streaming processed frames"""
        try:
            while self.running:
                if not self.processed_frame_queue.empty():
                    frame = self.processed_frame_queue.get_nowait()
                    
                    # Save processed frame with sequential numbering
                    frame_counter = getattr(self, 'frame_counter', 0)
                    temp_file = f"/tmp/yolo_frame_{frame_counter:04d}.jpg"
                    cv2.imwrite(temp_file, frame)
                    
                    # Increment counter
                    self.frame_counter = frame_counter + 1
                    
                    # Keep only last 100 frames to avoid disk space issues
                    if frame_counter > 100:
                        old_file = f"/tmp/yolo_frame_{frame_counter - 100:04d}.jpg"
                        if os.path.exists(old_file):
                            try:
                                os.remove(old_file)
                            except:
                                pass
                    
                    print(f"Saved processed frame: {temp_file}")
                    time.sleep(1.0 / self.fps)
                else:
                    time.sleep(0.001)
                    
        except Exception as e:
            print(f"Error in output thread: {e}")
    
    def start(self):
        """Start the processor"""
        if not self.start_input_stream():
            print("Failed to start input stream")
            return False
        
        self.running = True
        
        # Start threads
        self.input_thread_obj = threading.Thread(target=self.input_thread)
        self.processing_thread_obj = threading.Thread(target=self.processing_thread)
        self.output_thread_obj = threading.Thread(target=self.output_thread)
        
        self.input_thread_obj.start()
        self.processing_thread_obj.start()
        self.output_thread_obj.start()
        
        print("YOLO processor started")
        return True
    
    def stop(self):
        """Stop the processor"""
        self.running = False
        
        if hasattr(self, 'gst_process') and self.gst_process:
            try:
                self.gst_process.terminate()
                self.gst_process.wait(timeout=5)
                print("GStreamer process stopped")
            except:
                self.gst_process.kill()
        
        if hasattr(self, 'input_camera') and self.input_camera.isOpened():
            self.input_camera.release()
        
        # Wait for threads
        if hasattr(self, 'input_thread_obj'):
            self.input_thread_obj.join(timeout=1.0)
        if hasattr(self, 'processing_thread_obj'):
            self.processing_thread_obj.join(timeout=1.0)
        if hasattr(self, 'output_thread_obj'):
            self.output_thread_obj.join(timeout=1.0)
        
        print("YOLO processor stopped")

def main():
    """Main function"""
    signal.signal(signal.SIGINT, signal_handler)
    
    processor = SimpleYOLOProcessor(
        hef_path="yolov8n.hef",
        width=640,
        height=480,
        fps=30
    )
    
    signal_handler.processor = processor
    
    try:
        if processor.start():
            print("Processor started successfully. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        else:
            print("Failed to start processor")
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        processor.stop()

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nStopping...")
    if hasattr(signal_handler, 'processor'):
        signal_handler.processor.stop()
    sys.exit(0)

if __name__ == "__main__":
    main() 