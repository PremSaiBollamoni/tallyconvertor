
import sys
import os
import json
import base64
import tempfile

# Force current directory into sys.path to ensure imports work
# This is required because Netlify/Lambda might not have the function dir in path by default
# when running the handler.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Now standard imports will find the sibling files
try:
    from pipeline import InvoiceProcessingPipeline
except ImportError as e:
    print(f"CRITICAL: Could not import pipeline. Sys.path is: {sys.path}")
    print(f"Error: {e}")
    # We don't raise here to allow the handler to return a 500 JSON instead of crashing the process
    InvoiceProcessingPipeline = None

def handler(event, context):
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    # Early check for import failure
    if InvoiceProcessingPipeline is None:
        return {
            'statusCode': 500,
            'headers': headers, 
            'body': json.dumps({'error': 'Backend configuration error: Import failed'})
        }

    if event.get('httpMethod') != 'POST':
        return {'statusCode': 405, 'headers': headers, 'body': 'Method Not Allowed'}

    try:
        body = json.loads(event.get('body', '{}'))
        image_data = body.get('image')
        filename = body.get('filename', 'invoice.png')

        if not image_data:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No image data provided'})}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, filename)
            
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            missing_padding = len(image_data) % 4
            if missing_padding:
                image_data += '=' * (4 - missing_padding)
                
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_data))
                
            pipeline = InvoiceProcessingPipeline(output_dir=os.path.join(temp_dir, "output"))
            result = pipeline.process_single_invoice(file_path)
            
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
