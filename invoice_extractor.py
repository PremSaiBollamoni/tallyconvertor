import base64
import requests
import json
import os
from typing import Dict, List, Optional, Union

API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
# Use a valid, standard Vision model
MODEL = "meta-llama/Llama-3.2-11B-Vision-Instruct"


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_invoice_data(image_paths: List[str]) -> Dict:
    """
    Extract invoice data from one or multiple images (multi-page invoice) using the Vision API.
    
    Args:
        image_paths: List of paths to the invoice images (pages)
        
    Returns:
        Dictionary with extracted invoice data
    """
    
    content_list = []
    
    # 1. Add all images
    for path in image_paths:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image file not found: {path}")
        
        image_base64 = encode_image(path)
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{image_base64}"
            }
        })
    
    # 2. Add the extraction prompt
    content_list.append({
        "type": "text",
        "text": """Extract the following invoice information and return as JSON.
        If the invoice spans multiple pages, combine the data into a single invoice record.
        
        Fields required:
        - invoice_number
        - invoice_date (DD-MM-YYYY format)
        - customer_name
        - total_amount
        - currency
        - igst_amount (Total Integrated Tax)
        - cgst_amount (Total Central Tax)
        - sgst_amount (Total State Tax)
        - items: List of items, each containing:
            - item_name
            - quantity (number)
            - uom (Unit of Measurement e.g., Nos, Kgs, Box)
            - rate (unit price)
            - amount (line total)
            - hsn_code (if available)

        JSON Structure:
        {
            "invoice_number": "...",
            "invoice_date": "...",
            "customer_name": "...",
            "total_amount": 0.0,
            "igst_amount": 0.0,
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "items": [
                {
                    "item_name": "...",
                    "quantity": 0,
                    "uom": "...",
                    "rate": 0.0,
                    "amount": 0.0,
                    "hsn_code": "..."
                }
            ]
        }
        
        Only return valid JSON, no additional text."""
    })

    payload = {
        "model": MODEL,
        "max_tokens": 4092,
        "messages": [
            {
                "role": "user",
                "content": content_list
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Increased timeout significantly for image uploads
    response = requests.post(
        DEEPINFRA_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=120 
    )
    
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    return response.json()


def parse_vision_response(api_response: Dict) -> List[Dict]:
    """
    Parse the Vision API response and extract structured invoice data.
    """
    try:
        # Extract the message content from the API response
        if 'choices' not in api_response or not api_response['choices']:
             return [{"error": "Empty response from AI model", "raw": api_response}]
             
        message_content = api_response['choices'][0]['message']['content']
        
        # Robust JSON extraction: Find the first '{' and the last '}'
        import re
        
        # Try to find a JSON block specifically
        json_match = re.search(r'\{.*\}', message_content, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                invoice_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback: Validation logic or cleanup if stricter parsing needed
                return [{"error": "Found JSON-like block but failed to parse", "content": json_str}]
        else:
             return [{"error": "No JSON object found in response", "content": message_content}]
        
        # If it's a list of invoices, return as is. If single dict, wrap in list
        if isinstance(invoice_data, list):
            return invoice_data
        else:
            return [invoice_data]
        
    except (KeyError, IndexError) as e:
        return [{
            "error": f"Failed to parse response structure: {str(e)}",
            "raw_response": str(api_response)
        }]


def process_invoice_image(image_input: Union[str, List[str]]) -> List[Dict]:
    """
    Complete invoice extraction pipeline.
    
    Args:
        image_input: Path to the invoice image OR List of paths (multi-page)
        
    Returns:
        List of dictionaries with extracted invoice data
    """
    # Normalize input to list
    if isinstance(image_input, str):
        image_paths = [image_input]
    else:
        image_paths = image_input

    print(f"Processing invoice pages: {image_paths}")
    
    try:
        # Call Vision API
        api_response = extract_invoice_data(image_paths)
        
        # Parse the response
        invoices = parse_vision_response(api_response)
        
        if invoices and "error" not in invoices[0]:
            print(f"✓ Found {len(invoices)} invoice(s)")
            for invoice in invoices:
                print(f"  Invoice #: {invoice.get('invoice_number', 'N/A')}")
                print(f"  Customer: {invoice.get('customer_name', 'N/A')}")
                print(f"  Total: {invoice.get('total_amount', 'N/A')}")
        
        return invoices
        
    except FileNotFoundError as e:
        print(f"✗ File error: {str(e)}")
        return [{"error": str(e)}]
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection failed to DeepInfra: {str(e)}"
        print(f"✗ {error_msg}")
        return [{"error": error_msg}]
    except Exception as e:
        error_msg = f"Processing Error: {str(e)}"
        print(f"✗ {error_msg}")
        return [{"error": error_msg}]


if __name__ == "__main__":
    # Test with sample image
    if os.path.exists("invoice_sample.png"):
        result = process_invoice_image("invoice_sample.png")
        print("\nExtracted Data:")
        print(json.dumps(result, indent=2))
    else:
        print("invoice_sample.png not found")
