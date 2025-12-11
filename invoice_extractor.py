import base64
import requests
import json
import os
from typing import Dict, List, Optional, Union

API_KEY = "sGnexJYRzOzcMH3x2Rzg9CusBH11poeO"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
# User requested specific model
MODEL = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"


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
        "text": """Analyze the invoice image(s).
        
        CRITICAL INSTRUCTIONS:
        1. **Batch Mode**: If the images contain MULTIPLE DISTINCT invoices, return a JSON LIST of invoice objects (e.g., `[ {inv1}, {inv2} ]`).
        2. **Multi-Page Mode**: If the images are pages of the SAME invoice, combine them into a SINGLE invoice object.
        3. **Extraction Order**: 
           - FIRST: Locate the Invoice Number, Date, and Customer Name.
           - SECOND: Locate the Total Amount and Tax Totals (IGST/CGST/SGST).
           - THIRD: Extract the line items (Quantity, Rate, UOM, HSN).
        
        REQUIRED JSON STRUCTURE (for each invoice):
        {
            "invoice_number": "String (Required - Look for 'Invoice No', 'Bill No', 'Voucher No')",
            "invoice_date": "String (DD-MM-YYYY)",
            "customer_name": "String",
            "total_amount": Number (No commas, e.g. 1250.00),
            "currency": "String",
            "igst_amount": Number (No commas, default 0.00),
            "cgst_amount": Number (No commas, default 0.00),
            "sgst_amount": Number (No commas, default 0.00),
            "items": [
                {
                    "item_name": "String",
                    "quantity": Number (default 1),
                    "uom": "String (e.g. Nos, Kgs, Pcs, Box)",
                    "rate": Number (No commas),
                    "amount": Number (No commas),
                    "hsn_code": "String"
                }
            ]
        }
        
        RULES:
        - Return ONLY valid JSON.
        - Do NOT use commas in numeric values.
        - If a field is missing, use null or 0.00.
        - **IMPORTANT**: Do NOT just return a list of items. You MUST wrap them in the 'items' field of the invoice object.
        """
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
        
        # Helper to parse string with sanitization
        def try_parse(json_str):
            # SANITIZATION: Remove commas from numbers
            # Look for digit comma digit pattern and remove the comma
            # e.g. 74,900.00 -> 74900.00
            clean_str = re.sub(r'(\d),(\d)', r'\1\2', json_str)
            return json.loads(clean_str)

        import re
        import json

        # Strategy 1: Look for a generic JSON list [...]
        list_match = re.search(r'\[.*\]', message_content, re.DOTALL)
        if list_match:
            try:
                data = try_parse(list_match.group(0))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass # Fall through to other strategies

        # Strategy 2: Look for a generic JSON object {...} (or sequence of objects)
        # Note: This greedy match captures {obj1}, {obj2}
        obj_match = re.search(r'\{.*\}', message_content, re.DOTALL)
        if obj_match:
            json_candidate = obj_match.group(0)
            
            # Attempt 1: Direct Parse (Single Object)
            try:
                data = try_parse(json_candidate)
                if isinstance(data, list): return data
                return [data]
            except json.JSONDecodeError:
                pass

            # Attempt 2: It might be multiple objects like {A}, {B}. Try wrapping in [...]
            try:
                wrapped_candidate = f"[{json_candidate}]"
                data = try_parse(wrapped_candidate)
                if isinstance(data, list): return data
                return [data]
            except json.JSONDecodeError:
                pass
                
            # Attempt 3: Sometimes models forget commas between objects: {A}{B} -> {A},{B}
            # This is complex, but basic wrap is usually enough for "comma separated" failure.
            
            return [{"error": "Found JSON-like block but failed to parse (tried wrapping)", "content": json_candidate}]

        return [{"error": "No JSON structure found", "content": message_content}]
        
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
