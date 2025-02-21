import socket
import os

def send_file(server_ip, server_port, file_path):
    # Get file details
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Create a socket and connect to the server
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, server_port))

        # Send file size as a fixed 10-byte string (padded with zeros)
        s.send(f"{file_size:010d}".encode())

        # Send file name followed by a newline to mark its end
        s.sendall(f"{file_name}\n".encode())

        # Send file content in chunks
        with open(file_path, 'rb') as f:
            while chunk := f.read(1024):
                s.sendall(chunk)

    print(f"File '{file_name}' ({file_size} bytes) sent successfully!")

# Example usage
if __name__ == "__main__":
    SERVER_IP = "localhost"  # Change this if needed
    SERVER_PORT = 5123       # Should match the server's port
    FILE_PATH = "path/to/your/file.ext"  # Specify the file you want to send

    send_file(SERVER_IP, SERVER_PORT, FILE_PATH)
