import asyncio
import websockets

async def test_ws():
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws/chat") as ws:
            print("Connected to /ws/chat")
            await ws.send("test")
            print("Sent test message")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_ws())
