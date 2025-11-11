import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import urllib.parse

# Load mock data
with open('mock_data.json', 'r') as f:
    mock_data = json.load(f)

def get_recommendation(county, farm_type, soil_type=None):
    county = county.title()
    region_data = mock_data['regions'].get(county, {
        "soil": "loamy",
        "weather": "mild", 
        "crop_recommendation": "maize",
        "livestock_recommendation": "chicken"
    })
    
    if farm_type.lower() == "crop":
        recommendation = region_data["crop_recommendation"]
    else:
        recommendation = region_data["livestock_recommendation"]
    
    advice = f"For {county} with {region_data['soil']} soil and {region_data['weather']} weather, {recommendation} is recommended."
    
    return {
        "county": county,
        "soil": soil_type or region_data["soil"],
        "farm_type": farm_type,
        "recommendation": recommendation,
        "advice": advice
    }

class USSDHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ussd':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = parse_qs(post_data)
            
            text = data.get('text', [''])[0]
            
            if text == "":
                response = "CON Welcome to Agritech AI\\n1. Crop Recommendation\\n2. Livestock Recommendation"
            elif text in ["1", "2"]:
                response = "CON Enter your county (e.g., Makueni):"
            elif "*" in text:
                parts = text.split("*")
                if len(parts) == 2:
                    response = "CON Enter soil type (sandy/loamy/clay) or 'auto':"
                elif len(parts) >= 3:
                    option = parts[0]
                    county = parts[1]
                    soil = parts[2] if parts[2] != 'auto' else None
                    farm_type = "crop" if option == "1" else "livestock"
                    
                    result = get_recommendation(county, farm_type, soil)
                    response = f"END Recommended: {result['recommendation']}\\n{result['advice'][:80]}..."
                else:
                    response = "END Invalid input. Try again."
            else:
                response = "END Invalid option. Try again."
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(response.encode())
        
        elif self.path == '/recommend':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            result = get_recommendation(
                data['county'], 
                data['farm_type'], 
                data.get('soil_type')
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 8000), USSDHandler)
    print("Server running on http://0.0.0.0:8000")
    server.serve_forever()