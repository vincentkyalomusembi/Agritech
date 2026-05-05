#!/usr/bin/env python3
"""
Test USSD recommendation flow end-to-end.
Simulates the exact user interaction sequence with timing measurements.
"""

import time
from ussd_flow import handle_ussd
import json

def test_ussd_flow():
    """Simulate a complete USSD session with measurements."""
    print("=" * 60)
    print("USSD FLOW TEST - Simulating User Interaction")
    print("=" * 60)
    
    # Simulate USSD session (stateful via phone number)
    phone = "+254712345678"
    inputs = [
        ("", "Main menu"),  # Initial request
        ("1", "Select crop recommendation"),
        ("Nairobi", "Select county"),
        ("Loamy", "Select soil"),
        ("0.5", "Select farm size"),
        ("50000", "Select budget"),
        ("1", "Select experience (beginner)"),
    ]
    
    total_start = time.time()
    
    for i, (text, description) in enumerate(inputs):
        print(f"\n[Step {i+1}] {description}")
        print(f"  Input: '{text}' (phone: {phone})")
        
        step_start = time.time()
        try:
            response = handle_ussd(text, phone)
            step_time = time.time() - step_start
            
            print(f"  Time: {step_time:.3f}s")
            print(f"  Response:")
            
            # Format response for readability
            lines = response.split("\n")
            for line in lines[:8]:  # Show first 8 lines
                print(f"    {line}")
            if len(lines) > 8:
                print(f"    ... (+{len(lines) - 8} more lines)")
                
        except Exception as e:
            step_time = time.time() - step_start
            print(f"  ✗ Error after {step_time:.3f}s: {e}")
            return False
    
    total_time = time.time() - total_start
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total session time: {total_time:.3f}s")
    print(f"Average step time: {total_time / len(inputs):.3f}s")
    
    if total_time < 5:
        print("✓ PASS: Well below 30-second Africa's Talking timeout")
        return True
    else:
        print(f"✗ WARN: {total_time:.1f}s is approaching timeout")
        return False

def test_livestock_flow():
    """Test USSD livestock recommendation flow."""
    print("\n\n" + "=" * 60)
    print("LIVESTOCK USSD FLOW TEST")
    print("=" * 60)
    
    phone = "+254798765432"
    inputs = [
        ("", "Main menu"),
        ("2", "Select livestock recommendation"),
        ("Mombasa", "Select county"),
        ("Goat", "Select herd size/type"),
        ("1.0", "Select farm size"),
        ("30000", "Select budget"),
        ("2", "Select experience (intermediate)"),
    ]
    
    total_start = time.time()
    
    for i, (text, description) in enumerate(inputs):
        print(f"\n[Step {i+1}] {description}")
        print(f"  Input: '{text}'")
        
        step_start = time.time()
        try:
            response = handle_ussd(text, phone)
            step_time = time.time() - step_start
            
            print(f"  Time: {step_time:.3f}s")
            print(f"  First line: {response.split(chr(10))[0][:80]}")
                
        except Exception as e:
            step_time = time.time() - step_start
            print(f"  ✗ Error after {step_time:.3f}s: {e}")
            return False
    
    total_time = time.time() - total_start
    
    print("\n" + "=" * 60)
    print(f"Total session time: {total_time:.3f}s")
    print(f"✓ PASS" if total_time < 5 else "✗ WARN")
    return total_time < 5

if __name__ == "__main__":
    success1 = test_ussd_flow()
    success2 = test_livestock_flow()
    
    print("\n\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Crop flow: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Livestock flow: {'✓ PASS' if success2 else '✗ FAIL'}")
    
    if success1 and success2:
        print("\n✓ All tests passed! USSD is ready for production.")
    else:
        print("\n✗ Some tests failed. Review timing above.")
