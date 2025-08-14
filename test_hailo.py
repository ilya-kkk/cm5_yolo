#!/usr/bin/env python3
"""
Test Hailo Script
Simple script to test Hailo 8L functionality
"""

import numpy as np
import time
import sys

def test_hailo_import():
    """Test if Hailo platform can be imported"""
    try:
        from hailo_platform import HailoPlatform
        print("✅ Hailo platform import successful")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Hailo platform: {e}")
        return False

def test_hailo_platform():
    """Test Hailo platform initialization"""
    try:
        from hailo_platform import HailoPlatform
        
        print("Initializing Hailo platform...")
        platform = HailoPlatform()
        print("✅ Hailo platform initialized successfully")
        
        # Get platform info
        print(f"Platform info: {platform}")
        
        return platform
        
    except Exception as e:
        print(f"❌ Failed to initialize Hailo platform: {e}")
        return None

def test_model_loading(platform, hef_path):
    """Test model loading"""
    try:
        print(f"Loading model: {hef_path}")
        platform.load_model(hef_path)
        print("✅ Model loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return False

def test_inference(platform):
    """Test basic inference"""
    try:
        print("Testing inference with dummy data...")
        
        # Create dummy input data (640x640 RGB image)
        input_data = np.random.rand(1, 3, 640, 640).astype(np.float32)
        print(f"Input data shape: {input_data.shape}")
        print(f"Input data type: {input_data.dtype}")
        
        # Run inference
        start_time = time.time()
        outputs = platform.infer(input_data)
        inference_time = time.time() - start_time
        
        print(f"✅ Inference successful in {inference_time:.3f} seconds")
        print(f"Output type: {type(outputs)}")
        
        if isinstance(outputs, list):
            print(f"Number of outputs: {len(outputs)}")
            for i, output in enumerate(outputs):
                if hasattr(output, 'shape'):
                    print(f"  Output {i} shape: {output.shape}")
                else:
                    print(f"  Output {i}: {output}")
        else:
            if hasattr(outputs, 'shape'):
                print(f"Output shape: {outputs.shape}")
            else:
                print(f"Output: {outputs}")
        
        return True
        
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        return False

def main():
    """Main function"""
    print("Hailo 8L Test Script")
    print("=" * 50)
    
    # Test 1: Import
    if not test_hailo_import():
        print("\n❌ Hailo platform import failed")
        print("Please check Hailo installation")
        return 1
    
    # Test 2: Platform initialization
    platform = test_hailo_platform()
    if not platform:
        print("\n❌ Hailo platform initialization failed")
        return 1
    
    # Test 3: Model loading
    hef_path = "yolov8n.hef"
    if not test_model_loading(platform, hef_path):
        print("\n❌ Model loading failed")
        print("Please check if yolov8n.hef file exists and is valid")
        return 1
    
    # Test 4: Inference
    if not test_inference(platform):
        print("\n❌ Inference test failed")
        return 1
    
    print("\n✅ All Hailo tests passed!")
    print("Hailo 8L is ready for YOLO processing")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 