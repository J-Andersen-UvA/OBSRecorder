import socket
import os

class FileReceiver:
    def __init__(self, host, port, output_folder):
        self.host = host
        self.port = port
        self.output_folder = output_folder

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def receive_file(self, connection):
        file_size = int(connection.recv(1024).decode())
        file_name = connection.recv(1024).decode()
        file_path = os.path.join(self.output_folder, file_name)

        with open(file_path, 'wb') as file:
            bytes_received = 0
            while bytes_received < file_size:
                data = connection.recv(1024)
                if not data:
                    break
                file.write(data)
                bytes_received += len(data)
        print(f"Received file: {file_name}")

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")

        while True:
            connection, address = server_socket.accept()
            print(f"Connection from {address}")
            self.receive_file(connection)
            connection.close()

# example usage
if __name__ == "__main__":
    HOST = 'localhost'
    PORT = 5123
    OUTPUT_FOLDER = './out'
    receiver = FileReceiver(HOST, PORT, OUTPUT_FOLDER)
    receiver.start_server()
