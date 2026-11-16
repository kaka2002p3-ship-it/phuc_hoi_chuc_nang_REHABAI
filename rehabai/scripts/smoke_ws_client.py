import asyncio
import websockets
import json
import base64
import os
import numpy as np
import cv2

# This is a manually launched end-to-end smoke client; it requires a live
# backend and is not a pytest unit test.  Keep pytest from collecting the async
# helper while preserving ``python scripts/smoke_ws_client.py`` as the entry point.
__test__ = False

async def test_ws():
    token = os.environ.get("REHABAI_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("Set REHABAI_ACCESS_TOKEN to a valid login token before running this smoke client")
    uri = os.environ.get("REHABAI_WS_URL", "ws://localhost:8000/ws/inference")
    uri = f"{uri}{'&' if '?' in uri else '?'}token={token}"
    
    # Tạo một ảnh dummy 224x224 RGB
    dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
    # Encode as JPEG base64
    _, buffer = cv2.imencode('.jpg', dummy_img)
    b64_str = base64.b64encode(buffer).decode('utf-8')
    
    async with websockets.connect(uri) as websocket:
        print("Connected to WS!")
        
        # Gửi 100 frame để trigger 1 lần inference (buffer = 96)
        for i in range(100):
            payload = {
                "timestamp": i * 33, # 30 fps
                "session_id": "test-123",
                "frame": b64_str
            }
            await websocket.send(json.dumps(payload))
            
            # Chỉ chờ response thỉnh thoảng hoặc cuối cùng
            response = await websocket.recv()
            resp_data = json.loads(response)
            
            if "inference" in resp_data:
                print(f"Frame {i}: Got inference!")
                # JSON escaping keeps this manual smoke test usable in Windows
                # terminals whose active code page cannot print Vietnamese.
                print(json.dumps(resp_data["inference"], ensure_ascii=True))
                break
        
        print("Test WS completed.")

if __name__ == "__main__":
    asyncio.run(test_ws())
