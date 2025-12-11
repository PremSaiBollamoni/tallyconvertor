import requests
import base64
import json
import os

API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"

print("Testing Vision API Connection...")
print(f"Endpoint: {DEEPINFRA_ENDPOINT}")
print(f"Model: {MODEL}")
print()

# Check if sample image exists
if not os.path.exists("invoice_sample.png"):
    print("❌ invoice_sample.png not found")
    print("Please add a sample invoice image first")
    exit(1)

# Encode image
print("✓ Loading image...")
with open("invoice_sample.png", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode("utf-8")
print(f"✓ Image encoded ({len(image_base64)} chars)")
print()

# Prepare request
print("Preparing API request...")
payload = {
    "model": MODEL,
    "max_tokens": 4092,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": """Extract invoice information and return as JSON:
                    {
                        "invoice_number": "...",
                        "invoice_date": "...",
                        "customer_name": "...",
                        "total_amount": "...",
                        "items": []
                    }
                    Return only valid JSON."""
                }
            ]
        }
    ]
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print(f"✓ Headers: Authorization: Bearer {API_KEY[:20]}...")
print()

# Make request
print("Sending request to Vision API...")
try:
    response = requests.post(
        DEEPINFRA_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=60
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        print("✅ API Connection: SUCCESS")
        print("\nResponse Content:")
        print(json.dumps(response.json(), indent=2)[:500])
    else:
        print(f"❌ API Error: {response.status_code}")
        print("\nResponse:")
        print(response.text[:500])
        
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {str(e)}")
    print("\nPossible causes:")
    print("- Network connection issue")
    print("- API endpoint is down")
    print("- Firewall or proxy blocking")
    
except requests.exceptions.Timeout as e:
    print(f"❌ Timeout Error: {str(e)}")
    print("API is taking too long to respond")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
