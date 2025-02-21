import socket
import os

def send_file(server_ip, server_port, file_path):
    # Get file details.
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Create a socket and connect to the server.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, server_port))
        # Send file size and name.
        s.send(str(file_size).encode())
        s.send(file_name.encode())
        # Send file content.
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                s.send(data)
    print("File sent successfully!")

# example usage
if __name__ == "__main__":
    SERVER_IP = "localhost"  # Adjust as needed
    SERVER_PORT = 5123       # Should match the server's port
    FILE_PATH = "path/to/your/file.ext"  # Specify the file you want to send

    send_file(SERVER_IP, SERVER_PORT, FILE_PATH)
