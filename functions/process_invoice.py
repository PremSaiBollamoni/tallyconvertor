
import sys
import os
import json
import base64
import tempfile

# Files are now local in the same directory (self-contained function)
try:
    from pipeline import InvoiceProcessingPipeline
except ImportError:
    # Fallback/Debug
    print("Could not import pipeline from local directory")
    raise

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
