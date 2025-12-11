import base64
import requests
import os

API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"   # replace with your key

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

try:
    # Check if image file exists
    if not os.path.exists("invoice_sample.png"):
        print("Error: invoice_sample.png not found in the current directory.")
        print(f"Current directory: {os.getcwd()}")
        exit(1)
    
    image_base64 = encode_image("invoice_sample.png")

    payload = {
        "model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
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
                        "text": "Extract invoice_number, invoice_date, customer_name, amount."
                    }
                ]
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    res = requests.post(
        "https://api.deepinfra.com/v1/openai/chat/completions",
        json=payload,
        headers=headers,
        timeout=30
    )
    
    if res.status_code == 200:
        print("Success!")
        print(res.json())
    else:
        print(f"API Error: {res.status_code}")
        print(res.text)

except requests.exceptions.ConnectionError as e:
    print("Connection Error: Unable to reach the API.")
    print("Please check:")
    print("  1. Your internet connection")
    print("  2. The API endpoint is accessible")
    print(f"Details: {str(e)}")
except FileNotFoundError as e:
    print(f"File Error: {str(e)}")
except Exception as e:
    print(f"Error: {str(e)}")
