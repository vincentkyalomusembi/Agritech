import requests

# Test USSD flow
def test_ussd():
    base_url = "http://localhost:8000"
    
    # Test 1: Main menu
    print("=== Testing main menu ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001",  # Known user
        "text": ""
    })
    print(f"Response: {response.text}")
    
    # Test 2: Crop Recommendation flow
    print("\n=== Testing Crop Recommendation ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#", 
        "phoneNumber": "+254700000001",
        "text": "1"
    })
    print(f"Response: {response.text}")
    
    # Test 3: Full crop recommendation
    print("\n=== Testing full crop recommendation ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "1*Makueni*sandy"
    })
    print(f"Response: {response.text}")
    
    # Test 4: Weather Alerts
    print("\n=== Testing Weather Alerts ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "3*Makueni"
    })
    print(f"Response: {response.text}")
    
    # Test 5: Disease Alerts
    print("\n=== Testing Disease Alerts ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "4*Nakuru"
    })
    print(f"Response: {response.text}")
    
    # Test 6: Market Prices
    print("\n=== Testing Market Prices ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "5*1"
    })
    print(f"Response: {response.text}")
    
    # Test 7: Expert Visit
    print("\n=== Testing Expert Visit ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "6*1"
    })
    print(f"Response: {response.text}")
    
    # Test 8: Advisory Tips
    print("\n=== Testing Advisory Tips ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "7"
    })
    print(f"Response: {response.text}")
    
    # Test 9: My Profile
    print("\n=== Testing My Profile ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "8"
    })
    print(f"Response: {response.text}")
    
    # Test 10: Subscribe
    print("\n=== Testing Subscribe ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "9"
    })
    print(f"Response: {response.text}")
    
    # Test 11: Livestock Recommendation
    print("\n=== Testing Livestock Recommendation ===")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254700000001", 
        "text": "2*Nyeri*loamy"
    })
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_ussd()