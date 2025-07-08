from enum import Enum
import time
import os
import cv2
import numpy as np
import subprocess
import tempfile
# import src_sendAndReceive.sendFile as sendFile
import requests

def send_file_to_endpoint(endpoint: str, file_path: str, field_name: str = "file", extra_data: dict = None, headers: dict = None) -> requests.Response:
    """
    Sends a file to a specified HTTP endpoint using multipart/form-data.

    :param endpoint: The server's upload URL (e.g. "https://signcollect.nl/studioFilesServer/upload-mocap").
    :param file_path: Path to the file to be sent.
    :param field_name: The form field name expected by the server for file uploads.
    :param extra_data: Optional dict of additional form fields to include in the POST.
    :param headers: Optional dict of HTTP headers to include (e.g. authentication tokens).
    :return: The `requests.Response` object from the server.
    :raises: `requests.HTTPError` if the upload fails (non-2xx status code).
    """
    print(f"[OBS sender] Sending file '{file_path}' to endpoint '{endpoint}'...")
    # Verify the file exists
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"No such file: {file_path}")

    # Prepare extra form fields
    data = extra_data or {}
    
    # Open the file in binary mode and send it
    with open(file_path, "rb") as f:
        files = {
            field_name: (os.path.basename(file_path), f)
        }
        # Perform the POST
        resp = requests.post(endpoint, files=files, data=data, headers=headers)
    
    # Raise an exception for error codes (4xx, 5xx)
    resp.raise_for_status()
    return resp

class OBSStatus(Enum):
    NOT_CONNECTED = "Not connected to OBS"
    CONNECTED = "Connected to OBS"
    RECORDING_STARTED = "Recording started"
    RECORDING_STOPPED = "Recording stopped"
    ERROR = "Error"
    IDLE = "Idle"
    KILL = "Kill"
    SAVING = "Saving"

