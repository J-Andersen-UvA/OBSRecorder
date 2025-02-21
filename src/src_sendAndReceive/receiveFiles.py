import asyncio
import os
import argparse
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import fileManaging
import subprocess
import socket

def run_receiver_in_new_terminal(host, port, output_folder, receiver_script_path=b'C:\Users\VICON\Desktop\Code\OBSRecorder\OBSRecorder\src\src_sendAndReceive\receiveFiles.py', python_path=b'C:\Users\VICON\.pyenv\pyenv-win\versions\3.10.11\python.exe'):
    """Function to launch a separate terminal with the receiver script"""
    def is_port_in_use(host, port):
        """Check if a port is already in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False  # Port is available
            except OSError:
                return True  # Port is in use

    # Check if port is already in use
    # loop = asyncio.get_running_loop()
    # asyncio.set_event_loop(loop)
    if is_port_in_use(host, port):
        print(f"Port {port} is already in use. Please choose a different port.")
        return False  # Stop execution if the port is in use

    # Adjust the command to run the receiver in a new terminal window (e.g., for Linux/Mac)
    if sys.platform == "win32":
        # For Windows, use start to open a new command prompt
        subprocess.Popen([
            "start", 
            "cmd", 
            "/K", 
            python_path, 
            receiver_script_path, 
            "--host", host, 
            "--port", str(port), 
            "--output_folder", output_folder
        ], shell=True)
    else:
        # For Unix/Linux/MacOS, use gnome-terminal or similar
        subprocess.Popen(["gnome-terminal", "--", python_path, receiver_script_path, f'--host {host} --port {port} --output_folder {output_folder}', "&"])


class AsyncFileReceiver:
    def __init__(self, host, port, output_folder):
        self.host = host
        self.port = port
        self.output_folder = output_folder

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        # If there is already a process running on the specified port, we print a warning and quit.
        try:
            asyncio.run(self.check_port())
        except Exception as e:
            sys.exit()

    async def check_port(self):
        try:
            server = await asyncio.start_server(
                self.receive_file, self.host, self.port
            )
            server.close()
            await server.wait_closed()
        except OSError as e:
            print(f"Port {self.port} is already in use. Please choose a different port.")
            raise e

    async def receive_file(self, reader, writer):
        try:
            # Read the file size (first 10 bytes)
            file_size_data = await reader.readexactly(10)
            file_size = int(file_size_data.decode().strip())  # Convert to integer

            # Read the file name (until newline)
            file_name_data = await reader.readuntil(b"\n")
            file_name = file_name_data.decode().strip()  # Remove trailing newline

            # Construct the file path
            take_name = file_name.split("_", 1)[0]
            date_folder = fileManaging.get_save_location(self.output_folder, take_name)
            file_path = os.path.join(date_folder, file_name)
            print(f"Receiving file: {file_name} ({file_size} bytes)...")

            # Read the file contents
            bytes_received = 0
            with open(file_path, 'wb') as file:
                while bytes_received < file_size:
                    chunk = await reader.read(min(1024, file_size - bytes_received))
                    if not chunk:
                        break
                    file.write(chunk)
                    bytes_received += len(chunk)

            print(f"Received file: {file_name}")

            # Close connection
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            print(f"Error receiving file: {e}")

    async def start_server(self):
        server = await asyncio.start_server(
            self.receive_file, self.host, self.port
        )
        addr = server.sockets[0].getsockname()
        print(f"Async server listening on {addr}")

        async with server:
            await server.serve_forever()

# Example usage
if __name__ == "__main__":
    # make host, port and output_folder flags for the script
    parser = argparse.ArgumentParser(description="Async File Receiver")
    parser.add_argument('--host', type=str, default='localhost', help='Host to listen on')
    parser.add_argument('--port', type=int, default=5123, help='Port to listen on')
    parser.add_argument('--output_folder', type=str, default='./out', help='Folder to save received files')

    args = parser.parse_args()
    print(args)

    HOST = args.host
    PORT = args.port
    OUTPUT_FOLDER = args.output_folder

    receiver = AsyncFileReceiver(HOST, PORT, OUTPUT_FOLDER)
    asyncio.run(receiver.start_server())  # Run the server
