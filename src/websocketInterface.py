import asyncio
import sys
import time
import websockets
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from obsRecording import OBSController
from src_sendAndReceive.sendFile import send_file

class OBSWebSocketInterface:
    def __init__(self, host, port, obs_host, obs_port, obs_password, save_folder, buffer_folder):
        self.server_host = host
        self.server_port = port
        self.save_folder = save_folder
        self.obs_controller = OBSController(obs_host, obs_port, obs_password)
        self.obs_controller.set_buffer_folder(buffer_folder)
        self.obs_controller.set_save_location(save_folder)
        self.server = None  # Store server reference
        self.stop_event = asyncio.Event()  # Event to signal shutdown

    async def handler(self, websocket):
        async for message in websocket:
            if message == "Start":
                print("[WebSocket] Received 'Start' message.")
                self.obs_controller.start_recording()
            elif message == "Stop":
                print("[WebSocket] Received 'Stop' message.")
                self.obs_controller.stop_recording()
            elif message == "Kill":
                print("[WebSocket] Received 'Kill' message.")
                self.obs_controller.disconnect()
                await asyncio.sleep(2)  # Avoid blocking
                await websocket.close()
                self.stop_event.set()  # Signal shutdown
                return
            elif message.startswith("SetName"):
                print(f"[WebSocket] Received 'SetName' message: {message}")
                self.obs_controller.set_save_location(self.save_folder, message.lstrip("SetName "))
            elif message.startswith("SendFilePrevious"):
                print(f"[WebSocket] Received 'SendFilePrevious' message: {message}")
                host, port = message.split(" ")[1], int(message.split(" ")[2])
                last_folder = self.obs_controller.file_manager.last_used_folder
                if last_folder is None:
                    print("[WebSocket] No previous folder found.")
                elif not os.path.exists(last_folder):
                    print(f"[WebSocket] Previous folder '{last_folder}' does not exist.")
                elif host is None or port is None:
                    print("[WebSocket] Invalid host or port.")
                else:
                    for file in os.listdir(last_folder):
                        send_file(host, port, os.path.join(last_folder, file))
            else:
                print(f"[WebSocket] Received unknown message: {message}")

    async def start_server_async(self):
        print(f"[WebSocket] Starting server on {self.server_host}:{self.server_port}")
        self.server = await websockets.serve(self.handler, self.server_host, self.server_port)
        await self.stop_event.wait()  # ✅ Wait until "Kill" is received
        await self.shutdown_server()

    async def shutdown_server(self):
        print("[WebSocket] Shutting down server...")
        self.server.close()
        await self.server.wait_closed()
        print("[WebSocket] Server stopped.")

    def start_server(self):
        asyncio.run(self.start_server_async())

# Example usage
if __name__ == "__main__":
    ws_interface = OBSWebSocketInterface('localhost', 8765, 'localhost', 4457, None)
    ws_interface.start_server()