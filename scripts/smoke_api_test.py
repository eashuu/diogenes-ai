import sys
import os
from fastapi.testclient import TestClient

# Ensure project root is on sys.path so `src` package is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

from src.api.app import app

client = TestClient(app)

print('GET /')
r = client.get('/')
print(r.status_code)
print(r.json())

print('\nGET /health')
r = client.get('/health')
print(r.status_code)
print(r.json())

print('\nGET /health/live')
r = client.get('/health/live')
print(r.status_code)
print(r.json())

print('\nGET /health/ready')
r = client.get('/health/ready')
print(r.status_code)
print(r.json())
