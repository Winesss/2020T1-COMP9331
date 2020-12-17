from socket import *
import sys

serverPort=int(sys.argv[-1])

serverSocket=socket(AF_INET, SOCK_STREAM)   #TDP connection
serverSocket.bind(('localhost', serverPort))
serverSocket.listen(1)
print("The server is ready to receive")

while True:
    connectionSocket, addr=serverSocket.accept()
    try:
        request_path=connectionSocket.recv(1024).decode().split(' ')[1].replace('/', '')
        if request_path=='':
            request_path='index.html'
        if ".html" in request_path:
            with open(request_path, "rb") as file:
                file_data=file.read()
            response_line="HTTP/1.1 200 OK\r\n"
            response_header="Content-Type:text/html\r\n"
            response_body=file_data
            response_data=(response_line+response_header+"\r\n"+ response_body).encode()
            connectionSocket.send(response_data)
            file.close()
        elif ".png" in request_path:
            with open(request_path, "rb") as file:
                file_data=file.read()
            response_line="HTTP/1.1 200 OK\r\n"
            response_header="Content-Type:image/png\r\n"
            response_info="Accept-Ranges: bytes\r\n"
            response_body=file_data
            response_data=(response_line+response_header+response_info+"\r\n").encode()+ response_body
            connectionSocket.send(response_data)
            file.close()
        connectionSocket.close()
    except:
        response_line = "HTTP/1.1 404 Not Found\r\n"
        response_header = "Content-Type:text/html\r\n"
        response_body = "<html><head><title>404</title></head><body><p>404 Not Found </p></body></html>"
        response_data = (response_line + response_header + "\r\n" + response_body).encode()
        connectionSocket.send(response_data)
        connectionSocket.close()



