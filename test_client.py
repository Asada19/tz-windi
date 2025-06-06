#!/usr/bin/env python3

import asyncio
import websockets
import json
import requests

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/v1/ws/chat"

async def test_websocket():
    login_data = {"username": "alice", "password": "password123"}
    response = requests.post(f"{BASE_URL}/api/v1/auth/login-json", json=login_data)
    
    if response.status_code != 200:
        print("Login failed")
        return
        
    token = response.json()["access_token"]
    print(f"Got token: {token[:20]}...")
    
    uri = f"{WS_URL}?token={token}"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        message = {
            "action": "send_message",
            "data": {
                "chat_id": 1,
                "text": "Test message from Python client",
                "client_message_id": "test-123"
            }
        }
        
        await websocket.send(json.dumps(message))
        print("Message sent")
        
        try:
            while True:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"Received: {data}")
        except asyncio.TimeoutError:
            print("No more messages")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 