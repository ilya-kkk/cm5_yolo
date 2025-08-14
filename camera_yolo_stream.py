#!/usr/bin/env python3
"""
YOLOv8 Camera Stream with Hailo 8L
Processes CSI camera feed using YOLOv8 model on Hailo 8L accelerator
and streams processed video via GStreamer
"""

import cv2
import numpy as np
import time
import threading
import queue
import subprocess
import signal
import sys
from hailo_platform import HailoPlatform
from hailo_platform import HailoROI, HailoDetection
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib

class YOLOCameraStream:
    def __init__(self, hef_path, camera_index=0, width=1920, height=1080, fps=30):
        self.hef_path = hef_path
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        
        # Initialize Hailo platform
        self.hailo_platform = HailoPlatform()
        self.hailo_platform.load_model(hef_path)
        
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
        
        # Initialize GStreamer
        Gst.init(None)
        
    def start_camera(self):
        """Start CSI camera capture"""
        try:
            # Use libcamera for CSI camera
            self.camera = cv2.VideoCapture(f"libcamera://{self.camera_index}")
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.camera.isOpened():
                print(f"Failed to open camera {self.camera_index}")
                return False
                
            print(f"Camera started: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
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
    
    def gstreamer_stream_thread(self):
        """Thread for streaming processed video via GStreamer"""
        try:
            # GStreamer pipeline for streaming
            pipeline_str = (
                f"appsrc name=source is-live=true format=time caps=video/x-raw,format=BGR,"
                f"width={self.width},height={self.height},framerate={self.fps}/1 ! "
                f"videoconvert ! video/x-raw,format=I420 ! "
                f"x264enc tune=zerolatency speed-preset=ultrafast ! "
                f"h264parse ! rtph264pay ! "
                f"udpsink host=192.168.0.173 port=5000"
            )
            
            # Create GStreamer pipeline
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.appsrc = self.pipeline.get_by_name("source")
            
            # Set up appsrc properties
            self.appsrc.set_property("do-timestamp", True)
            self.appsrc.set_property("stream-type", 0)  # GST_APP_STREAM_TYPE_STREAM
            
            # Start pipeline
            self.pipeline.set_state(Gst.State.PLAYING)
            
            print("GStreamer pipeline started")
            
            # Stream frames
            while self.running:
                try:
                    if not self.processed_frame_queue.empty():
                        frame = self.processed_frame_queue.get_nowait()
                        
                        # Convert frame to GStreamer buffer
                        height, width = frame.shape[:2]
                        channels = frame.shape[2] if len(frame.shape) > 2 else 1
                        
                        # Create GStreamer buffer
                        buffer = Gst.Buffer.new_wrapped(frame.tobytes())
                        buffer.pts = Gst.util_uint64_scale(self.fps_counter, Gst.SECOND, self.fps)
                        buffer.dts = buffer.pts
                        buffer.duration = Gst.util_uint64_scale(1, Gst.SECOND, self.fps)
                        
                        # Push buffer to pipeline
                        ret = self.appsrc.emit("push-buffer", buffer)
                        if ret != Gst.FlowReturn.OK:
                            print(f"Error pushing buffer: {ret}")
                            break
                            
                    else:
                        time.sleep(0.001)
                        
                except Exception as e:
                    print(f"Error in streaming thread: {e}")
                    time.sleep(0.001)
                    
        except Exception as e:
            print(f"Error setting up GStreamer: {e}")
    
    def start(self):
        """Start the camera stream processing"""
        if not self.start_camera():
            return False
        
        self.running = True
        
        # Start threads
        self.capture_thread = threading.Thread(target=self.camera_capture_thread)
        self.processing_thread_obj = threading.Thread(target=self.processing_thread)
        self.streaming_thread = threading.Thread(target=self.gstreamer_stream_thread)
        
        self.capture_thread.start()
        self.processing_thread_obj.start()
        self.streaming_thread.start()
        
        print("YOLO camera stream started")
        return True
    
    def stop(self):
        """Stop the camera stream processing"""
        self.running = False
        
        # Stop camera
        if hasattr(self, 'camera') and self.camera.isOpened():
            self.camera.release()
        
        # Stop GStreamer pipeline
        if hasattr(self, 'pipeline'):
            self.pipeline.set_state(Gst.State.NULL)
        
        # Wait for threads to finish
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join(timeout=1.0)
        if hasattr(self, 'processing_thread_obj'):
            self.processing_thread_obj.join(timeout=1.0)
        if hasattr(self, 'streaming_thread'):
            self.streaming_thread.join(timeout=1.0)
        
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
        width=1920,
        height=1080,
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