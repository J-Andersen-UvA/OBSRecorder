# Recording with Optical Cameras through OBS
The OBS portion of the program allows us to record with optical cameras through OBS. This section goes over prerequisites and steps to properly setup OBS.

## Prerequisites
- **OBS Version**: 26.0 or higher
- **OBS Source Record Plugin**: [Download here](https://obsproject.com/forum/resources/source-record.1285/)

## Setup Instructions

### Step 1: Enable WebSocket Server in OBS
1. Open OBS settings.
2. Go to the **WebSocket Server Settings** section (requires OBS WebSocket plugin).
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
     2. Add a **Source Record** filter to the camera source.
     3. Set the **Record Mode** to `Recording`.
     4. Specify the path to a `buffer_folder` (default: `D:/VideoCapture/SourceRecordBuffer`).
     5. Modify the default file name to ensure it doesn’t collide with other cameras' recordings.
     6. (Optional) If you want file splitting based on recording time or size, you can set this here.


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

