import src.obsRecording as obsRecording
import src.popUp as popUp
import yaml
import asyncio

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
            self.receiver_host = args['receiver_machine']['ip']
            self.receiver_port = args['receiver_machine']['port']
            self.python_path = args['python_path']
            self.receiver_script_path = args['receiver_script_path']
        
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

async def sender_main(args):
    from src.src_sendAndReceive.receiveFiles import AsyncFileReceiver, run_receiver_in_new_terminal
    import websockets

    async def send_message(message):
        uri = f"ws://{args.target_host}:{args.target_port}"
        async with websockets.connect(uri) as websocket:
            await websocket.send(message)
            print(f"Sent message: {message}")

    # Launch the file receiver in a new terminal
    run_receiver_in_new_terminal(args.receiver_host, args.receiver_port, args.save_folder, args.receiver_script_path, args.python_path)

    # Send commands to request the file
    await send_message("SetName TEST6")
    await send_message("Start")
    await asyncio.sleep(4)
    await send_message("Stop")
    await send_message(f"SendFilePrevious {args.receiver_host} {args.receiver_port}")

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
    asyncio.run(sender_main(args))