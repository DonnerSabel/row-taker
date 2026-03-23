# import socket



# def start_server()
#     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server_socket.bind(('localhost', 12345))
#     server_socket.listen(5)
#     print("Server started and listening on port 12345")

#     while True:
#         client_socket, addr = server_socket.accept()
#         print(f"Connection from {addr} has been established.")
#         client_socket.sendall(b"Welcome to the Row Taker Server!")
#         client_socket.close()