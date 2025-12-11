
import sys
import os
import json
import base64
import tempfile

# Add root directory to path to allow importing local modules
current_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

try:
    from pipeline import InvoiceProcessingPipeline
except ImportError:
    # Fallback for local testing or if path is different
    sys.path.append(os.path.join(os.getcwd()))
    try:
        from pipeline import InvoiceProcessingPipeline
    except ImportError:
        pass 

def handler(event, context):
    print("Received event")
    
    # Handle CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    if event.get('httpMethod') != 'POST':
        return {
            'statusCode': 405, 
            'headers': headers,
            'body': 'Method Not Allowed'
        }

    try:
        body = json.loads(event.get('body', '{}'))
        image_data = body.get('image') # base64 string
        filename = body.get('filename', 'invoice.png')

        if not image_data:
            return {
                'statusCode': 400, 
                'headers': headers,
                'body': json.dumps({'error': 'No image data provided'})
            }

        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Created temp dir: {temp_dir}")
            
            # Save the image content to a file
            file_path = os.path.join(temp_dir, filename)
            
            # Remove data URL header if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Ensure proper padding for base64
            missing_padding = len(image_data) % 4
            if missing_padding:
                image_data += '=' * (4 - missing_padding)
                
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_data))
                
            print(f"Saved file to {file_path}")

            # Initialize pipeline with the temp directory as output
            pipeline = InvoiceProcessingPipeline(output_dir=os.path.join(temp_dir, "output"))
            
            # Process the invoice
            result = pipeline.process_single_invoice(file_path)
            
            print("Processing complete")

            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500, 
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'trace': traceback.format_exc()
            })
        }

if __name__ == "__main__":
    # Local Test
    print("Running local test...")
    sample_img = os.path.join(root_dir, "invoice_sample.png")
    if os.path.exists(sample_img):
        with open(sample_img, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        
        event = {
            "httpMethod": "POST",
            "body": json.dumps({
                "image": b64_data,
                "filename": "test_invoice.png"
            })
        }
        
        response = handler(event, None)
        print("\nResponse Status:", response['statusCode'])
        print("Response Body Snippet:", response['body'][:200])
    else:
        print("invoice_sample.png not found for testing")
