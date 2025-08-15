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
    HAILO_AVAILABLE = True  # Enable Hailo
    print("Hailo Platform imported successfully")
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
        
        # External camera stream process
        self.libcamera_process = None
        
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
        """Start camera capture from UDP stream"""
        try:
            print("Starting camera from UDP stream...")
            
            # Wait a bit for stream to stabilize
            time.sleep(2)
            
            # Try to connect to UDP stream from external libcamera-vid process
            udp_url = "udp://127.0.0.1:5000"
            
            # Use GStreamer to read from UDP stream
            gst_str = f"udpsrc port=5000 ! jpegdec ! videoconvert ! appsink"
            
            print(f"Trying GStreamer UDP stream: {gst_str}")
            
            self.camera = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
            
            if self.camera.isOpened():
                # Wait a bit for stream to start
                time.sleep(2)
                
                # Try to read a test frame
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    print(f"UDP stream camera started successfully: frame shape: {test_frame.shape}")
                    return True
                else:
                    print("UDP stream camera opened but failed to read frame")
                    self.camera.release()
            else:
                print("Failed to open UDP stream camera")
            
            # Fallback: try direct UDP with OpenCV
            print("Trying direct UDP with OpenCV...")
            self.camera = cv2.VideoCapture(udp_url)
            
            if self.camera.isOpened():
                time.sleep(2)
                ret, test_frame = self.camera.read()
                if ret and test_frame is not None:
                    print(f"Direct UDP camera started successfully: frame shape: {test_frame.shape}")
                    return True
                else:
                    print("Direct UDP camera opened but failed to read frame")
                    self.camera.release()
            else:
                print("Failed to open direct UDP camera")
            
            print("All camera access methods failed")
            return False
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def try_gstreamer_camera(self):
        """Try to start camera using GStreamer with libcamera"""
        # This method is no longer used with UDP stream approach
        return False
    
    def try_libcamera_subprocess(self):
        """Try to start camera using libcamera-still subprocess"""
        # This method is no longer used with UDP stream approach
        return False
    
    def try_libcamera_vid_streaming(self):
        """Try to start camera using libcamera-vid streaming"""
        # This method is no longer used with UDP stream approach
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
        return self.start_processed_video_streaming()
    
    def streaming_thread(self):
        """Thread for streaming processed video"""
        if not self.start_streaming():
            return
        
        # Initialize frame counter
        frame_counter = 0
        
        try:
            # Stream processed frames using GStreamer
            while self.running:
                try:
                    if not self.processed_frame_queue.empty():
                        frame = self.processed_frame_queue.get_nowait()
                        
                        # Save processed frame with sequential numbering
                        temp_file = f"/tmp/processed_frame_{frame_counter}.jpg"
                        cv2.imwrite(temp_file, frame)
                        
                        # Increment counter
                        frame_counter += 1
                        
                        # Keep only last 100 frames to avoid disk space issues
                        if frame_counter > 100:
                            old_file = f"/tmp/processed_frame_{frame_counter - 100}.jpg"
                            if os.path.exists(old_file):
                                os.remove(old_file)
                        
                        time.sleep(1.0 / self.fps)  # Maintain frame rate
                            
                    else:
                        time.sleep(0.001)
                        
                except Exception as e:
                    print(f"Error in streaming thread: {e}")
                    time.sleep(0.001)
                    
        except Exception as e:
            print(f"Error in streaming thread: {e}")
        finally:
            # Clean up temporary files
            for i in range(max(0, frame_counter - 100), frame_counter):
                temp_file = f"/tmp/processed_frame_{i}.jpg"
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
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
        
        # Wait for threads to finish
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'processing_thread_obj'):
            self.processing_thread_obj.join(timeout=1.0)
        if hasattr(self, 'streaming_thread_obj'):
            self.streaming_thread_obj.join(timeout=1.0)
        
        # Cleanup all resources
        self.cleanup()
        
        print("YOLO camera stream stopped")

    def start_processed_video_streaming(self):
        """Start streaming of processed video"""
        try:
            print("Starting processed video streaming...")
            
            # For now, just save processed frames to /tmp for debugging
            # The main YOLO processing will still work and save frames
            print("Processed video frames will be saved to /tmp/processed_frame_*.jpg")
            print("You can view them manually or use external tools to stream them")
            return True
                
        except Exception as e:
            print(f"Error starting processed video streaming: {e}")
            return False

    def ensure_camera_stream_running(self):
        """Ensure external camera stream is running"""
        try:
            # Check if libcamera-vid is already running
            result = subprocess.run(['pgrep', '-f', 'libcamera-vid'], capture_output=True, text=True)
            if result.returncode == 0:
                print("External camera stream already running")
                return True
            
            print("Starting external camera stream...")
            
            # Start libcamera-vid streaming process
            stream_cmd = [
                'libcamera-vid',
                '-t', '0',  # Stream indefinitely
                '--codec', 'h264',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--inline',
                '-o', 'udp://127.0.0.1:5000'  # Stream to local UDP port
            ]
            
            print(f"Starting libcamera-vid: {' '.join(stream_cmd)}")
            
            # Start the streaming process
            self.libcamera_process = subprocess.Popen(
                stream_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait a bit for the process to start
            time.sleep(3)
            
            # Check if process is still running
            if self.libcamera_process.poll() is None:
                print("External camera stream started successfully")
                return True
            else:
                print("Failed to start external camera stream")
                stdout, stderr = self.libcamera_process.communicate()
                print(f"stdout: {stdout.decode()}")
                print(f"stderr: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"Error starting external camera stream: {e}")
            return False

    def stop_camera(self):
        """Stop camera capture and cleanup"""
        try:
            if hasattr(self, 'camera') and self.camera is not None:
                self.camera.release()
                self.camera = None
                print("Camera stopped")
            
            # Stop external camera stream process
            if hasattr(self, 'libcamera_process') and self.libcamera_process is not None:
                try:
                    self.libcamera_process.terminate()
                    self.libcamera_process.wait(timeout=5)
                    print("External camera stream stopped")
                except subprocess.TimeoutExpired:
                    self.libcamera_process.kill()
                    print("External camera stream force killed")
                except Exception as e:
                    print(f"Error stopping external camera stream: {e}")
                finally:
                    self.libcamera_process = None
                    
        except Exception as e:
            print(f"Error stopping camera: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.stop_camera()
            print("Camera resources cleaned up")
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

def signal_handler(sig, frame):
    """Handle Ctrl+C signal"""
    print("\nReceived interrupt signal, stopping stream...")
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