# Recording with Optical Cameras through OBS
The OBS portion of the program allows us to record with optical cameras through OBS. This section goes over prerequisites and steps to properly setup OBS.

## Prerequisites
- **OBS Version**: 26.0 or higher
- **OBS Source Record Plugin**: [Download here](https://obsproject.com/forum/resources/source-record.1285/)

## Setup Instructions

### Step 1: Enable WebSocket Server in OBS
1. Open OBS.
2. Under tools, **WebSocket Server Settings** section.
3. Enable the WebSocket server and note the following:
   - **Host** (default: `localhost`)
   - **Port** (default: `4444`)
   - **Password** (if required).


### Step 2: Configure OBS Scenes and Cameras
1. **Create Scenes**:
   - Add a scene for each camera you want to record.
2. **Add Cameras**:
   - For each scene, add the corresponding camera as a source.
3. **Configure Source Record Plugin**:
   - For all cameras **except the main camera**:
     1. Go to the scene.
     2. Right click on the scene, and click filters.
     3. Add a **Source Record** filter to the camera source.
     4. Set the **Record Mode** to `Recording`.
     5. Specify the path to a `buffer_folder` (default: `D:/VideoCapture/SourceRecordBuffer`).
     6. Modify the default file name to ensure it doesn’t collide with other cameras' recordings.
     7. (Optional) If you want file splitting based on recording time or size, you can set this here.
     8. (Optional) Look at the bitrate, the default is low.


### Step 3: Select the Main Camera
- During a recording session, ensure the **main camera scene** is selected in OBS. 
  - This camera will record directly through OBS.
  - Other cameras will record via the Source Record plugin.
  - (Optional) In the advanced output settings, under record, you can set automatic file splitting if needed.


### Step 4: Update the Configuration File
In your `config.yaml`, set the following parameters:
- `obs_host`: Host address of the OBS WebSocket server.
- `obs_port`: Port for the OBS WebSocket server.
- `buffer_folder`: Path to the folder used by the Source Record plugin for buffer recordings.
- `save_folder`: Path to the folder where final recordings will be saved.


## Recording Workflow

### Python Commands
Once the setup is complete, you can control the recording via Python using the following commands:

```python
# Initialize OBS Controller
obs = obsRecording.OBSController(args.obs_host, args.obs_port, args.obs_password, popUp=popUp.PopUp())

# Set Save Location
obs.set_save_location(args.obs_save_folder, vid_name="testName")

# Set Buffer Folder location (should match the filter location of the Source Record plugin)
obs.set_buffer_folder(args.obs_buffer_folder)

# Start Recording
obs.start_recording()

# Stop Recording
obs.stop_recording()
```

## WebSocket interface
This project provides a Python-based interface for controlling OBS through WebSockets.

### Host
The WebSocket server is implemented in the OBSWebSocketInterface class. It listens for WebSocket messages and executes commands accordingly.
Attributes:
- server_host (str): The host address for the WebSocket server.
- server_port (int): The port number for the WebSocket server.
- save_folder (str): The folder where recordings will be saved.
- obs_controller (OBSController): An instance of OBSController to manage OBS.
- server (websockets.server): The WebSocket server instance.
- stop_event (asyncio.Event): An event used to signal server shutdown.

Methods:
- handler(websocket): Handles incoming WebSocket messages and processes commands.
- start_server_async(): Starts the WebSocket server asynchronously and listens for the "Kill" message to shut down the server.
- shutdown_server(): Shuts down the WebSocket server.
- start_server(): Starts the WebSocket server and runs it until shutdown.

Example starting server:
```python
obs_ws = OBSWebSocketInterface(server_host='localhost', server_port=8765, save_folder='/path/to/save')
obs_ws.start_server()
```

### Client
A WebSocket client is responsible for sending commands to the server. The client can initiate recording, stop recording, and request previous recorded files.
Example sender (receiver_main):
```python
async def receiver_main(args):
    from src.src_sendAndReceive.receiveFiles import AsyncFileReceiver, run_receiver_in_new_terminal
    import websockets

    async def send_message(message):
        uri = f"ws://{args.target_host}:{args.target_port}"
        async with websockets.connect(uri) as websocket:
            await websocket.send(message)
            print(f"Sent message: {message}")

    # Launch the file receiver in a new terminal
    run_receiver_in_new_terminal(args.receiver_host, args.receiver_port, args.save_folder, args.receiver_script_path, args.python_path)

    # Send commands to control OBS
    await send_message("SetName TEST6")
    await send_message("Start")
    await asyncio.sleep(4)
    await send_message("Stop")
    await send_message(f"SendFilePrevious {args.receiver_host} {args.receiver_port}")
```

Running the client:
To send commands to the WebSocket server, run the sender script with appropriate arguments.
```python
import asyncio
args = Namespace(target_host='localhost', target_port=8765, receiver_host='remote_host', receiver_port=9000, save_folder='/path/to/save', receiver_script_path='/path/to/script.py', python_path='python3')
asyncio.run(receiver_main(args))
```
