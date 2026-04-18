import requests
import json

r = requests.get('http://localhost:8082/api/health', timeout=10)
data = r.json()
routes = data.get('api_routes', [])
print('Routes with stream or thinking:')
for route in routes:
    p = route.get('path', '')
    if 'stream' in p.lower() or 'thinking' in p.lower():
        print(f"  Route: {p}, Methods: {route.get('methods')}")