class OBSController:
    """
    Controls the OBS WebSocket connection and recording functionality.
    It also manages the storage of recorded files in a dynamic folder structure.
    To this end it uses 3 internal components:
    - ConnectionManager: Manages the connection to the OBS WebSocket server.
    - RecordingController: Controls the recording functionality in OBS.
    - FileManagementController: Manages the recorded files and their storage locations.
    """
    def __init__(self, host, port, password, popUp=None):
        print("[OBS] Initializing OBS Controller...")
        self.host = host
        self.port = port
        self.password = password
        self.popUp = popUp
        self.ws = None  # Initialize the client without parameters
        self.queued_operations = []
        self.last_upload_health = True, "Good"  # Health check for last upload

        # Internal components
        self.connection_manager = self.ConnectionManager(self)
        if self.connection_manager.check_connection():
            self.connection_manager.connect()
            self.recording_controller = self.RecordingController(self)
            self.file_manager = self.FileManagementController(self)
            self.statusCode = OBSStatus.IDLE
        else:
            self.recording_controller = None
            self.file_manager = None
            self.statusCode = OBSStatus.NOT_CONNECTED

    # Public Methods (Delegation)
    def check_connection(self):
        return self.connection_manager.check_connection()

    def connect(self):
        self.connection_manager.connect()
        self.statusCode = OBSStatus.CONNECTED

    def disconnect(self):
        self.connection_manager.disconnect()
        self.statusCode = OBSStatus.KILL

    def pop_all_queued_operations(self):
        while self.queued_operations:
            self.queued_operations.pop(0)()

    def start_recording(self):
        if self.statusCode != OBSStatus.IDLE:
            print("[OBS ERROR] OBS is not IDLE. Cannot start recording.")
            return

        if self.ws:
            self.recording_controller.start_recording()
        else:
            print("[OBS ERROR] Not connected to OBS WebSocket. Cannot start recording.")

    def stop_recording(self):
        if self.statusCode != OBSStatus.RECORDING_STARTED:
            print("[OBS ERROR] Recording is not active. Cannot stop recording.")
            return
        self.recording_controller.stop_recording()
        self.statusCode = OBSStatus.IDLE

    def set_record_directory(self, path):
        self.recording_controller.set_record_directory(path)

    def set_save_location(self, root_folder, vid_name="Recording"):
        if self.statusCode != OBSStatus.IDLE:
            print("[OBS ERROR] OBS is not IDLE. Queueing save location...")
            self.queued_operations.append(lambda: self.set_save_location(root_folder, vid_name))
            return False
        self.statusCode = OBSStatus.SAVING
        self.file_manager.set_save_location(root_folder, vid_name)
        self.statusCode = OBSStatus.IDLE
        print(f"[OBS] Save location set to: {self.file_manager.current_using_folder}!")
        return True

    def move_recorded_files(self, max_retries=6, delay=0.5):
        self.statusCode = OBSStatus.SAVING
        self.file_manager.move_recorded_files(max_retries, delay)
        self.statusCode = OBSStatus.IDLE
        if self.queued_operations:
            self.pop_all_queued_operations()

    def prepend_vid_name_last_recordings(self, vid_name=None, max_retries=6, delay=0.5):
        self.statusCode = OBSStatus.SAVING
        self.file_manager.prepend_vid_name_last_recordings(vid_name, max_retries, delay)
        self.statusCode = OBSStatus.IDLE
        if self.queued_operations:
            self.pop_all_queued_operations()
    
    def set_buffer_folder(self, path):
        self.file_manager.set_buffer_folder(path)
    
    def upload_last_recordings(self, endpoint, field_name="file", extra_data=None, headers=None):
        """
        Uploads the last recorded files to a specified HTTP endpoint using multipart/form-data.
        """
        if not self.file_manager.current_using_folder:
            error = "[OBS ERROR] No last used folder set for the recording. Cannot upload recordings."
            print(error)
            self.last_upload_health = False, error
            return False, error

        if not os.path.exists(self.file_manager.current_using_folder):
            error = f"[OBS ERROR] Last used folder '{self.file_manager.current_using_folder}' does not exist."
            print(error)
            self.last_upload_health = False, error
            return False, error

        print(f"[OBS] Uploading last recordings from '{self.file_manager.current_using_folder}' to '{endpoint}'...")
        for file in os.listdir(self.file_manager.current_using_folder):
            file_path = os.path.join(self.file_manager.current_using_folder, file)
            if os.path.isfile(file_path):
                print(send_file_to_endpoint(endpoint, file_path, field_name, extra_data, headers))

        print("[OBS] Upload completed.")
        self.last_upload_health = True, "Good"
        return True, "Good"

    # Internal Components
    class ConnectionManager:
        """Manages the connection to the OBS WebSocket server."""
        def __init__(self, parent):
            self.parent = parent

        def check_connection(self):
            import websocket
            try:
                ws = websocket.create_connection(f"ws://{self.parent.host}:{self.parent.port}")
                print("[OBS] Should be able to connect to OBS webserver!")
                ws.close()
                return True
            except Exception as e:
                print(f"[OBS ERROR] You cannot connect to the OBS webserver: {e}")
                return False

        def connect(self):
            import obsws_python as obs
            try:
                if self.parent.password:
                    self.parent.ws = obs.ReqClient(
                        host=self.parent.host, port=self.parent.port, password=self.parent.password
                    )
                else:
                    self.parent.ws = obs.ReqClient(host=self.parent.host, port=self.parent.port)
                print("[OBS] Connected to OBS WebSocket.")
            except Exception as e:
                print(f"[OBS ERROR] Failed to connect to OBS: {e}")

        def disconnect(self):
            if self.parent.ws:
                self.parent.ws.disconnect()
                print("[OBS] Disconnected from OBS WebSocket.")

    class RecordingController:
        """Controls the recording functionality in OBS."""
        def __init__(self, parent):
            self.parent = parent

        def set_record_directory(self, path):
            if not self.parent.ws:
                print("[OBS ERROR] WebSocket connection not established. Cannot set record directory.")
                return
            try:
                self.parent.ws.set_record_directory(path)
                print(f"[OBS] Recording directory set to: {path}")
            except Exception as e:
                print(f"[OBS ERROR] Failed to set recording directory in OBS: {e}")

        def start_recording(self):
            if self.parent.statusCode != OBSStatus.IDLE:
                print("[OBS ERROR] OBS is not IDLE. Cannot start recording.")
                return

            if not self.parent.ws:
                print("[OBS ERROR} WebSocket connection not established. Cannot start recording.")
                return
            try:
                self.parent.ws.start_record()
                print("[OBS] Started recording.")
                self.parent.statusCode = OBSStatus.RECORDING_STARTED
            except Exception as e:
                print(f"[OBS ERROR] Failed to start recording: {e}")

        def stop_recording(self):
            if self.parent.statusCode != OBSStatus.RECORDING_STARTED:
                print("[OBS ERROR] Recording is not active. Cannot stop recording.")
                return

            if not self.parent.ws:
                print("[OBS ERROR] WebSocket connection not established. Cannot stop recording.")
                return
            try:
                self.parent.ws.stop_record()
                print("[OBS] Stopped recording.")
                time.sleep(1)
                self.parent.file_manager.move_recorded_files()
                time.sleep(1)
                self.parent.file_manager.prepend_vid_name_last_recordings()
                self.parent.statusCode = OBSStatus.IDLE
                if self.parent.queued_operations:
                    self.parent.pop_all_queued_operations()
            except Exception as e:
                print(f"[OBS ERROR] Failed to stop recording: {e}")

    class FileManagementController:
        """Manages the recorded files and their storage locations."""
        def __init__(self, parent):
            self.parent = parent
            self.buffer_folder = r"D:\VideoCapture\SourceRecordBuffer"
            self.last_vid_name = None
            self.current_using_folder = None
            self.last_used_root_folder = None

            # vars for health check
            self.last_used_folder = None
            self.sessions_started = False
            self.health_check = True
            self.previous_values = {}        

        def set_buffer_folder(self, path):
            """Sets the location to store the recorded files temporarily."""
            import os

            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            self.buffer_folder = path
            print(f"[OBS] Buffer path set to: {self.buffer_folder}")

        def set_save_location(self, root_folder, vid_name="Recording"):
            """Sets the location to save the recorded files dynamically."""
            import os
            from datetime import datetime

            if root_folder == None:
                root_folder = self.last_used_root_folder

            if not os.path.exists(root_folder):
                create = self.parent.popUp.show_popup_yesno(
                    "Warning", f"The folder '{root_folder}' does not exist. Do you want to create it?"
                )
                if not create:
                    raise ValueError(f"[OBS ERROR] Root path '{root_folder}' does not exist.")
                else:
                    os.makedirs(root_folder, exist_ok=True)
            
            self.last_used_root_folder = root_folder
            self.last_vid_name = vid_name

            # Create a date folder under the root folder
            date_folder = os.path.join(root_folder, datetime.now().strftime("%Y-%m-%d"))
            os.makedirs(date_folder, exist_ok=True)

            # Create a subfolder for each recording session with incremental numbers
            session_folder_base = os.path.join(date_folder, vid_name)
            session_folder = self.get_incremental_folder(session_folder_base)

            os.makedirs(session_folder, exist_ok=True)

            # self.parent.recording_controller.set_record_directory(session_folder)
            self.last_used_folder = self.current_using_folder
            self.current_using_folder = session_folder
            print(f"[OBS] Save path set to: {self.current_using_folder}")

        def get_incremental_folder(self, base_path):
            """Finds the next available subfolder number in the given base path."""
            import os
            i = 1
            while os.path.exists(os.path.join(base_path, f"{i}")):
                i += 1
            return os.path.join(base_path, f"{i}")

        def move_recorded_files(self, max_retries=6, delay=0.5):
            """Move all files from the buffer to the last used folder."""
            import os
            import shutil
            import time

            if not self.current_using_folder:
                print("[OBS ERROR] No folder set for the recording. Can't move the files.")
                return

            self.sessions_started = True

            try:
                for filename in os.listdir(self.buffer_folder):
                    file_path = os.path.join(self.buffer_folder, filename)
                    if os.path.isfile(file_path):
                        destination = os.path.join(self.current_using_folder, filename)
                        retries = 0
                        while retries < max_retries:
                            try:
                                shutil.move(file_path, destination)
                                print(f"[OBS] Moved {filename} to {self.current_using_folder}")
                                break
                            except PermissionError as e:
                                print(f"[OBS ERROR] Error moving {filename}: {e}. Retrying in {delay} seconds...")
                                retries += 1
                                time.sleep(delay)
                                if retries == max_retries:
                                    print(f"[OBS ERROR] Failed to move {filename} after {max_retries} retries.")
            except Exception as e:
                print(f"[OBS ERROR] Failed to move the files: {e}")

        def check_last_used_folder(self):
            """Check if the last used folder exists. Check if it contains any files. Check if the files are not just black screens. On success return True, else return False."""
            # Check if a recording session has been started
            if not self.sessions_started:
                print("[OBS ERROR] No recording session has been started yet. Can't check the last used folder.")
                return True, "Good"

            # Check if values have changed since last health check
            # if self.previous_values == {
            #     "last_used_folder": self.last_used_folder,
            #     "current_using_folder": self.current_using_folder,
            #     "last_vid_name": self.last_vid_name,
            # }:
            #     print("[OBS] No changes detected since last health check. Skipping checks.")
            #     return self.health_check

            self.health_check = False

            # Check presence of current_using_folder and its contents
            if not self.last_used_folder:
                error = "[OBS ERROR] No last used folder set for the recording. Can't check the last used folder."
                return False, error

            # Check if the last used folder exists
            if not os.path.exists(self.last_used_folder):
                error = f"[OBS ERROR] Last used folder '{self.last_used_folder}' does not exist."
                print(error)
                return False, error

            # Check if the last used folder contains any files
            files = os.listdir(self.last_used_folder)
            if not files:
                error = f"[OBS ERROR] Last used folder '{self.last_used_folder}' is empty."
                return False, error

            # Check if the files are not just black screens
            for file in files:
                file_path = os.path.join(self.last_used_folder, file)
                if not os.path.isfile(file_path):
                    continue
                
                # Check if the first frame is the same as the last frame
                if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    if self.is_first_last_same(file_path):
                        error = f"[OBS ERROR] Video '{file}' has the same first and last frame."
                        print(error)
                        return False, error

            self.previous_values = {
                "last_used_folder": self.last_used_folder,
                "current_using_folder": self.current_using_folder,
                "last_vid_name": self.last_vid_name
            }
            self.health_check = True
            print(f"[OBS] Last used folder is valid and contains valid files: {self.last_used_folder}")
            return True, "Good"

        def ffmpeg_extract_frame(self, video_path, time_sec, tmp_png_path):
            """
            Extract a single frame at `time_sec`:
            - if time_sec >= 0: number of seconds from the start
            - if time_sec <  0: number of seconds from the end (using -sseof)
            """
            # Build seek arguments
            if time_sec >= 0:
                seek_args = ["-ss", str(time_sec)]
            else:
                # -sseof is a global option: seek from end-of-file
                seek_args = ["-sseof", str(time_sec)]
            
            cmd = (
                ["ffmpeg", "-y"]
                + seek_args
                + ["-i", video_path,
                "-frames:v", "1",
                "-q:v", "2",        # pretty good quality
                tmp_png_path]
            )
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        def is_first_last_same(self, video_path, diff_thresh=1e-6):
            # Create two temp PNG paths
            fd1, png1 = tempfile.mkstemp(suffix=".png"); os.close(fd1)
            fd2, png2 = tempfile.mkstemp(suffix=".png"); os.close(fd2)

            try:
                # 1) Grab exactly the first frame
                self.ffmpeg_extract_frame(video_path, 0.0, png1)
                # 2) Grab exactly the last frame (0.1s from the end)
                self.ffmpeg_extract_frame(video_path, -0.1, png2)

                # Load & convert to grayscale
                g1 = cv2.cvtColor(cv2.imread(png1), cv2.COLOR_BGR2GRAY)
                g2 = cv2.cvtColor(cv2.imread(png2), cv2.COLOR_BGR2GRAY)

                # Compute normalized MSE
                mse = np.mean((g1.astype("float32") - g2.astype("float32")) ** 2)
                norm_mse = mse / (255.0**2)
                return norm_mse < diff_thresh

            finally:
                os.remove(png1)
                os.remove(png2)

        def prepend_vid_name_last_recordings(self, vid_name=None, max_retries=6, delay=0.5):
            """Prepend the gloss name to the last recorded files."""
            import os
            import time

            if not self.current_using_folder:
                print("[OBS ERROR] No folder set for the recording. Can't prepend the gloss name.")
                return

            if not vid_name:
                vid_name = self.last_vid_name

            try:
                for filename in os.listdir(self.current_using_folder):
                    file_path = os.path.join(self.current_using_folder, filename)
                    if os.path.isfile(file_path):
                        new_filename = f"{vid_name}_{filename}"
                        retries = 0
                        while retries < max_retries:
                            try:
                                os.rename(file_path, os.path.join(self.current_using_folder, new_filename))
                                print(f"[OBS] Renamed {filename} to {new_filename}")
                                break
                            except PermissionError as e:
                                print(f"[OBS ERROR] Error renaming {filename}: {e}. Retrying in {delay} seconds...")
                                retries += 1
                                time.sleep(delay)
                                if retries == max_retries:
                                    print(f"[OBS ERROR] Failed to rename {filename} after {max_retries} retries.")
            except Exception as e:
                print(f"[OBS ERROR] Failed to rename the files: {e}")
