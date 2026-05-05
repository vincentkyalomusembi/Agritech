#!/usr/bin/env python3
"""
Direct test of USSD optimization.
Calls get_recommendation directly with ussd_mode to measure performance.
"""

import time
from recommender import get_recommendation

def test_ussd_recommendations():
    """Test USSD-mode recommendations with timing."""
    print("=" * 70)
    print("DIRECT USSD OPTIMIZATION TEST")
    print("=" * 70)
    
    test_cases = [
        {
            "name": "Nairobi Crop (Loamy soil)",
            "county": "Nairobi",
            "farm_type": "crop",
            "soil_type": "loamy",
            "farm_size": "0.5 acres",
            "budget": "50000",
            "experience": "beginner",
        },
        {
            "name": "Mombasa Livestock (Goat)",
            "county": "Mombasa",
            "farm_type": "livestock",
            "soil_type": "sandy",
            "farm_size": "1.0 acres",
            "budget": "30000",
            "experience": "intermediate",
        },
        {
            "name": "Kisumu Crop (Clay soil)",
            "county": "Kisumu",
            "farm_type": "crop",
            "soil_type": "clay",
            "farm_size": "2.0 acres",
            "budget": "75000",
            "experience": "expert",
        },
    ]
    
    print("\n[USSD MODE - Fast Path]")
    print("-" * 70)
    
    ussd_times = []
    for test in test_cases:
        name = test["name"]
        test_dict = {k: v for k, v in test.items() if k != "name"}
        print(f"\n{name}:")
        
        start = time.time()
        result = get_recommendation(**test_dict, ussd_mode=True)
        elapsed = time.time() - start
        ussd_times.append(elapsed)
        
        print(f"  ✓ Time: {elapsed:.3f}s")
        print(f"    Recommendation: {result['recommendation'].title()}")
        print(f"    Options: {result['recommendation_options']}")
        print(f"    Advice length: {len(result['advice'])} chars")
    
    print("\n" + "=" * 70)
    print("[API MODE - Full Pipeline]")
    print("-" * 70)
    
    api_times = []
    for test in test_cases:
        name = test["name"]
        test_dict = {k: v for k, v in test.items() if k != "name"}
        print(f"\n{name}:")
        
        start = time.time()
        result = get_recommendation(**test_dict, ussd_mode=False)
        elapsed = time.time() - start
        api_times.append(elapsed)
        
        print(f"  ✓ Time: {elapsed:.3f}s")
        print(f"    Recommendation: {result['recommendation'].title()}")
        print(f"    Options: {result['recommendation_options']}")
        print(f"    Advice length: {len(result['advice'])} chars")
        print(f"    Has alerts: {'yes' if 'alerts' in result else 'no'}")
        print(f"    Has market data: {'yes' if 'market' in result else 'no'}")
    
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    
    avg_ussd = sum(ussd_times) / len(ussd_times)
    avg_api = sum(api_times) / len(api_times)
    speedup = avg_api / avg_ussd
    
    print(f"\nUSSD Mode (Fast):")
    print(f"  Average time: {avg_ussd:.3f}s")
    print(f"  Min: {min(ussd_times):.3f}s, Max: {max(ussd_times):.3f}s")
    print(f"  Status: {'✓ PASS' if avg_ussd < 2.0 else '✗ WARN'} (Goal: <2.0s)")
    
    print(f"\nAPI Mode (Full):")
    print(f"  Average time: {avg_api:.3f}s")
    print(f"  Min: {min(api_times):.3f}s, Max: {max(api_times):.3f}s")
    print(f"  Status: {'✓ OK' if avg_api < 15.0 else '✗ SLOW'} (Note: Full pipeline)")
    
    print(f"\nSpeedup Factor: {speedup:.1f}x faster for USSD")
    
    print("\n" + "=" * 70)
    print("Africa's Talking USSD Timeout Check")
    print("=" * 70)
    
    safety_margin = 30.0 - (avg_ussd * 1.5)  # 1.5x buffer for network variation
    print(f"\nUSSD Timeout: 30 seconds (Africa's Talking standard)")
    print(f"Expected response time (avg): {avg_ussd:.3f}s")
    print(f"With 1.5x safety margin: {avg_ussd * 1.5:.3f}s")
    print(f"Safety margin remaining: {safety_margin:.3f}s")
    
    if safety_margin > 3.0:
        print(f"✓ SAFE: Plenty of buffer below 30-second timeout")
        return True
    else:
        print(f"✗ WARNING: Close to timeout limit")
        return False

if __name__ == "__main__":
    success = test_ussd_recommendations()
    exit(0 if success else 1)
