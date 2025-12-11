import requests
import time
import sys

DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"

def test_connection():
    print("--- STARTING CONNECTION TEST ---")
    
    # 1. Basic DNS/Ping check
    print("\n1. Testing GET https://api.deepinfra.com ...")
    try:
        r = requests.get("https://api.deepinfra.com", timeout=10)
        print(f"   Status Code: {r.status_code}")
    except Exception as e:
        print(f"   GET FAILED: {type(e).__name__}: {e}")

    # 2. Test API Auth with valid model
    print("\n2. Testing POST to API (Auth + Chat Completion) ...")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    # Use a known-good text model for this basic test
    payload = {
        "model": "meta-llama/Meta-Llama-3-8B-Instruct", 
        "messages": [{"role": "user", "content": "Ping"}]
    }
    
    try:
        t0 = time.time()
        print(f"   Sending request to {DEEPINFRA_ENDPOINT}...")
        r = requests.post(DEEPINFRA_ENDPOINT, json=payload, headers=headers, timeout=30)
        t1 = time.time()
        print(f"   Time elapsed: {t1-t0:.2f}s")
        print(f"   Status Code: {r.status_code}")
        
        if r.status_code == 200:
            print("   SUCCESS! Response content:")
            print(r.text[:200] + "...")
        else:
            print("   API RETURNED ERROR:")
            print(r.text)
            
    except requests.exceptions.ConnectionError as e:
        print(f"   CONNECTION ERROR CAUGHT: {e}")
    except requests.exceptions.Timeout as e:
        print(f"   TIMEOUT ERROR CAUGHT: {e}")
    except Exception as e:
        print(f"   GENERAL ERROR CAUGHT: {type(e).__name__}: {e}")

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    test_connection()
