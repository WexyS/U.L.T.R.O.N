
import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/chat"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send a ping or message
            payload = {
                "message": "Hello Ultron, respond briefly.",
                "mode": "chat",
                "conversation_id": None,
                "history": []
            }
            await websocket.send(json.dumps(payload))
            print("Message sent.")
            
            # Wait for response
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    data = json.loads(response)
                    print(f"Received: {data['type']}")
                    if data['type'] == 'token':
                        print(f"Content: {data['content']}")
                    if data['type'] == 'complete':
                        print("Chat completed successfully.")
                        break
                    if data['type'] == 'error':
                        print(f"Error from server: {data['content']}")
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response.")
                    break
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
