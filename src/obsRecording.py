from enum import Enum
import time

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
        print(f"[OBS] Save location set!")
        return True

    def move_recorded_files(self, max_retries=6, delay=0.5):
        self.statusCode = OBSStatus.SAVING
        self.file_manager.move_recorded_files(max_retries, delay)
        self.statusCode = OBSStatus.IDLE
        if self.queued_operations:
            self.queued_operations.pop(0)()

    def prepend_vid_name_last_recordings(self, vid_name=None, max_retries=6, delay=0.5):
        self.statusCode = OBSStatus.SAVING
        self.file_manager.prepend_vid_name_last_recordings(vid_name, max_retries, delay)
        self.statusCode = OBSStatus.IDLE
        if self.queued_operations:
            self.queued_operations.pop(0)()
    
    def set_buffer_folder(self, path):
        self.file_manager.set_buffer_folder(path)

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
                    self.parent.queued_operations.pop(0)()
            except Exception as e:
                print(f"[OBS ERROR] Failed to stop recording: {e}")

    class FileManagementController:
        """Manages the recorded files and their storage locations."""
        def __init__(self, parent):
            self.parent = parent
            self.buffer_folder = r"D:\VideoCapture\SourceRecordBuffer"
            self.last_vid_name = None
            self.last_used_folder = None
            self.last_used_root_folder = None

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
            self.last_used_folder = session_folder
            print(f"[OBS] Save path set to: {self.last_used_folder}")

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

            if not self.last_used_folder:
                print("[OBS ERROR] No folder set for the recording. Can't move the files.")
                return

            try:
                for filename in os.listdir(self.buffer_folder):
                    file_path = os.path.join(self.buffer_folder, filename)
                    if os.path.isfile(file_path):
                        destination = os.path.join(self.last_used_folder, filename)
                        retries = 0
                        while retries < max_retries:
                            try:
                                shutil.move(file_path, destination)
                                print(f"[OBS] Moved {filename} to {self.last_used_folder}")
                                break
                            except PermissionError as e:
                                print(f"[OBS ERROR] Error moving {filename}: {e}. Retrying in {delay} seconds...")
                                retries += 1
                                time.sleep(delay)
                                if retries == max_retries:
                                    print(f"[OBS ERROR] Failed to move {filename} after {max_retries} retries.")
            except Exception as e:
                print(f"[OBS ERROR] Failed to move the files: {e}")

        def prepend_vid_name_last_recordings(self, vid_name=None, max_retries=6, delay=0.5):
            """Prepend the gloss name to the last recorded files."""
            import os
            import time

            if not self.last_used_folder:
                print("[OBS ERROR] No folder set for the recording. Can't prepend the gloss name.")
                return

            if not vid_name:
                vid_name = self.last_vid_name

            try:
                for filename in os.listdir(self.last_used_folder):
                    file_path = os.path.join(self.last_used_folder, filename)
                    if os.path.isfile(file_path):
                        new_filename = f"{vid_name}_{filename}"
                        retries = 0
                        while retries < max_retries:
                            try:
                                os.rename(file_path, os.path.join(self.last_used_folder, new_filename))
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
