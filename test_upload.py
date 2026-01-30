
import httpx
import os
import sys

# Constants
API_URL = "http://localhost:8000/upload"
IMAGE_PATH = "/home/web3_moxpc0/help2earn/backend/uploads/facilities/pending/54effc8f-10c6-4f36-b8ae-aabf569bbfaf.jpg"
WALLET = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
LAT = 19.0760
LNG = 72.8777

def test_upload():
    print(f"Testing upload to {API_URL}...")
    
    if not os.path.exists(IMAGE_PATH):
        print(f"Error: Image not found at {IMAGE_PATH}")
        return

    try:
        files = {'image': ('test_image.jpg', open(IMAGE_PATH, 'rb'), 'image/jpeg')}
        data = {
            'latitude': str(LAT),
            'longitude': str(LNG),
            'wallet_address': WALLET
        }
        
        # Increase timeout because agent workflow takes time (Gemini + Blockchain)
        timeout = httpx.Timeout(120.0, connect=10.0)
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(API_URL, files=files, data=data)
            
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(response.text)
        
        if response.status_code == 200:
            print("\nSUCCESS: Workflow completed!")
        else:
            print("\nFAILURE: Request failed.")
            
    except Exception as e:
        print(f"Error during request: {e}")

if __name__ == "__main__":
    test_upload()
