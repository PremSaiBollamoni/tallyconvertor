
import http.server
import socketserver
import json
import os
import sys
import base64

# Ensure simple imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the actual function handler
try:
    from functions import process_invoice
except ImportError:
    # Handle if run from different dir
    sys.path.append(os.path.join(os.getcwd(), 'functions'))
    import process_invoice

PORT = 8000

class LocalNetlifyHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/.netlify/functions/process_invoice':
            content_len = int(self.headers.get('Content-Length'))
            post_body = self.rfile.read(content_len).decode('utf-8')
            
            # Mock Netlify Event
            event = {
                'httpMethod': 'POST',
                'body': post_body,
                'headers': {k: v for k, v in self.headers.items()}
            }
            
            # Call the handler
            try:
                response = process_invoice.handler(event, None)
                
                self.send_response(response['statusCode'])
                self.send_header('Content-type', 'application/json')
                
                # Add CORS headers for good measure (though strict local origin usually fine)
                self.send_header('Access-Control-Allow-Origin', '*')
                
                self.end_headers()
                self.wfile.write(response['body'].encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Function not found")

    def do_GET(self):
        # Serve index.html for root path
        if self.path == '/':
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

print(f"Starting local testing server at http://localhost:{PORT}")
print("Use Ctrl+C to stop")

with socketserver.TCPServer(("", PORT), LocalNetlifyHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
