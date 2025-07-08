import socket
import os
import requests

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


def send_file_to_endpoint(endpoint: str, file_path: str, field_name: str = "file", extra_data: dict = None, headers: dict = None) -> requests.Response:
    """
    Sends a file to a specified HTTP endpoint using multipart/form-data.

    :param endpoint: The server's upload URL.
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
    

# Example usage
if __name__ == "__main__":
    SERVER_IP = "localhost"  # Change this if needed
    SERVER_PORT = 5123       # Should match the server's port
    FILE_PATH = "path/to/your/file.ext"  # Specify the file you want to send

    send_file(SERVER_IP, SERVER_PORT, FILE_PATH)
