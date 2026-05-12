import requests

# Test USSD flow
def test_ussd():
    base_url = "http://localhost:8000"
    
    # Test 1: Main menu
    print("Testing main menu...")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254711000000",
        "text": ""
    })
    print(f"Response: {response.text}")
    
    # Test 2: Select option 1
    print("\nTesting option 1...")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#", 
        "phoneNumber": "+254711000000",
        "text": "1"
    })
    print(f"Response: {response.text}")
    
    # Test 3: Full flow
    print("\nTesting full flow...")
    response = requests.post(f"{base_url}/ussd", data={
        "sessionId": "123",
        "serviceCode": "*384*1234#",
        "phoneNumber": "+254711000000", 
        "text": "1*Nairobi*loamy"
    })
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_ussd()