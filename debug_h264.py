#!/usr/bin/env python3
"""
Debug script to analyze H.264 stream from libcamera-vid
"""

import socket
import time
import struct

def analyze_h264_stream():
    """Analyze H.264 stream in detail"""
    print("🔍 Analyzing H.264 stream from libcamera-vid...")
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 5000))
    sock.settimeout(5.0)
    
    print("✅ UDP socket created, waiting for data...")
    
    try:
        # Receive data
        data, addr = sock.recvfrom(65536)
        
        if data:
            print(f"📦 Received {len(data)} bytes from {addr}")
            print(f"📊 First 100 bytes: {data[:100]}")
            print(f"🔢 Hex dump (first 200 bytes):")
            
            # Hex dump
            for i in range(0, min(200, len(data)), 16):
                chunk = data[i:i+16]
                hex_str = ' '.join(f'{b:02x}' for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                print(f"{i:04x}: {hex_str:<48} {ascii_str}")
            
            # Analyze NAL units
            print(f"\n🎯 NAL Unit Analysis:")
            
            # Find start codes
            start_codes = [b'\x00\x00\x01', b'\x00\x00\x00\x01']
            nal_units = []
            
            for start_code in start_codes:
                pos = 0
                while True:
                    pos = data.find(start_code, pos)
                    if pos == -1:
                        break
                    
                    # Extract NAL unit type
                    if pos + len(start_code) < len(data):
                        nal_type = data[pos + len(start_code)] & 0x1F
                        nal_type_name = get_nal_type_name(nal_type)
                        
                        print(f"  Found start code at {pos}: NAL type {nal_type} ({nal_type_name})")
                        
                        # Find next start code
                        next_pos = -1
                        for next_start in start_codes:
                            next_pos = data.find(next_start, pos + 1)
                            if next_pos != -1:
                                break
                        
                        if next_pos != -1:
                            nal_unit = data[pos:next_pos]
                        else:
                            nal_unit = data[pos:]
                        
                        nal_units.append((nal_type, nal_type_name, len(nal_unit)))
                    
                    pos += 1
            
            print(f"\n📋 NAL Units found: {len(nal_units)}")
            for i, (nal_type, nal_name, size) in enumerate(nal_units):
                print(f"  {i+1}. Type {nal_type} ({nal_name}): {size} bytes")
            
            # Check for SPS/PPS
            has_sps = any(nal_type == 7 for nal_type, _, _ in nal_units)
            has_pps = any(nal_type == 8 for nal_type, _, _ in nal_units)
            
            print(f"\n🔍 Stream Analysis:")
            print(f"  SPS (Sequence Parameter Set): {'✅' if has_sps else '❌'}")
            print(f"  PPS (Picture Parameter Set): {'✅' if has_pps else '❌'}")
            
            if not has_sps or not has_pps:
                print(f"\n🚨 PROBLEM: Missing SPS/PPS data!")
                print(f"   This is why H.264 decoding fails.")
                print(f"   libcamera-vid is sending incomplete H.264 stream.")
            
            return data
        else:
            print("❌ No data received")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        sock.close()

def get_nal_type_name(nal_type):
    """Get human-readable NAL type name"""
    nal_types = {
        0: "Unspecified",
        1: "Coded slice of a non-IDR picture",
        2: "Coded slice data partition A",
        3: "Coded slice data partition B", 
        4: "Coded slice data partition C",
        5: "Coded slice of an IDR picture",
        6: "Supplemental enhancement information (SEI)",
        7: "Sequence parameter set (SPS)",
        8: "Picture parameter set (PPS)",
        9: "Access unit delimiter",
        10: "End of sequence",
        11: "End of stream",
        12: "Filler data",
        13: "Sequence parameter set extension",
        14: "Prefix NAL unit",
        15: "Subset sequence parameter set",
        16: "Reserved",
        17: "Reserved",
        18: "Reserved",
        19: "Coded slice of an auxiliary coded picture without partitioning",
        20: "Coded slice extension",
        21: "Coded slice extension for depth view components"
    }
    return nal_types.get(nal_type, f"Unknown ({nal_type})")

if __name__ == "__main__":
    analyze_h264_stream() 