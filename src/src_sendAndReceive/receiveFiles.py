import asyncio
import os
import argparse

class AsyncFileReceiver:
    def __init__(self, host, port, output_folder):
        self.host = host
        self.port = port
        self.output_folder = output_folder

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    async def receive_file(self, reader, writer):
        try:
            # Read the file size (first 10 bytes)
            file_size_data = await reader.readexactly(10)
            file_size = int(file_size_data.decode().strip())  # Convert to integer

            # Read the file name (until newline)
            file_name_data = await reader.readuntil(b"\n")
            file_name = file_name_data.decode().strip()  # Remove trailing newline

            file_path = os.path.join(self.output_folder, file_name)
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
