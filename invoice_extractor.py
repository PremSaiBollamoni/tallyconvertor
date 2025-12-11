import base64
import requests
import json
import os
from typing import Dict, List, Optional

API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
MODEL = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_invoice_data(image_path: str) -> Dict:
    """
    Extract invoice data from an image using the Vision API.
    
    Returns:
        Dictionary with extracted invoice data
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    image_base64 = encode_image(image_path)
    
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
                        "text": """Extract the following invoice information and return as JSON:
                        {
                            "invoice_number": "...",
                            "invoice_date": "...",
                            "customer_name": "...",
                            "amount": "...",
                            "currency": "...",
                            "items": []
                        }
                        
                        Only return valid JSON, no additional text."""
                    }
                ]
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        DEEPINFRA_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    return response.json()


def parse_vision_response(api_response: Dict) -> List[Dict]:
    """
    Parse the Vision API response and extract structured invoice data.
    
    Args:
        api_response: Raw response from Vision API
        
    Returns:
        List of dictionaries with invoice data
    """
    try:
        # Extract the message content from the API response
        message_content = api_response['choices'][0]['message']['content']
        
        # Remove markdown code blocks if present
        import re
        message_content = re.sub(r'```json\n?', '', message_content)
        message_content = re.sub(r'```\n?', '', message_content)
        message_content = message_content.strip()
        
        # Parse JSON
        invoice_data = json.loads(message_content)
        
        # If it's a list of invoices, return as is. If single dict, wrap in list
        if isinstance(invoice_data, list):
            return invoice_data
        else:
            return [invoice_data]
        
    except (KeyError, json.JSONDecodeError, IndexError) as e:
        return [{
            "error": f"Failed to parse response: {str(e)}",
            "raw_response": str(api_response)
        }]


def process_invoice_image(image_path: str) -> List[Dict]:
    """
    Complete invoice extraction pipeline.
    
    Args:
        image_path: Path to the invoice image
        
    Returns:
        List of dictionaries with extracted invoice data
    """
    print(f"Processing invoice: {image_path}")
    
    try:
        # Call Vision API
        api_response = extract_invoice_data(image_path)
        
        # Parse the response
        invoices = parse_vision_response(api_response)
        
        if invoices and "error" not in invoices[0]:
            print(f"✓ Found {len(invoices)} invoice(s)")
            for invoice in invoices:
                print(f"  Invoice #: {invoice.get('invoice_number', 'N/A')}")
                print(f"  Customer: {invoice.get('customer_name', 'N/A')}")
                print(f"  Amount: {invoice.get('amount', 'N/A')}")
        
        return invoices
        
    except FileNotFoundError as e:
        print(f"✗ File error: {str(e)}")
        return [{"error": str(e)}]
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {str(e)}")
        return [{"error": "Unable to reach Vision API"}]
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return [{"error": str(e)}]


if __name__ == "__main__":
    # Test with sample image
    if os.path.exists("invoice_sample.png"):
        result = process_invoice_image("invoice_sample.png")
        print("\nExtracted Data:")
        print(json.dumps(result, indent=2))
    else:
        print("invoice_sample.png not found")
