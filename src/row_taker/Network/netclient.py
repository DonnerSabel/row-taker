import socket
import json


def client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("192.168.221.88", 5555)) #connecting to the server on localhost and port 5555
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

client() #starting the client