import src.obsRecording as obsRecording
import src.popUp as popUp
import yaml

class ConfigInfo:
    def __init__(self, config_file):
        with open(config_file, 'r') as file:
            args = yaml.safe_load(file)
            self.obs_host = args['obs_connection']['obs_host']
            self.obs_port = args['obs_connection']['obs_port']
            self.obs_password = args['obs_connection']['obs_password']
            self.buffer_folder = args['paths']['buffer_folder']
            self.save_folder = args['paths']['save_folder']
            self.target_host = args['target_machine']['ip']
            self.target_port = args['target_machine']['port']
        
        if not self.__check_values():
            print("Error: Missing values in config file.")
            exit()

    def __check_values(self):
        # Check connection values
        if self.obs_host is None or self.obs_port is None:
            return False

        # Check path values
        if self.buffer_folder is None or self.save_folder is None:
            return False

        return True

if __name__ == '__main__':
    # # Example usage locally
    args = ConfigInfo('config.yaml')

    # obs = obsRecording.OBSController(args.obs_host, args.obs_port, args.obs_password, popUp=popUp.PopUp())
    
    # if obs.statusCode == obsRecording.OBSStatus.NOT_CONNECTED or obs.statusCode == obsRecording.OBSStatus.ERROR:
    #     print("OBS not connected or turned off. Please check the connection and try again.")
    #     exit()

    # try:
    #     # Set save and buffer locations, also set the video name
    #     obs.set_save_location(args.save_folder, vid_name="testvid")
    #     obs.set_buffer_folder(args.buffer_folder)

    #     # Start recording
    #     obs.start_recording()

    #     # Simulate recording duration
    #     import time
    #     recordingTime = 5 # 5 seconds
    #     print(f"Recording for {recordingTime} seconds...")
    #     time.sleep(recordingTime)

    #     # Stop recording
    #     obs.stop_recording()

    # finally:
    #     # Savely disconnect from OBS
    #     obs.disconnect()


    # Example usage with WebSocket
    # Opening a websocket server to control OBS
    from src.websocketInterface import OBSWebSocketInterface
    import websockets
    import threading
    obsWebsock = OBSWebSocketInterface(args.target_host, args.target_port, args.obs_host, args.obs_port, args.obs_password, args.save_folder, args.buffer_folder)
    server_thread = threading.Thread(target=obsWebsock.start_server)
    server_thread.start()

    # Sending messages to target machine
    import time
    import asyncio
    async def send_message(message):
        uri = f"ws://{args.target_host}:{args.target_port}"
        async with websockets.connect(uri) as websocket:
            await websocket.send(message)
            print(f"Sent message: {message}")
    
    asyncio.get_event_loop().run_until_complete(send_message("SetNameTESTNAAM"))
    asyncio.get_event_loop().run_until_complete(send_message("Start"))
    # Wait for recording to finish
    time.sleep(2)
    asyncio.get_event_loop().run_until_complete(send_message("Stop"))
    asyncio.get_event_loop().run_until_complete(send_message("Kill"))
