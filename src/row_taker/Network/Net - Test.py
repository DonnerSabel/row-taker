import socket

server= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 5555)) #

def start_server():
    server.listen()     #server waiting for connection op port 5555


    client_socket, addr = server.accept() #accepting the connection from client and storing the client socket and address in variables
    print(f"Connection from {addr} has been established.")
    with client_socket:
        client_socket.send(bytes("Welcome to the server!", "utf-8"))#sending a welcome message to the client
        client_socket.close() #closing the client socket after sending the message
        while True:
            data = client_socket.recv(1024) #receiving data from the client
            if not data:
                break
            client_socket.sendall(data) #sending the received data back to the client (echoing)

def client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", 5555)) #connecting to the server on localhost and port 5555
    welcome_message = client_socket.recv(1024) #receiving the welcome message from the server
    print(welcome_message.decode("utf-8")) #printing the welcome message

    while True:
        message = input("Enter a message to send to the server (or 'exit' to quit): ")
        if message.lower() == "exit":
            break
        client_socket.sendall(bytes(message, "utf-8")) #sending the message to the server
        response = client_socket.recv(1024) #receiving the response from the server
        print(f"Received from server: {response.decode('utf-8')}") #printing the response from the server

    client_socket.close() #closing the client socket when done

print("AAAAAAA")
start_server() #starting the server