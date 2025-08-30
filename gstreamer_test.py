#!/usr/bin/env python3
"""
Minimal GStreamer test to diagnose the issue
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import sys

def test_gstreamer_basic():
    """Test basic GStreamer functionality"""
    print("🚀 Starting GStreamer basic test...")
    
    try:
        # Test 1: Initialize GStreamer
        print("🔍 Test 1: Initializing GStreamer...")
        Gst.init(None)
        print(f"✅ GStreamer initialized, version: {Gst.version_string()}")
        
        # Test 2: Create simple pipeline
        print("\n🔍 Test 2: Creating simple pipeline...")
        pipeline_str = "videotestsrc ! videoconvert ! fakesink"
        pipeline = Gst.parse_launch(pipeline_str)
        print("✅ Simple pipeline created")
        
        # Test 3: Set pipeline state
        print("\n🔍 Test 3: Setting pipeline state...")
        ret = pipeline.set_state(Gst.State.PLAYING)
        print(f"✅ Pipeline state set to PLAYING: {ret}")
        
        # Test 4: Wait for state change
        print("\n🔍 Test 4: Waiting for state change...")
        ret = pipeline.get_state(Gst.CLOCK_TIME_NONE)
        print(f"✅ Pipeline state: {ret[1]}")
        
        # Test 5: Stop pipeline
        print("\n🔍 Test 5: Stopping pipeline...")
        pipeline.set_state(Gst.State.NULL)
        print("✅ Pipeline stopped")
        
        print("\n🎉 Basic GStreamer test passed!")
        return True
        
    except Exception as e:
        print(f"❌ GStreamer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gstreamer_hailo():
    """Test GStreamer with Hailo elements"""
    print("\n🚀 Starting GStreamer Hailo test...")
    
    try:
        # Test 1: Check Hailo GStreamer elements
        print("🔍 Test 1: Checking Hailo GStreamer elements...")
        registry = Gst.Registry.get()
        
        # Look for Hailo elements
        hailo_elements = []
        for feature in registry.get_feature_list(Gst.ElementFactory):
            if 'hailo' in feature.get_name().lower():
                hailo_elements.append(feature.get_name())
        
        print(f"   Found {len(hailo_elements)} Hailo elements:")
        for element in hailo_elements:
            print(f"     - {element}")
        
        if not hailo_elements:
            print("   ⚠️ No Hailo GStreamer elements found")
            print("   💡 This might be the cause of segmentation fault")
        
        # Test 2: Try to create Hailo pipeline
        print("\n🔍 Test 2: Testing Hailo pipeline creation...")
        try:
            # Try to create a simple Hailo pipeline
            hailo_pipeline_str = "videotestsrc ! hailooverlay ! videoconvert ! fakesink"
            hailo_pipeline = Gst.parse_launch(hailo_pipeline_str)
            print("✅ Hailo pipeline created successfully")
            hailo_pipeline.set_state(Gst.State.NULL)
        except Exception as e:
            print(f"   ❌ Hailo pipeline creation failed: {e}")
            print("   💡 This confirms the issue is with Hailo GStreamer elements")
        
        print("\n🎉 GStreamer Hailo test completed!")
        return True
        
    except Exception as e:
        print(f"❌ GStreamer Hailo test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 GStreamer Diagnostics for Hailo CM5")
    print("=" * 50)
    
    success1 = test_gstreamer_basic()
    success2 = test_gstreamer_hailo()
    
    if success1 and success2:
        print("\n🎉 All GStreamer tests passed!")
        print("💡 The issue might be in hailo-apps integration")
    else:
        print("\n🚨 Some GStreamer tests failed!")
        print("💡 This explains the segmentation fault")
    
    exit(0 if (success1 and success2) else 1)
