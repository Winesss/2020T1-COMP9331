from socket import *
from select import *
import sys
import threading
import time
import datetime as dt
import pickle


class DHTNode:
    def __init__(self):
        self.peer = None
        self.port = None
        self.first_successor = None

        self.second_successor = None
        self.ping_interval = None

        self.isAlive = True
        self.know_peer=None

        self.first_predecessor = None  # in order to give feedback when its update
        self.second_predecessor = None

    def initDHT(self, peer, first_successor, second_successor, ping_interval):
        self.peer = peer
        self.first_successor = first_successor
        self.second_successor = second_successor
        self.ping_interval = ping_interval
        self.port = self.peer + 12000

    def UDPServer(self, host):
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind((host, self.peer + 12000))
        while self.isAlive:
            message, client_address = serverSocket.recvfrom(1024)
            packet_req = pickle.loads(message)
            # receive ping request
            if packet_req["type"] == "Ping_Request":
                print(f"Ping request message received from Peer {packet_req['Peer']} ")
                # record predecessor
                if self.peer == packet_req["FS"]:
                    self.first_predecessor = packet_req["Peer"]
                if self.peer == packet_req["SC"]:
                    self.second_predecessor = packet_req["Peer"]
                response = pickle.dumps({"type": "Ping_Response", "seq": packet_req["seq"], "Peer": self.peer})
                serverSocket.sendto(response, client_address)
        serverSocket.close()

    def UDPClient(self, host):
        clientSocket = socket(AF_INET, SOCK_DGRAM)
        # wait for all the servers are ready
        clientSocket.settimeout(1)
        seq = 0
        recvd_seq1 = 0
        recvd_seq2 = 0
        isFirAlive = True
        isSecAlive = True
        while self.isAlive:
            print(f"Ping requests sent to Peers {self.first_successor} and {self.second_successor}")
            try:
                SendPing = pickle.dumps(
                    {"type": "Ping_Request", "seq": seq, "Peer": self.peer, "FS": self.first_successor,
                     "SC": self.second_successor})
                clientSocket.sendto(SendPing, (host, self.first_successor + 12000))
                ready = select([clientSocket], [], [], 1)
                if ready[0]:
                    packet_rep = pickle.loads(clientSocket.recv(1024))
                    print(f"Ping response received from Peer {packet_rep['Peer']}")
                    if self.first_successor == packet_rep["Peer"]:
                        recvd_seq1 = max(recvd_seq1, packet_rep["seq"])
                    if self.second_successor == packet_rep["Peer"]:
                        recvd_seq2 = max(recvd_seq2, packet_rep["seq"])
                # send ping request to the second successor
                clientSocket.sendto(SendPing, (host, self.second_successor + 12000))
                ready = select([clientSocket], [], [], 1)
                if ready[0]:
                    packet_rep = pickle.loads(clientSocket.recv(1024))
                    print(f"Ping response received from Peer {packet_rep['Peer']}")
                    if self.first_successor == packet_rep["Peer"]:
                        recvd_seq1 = max(recvd_seq1, packet_rep["seq"])
                    if self.second_successor == packet_rep["Peer"]:
                        recvd_seq2 = max(recvd_seq2, packet_rep["seq"])

                if seq-recvd_seq1==2:
                    if isFirAlive:
                        deadPeer=self.first_successor
                        print(f"Peer {deadPeer} is no longer alive")
                        #print("current peer",self.peer)
                        message=pickle.dumps({"type":"Request_Successor","Peer":self.peer,"Kill_Peer":deadPeer})
                        self.forward(host,message,self.second_successor)
                        isFirAlive=False
                if seq-recvd_seq2==2:
                    if isSecAlive:
                        deadPeer = self.second_successor
                        print(f"Peer {deadPeer} is no longer alive")
                        message = pickle.dumps({"type": "Request_Successor", "Peer": self.peer, "Kill_Peer": deadPeer})
                        self.forward(host, message, self.first_successor)
                        isSecAlive = False

                seq+=1
                time.sleep(self.ping_interval)
            except TimeoutError:
                continue
        clientSocket.close()
        # kill

    def TCPserver(self,host):
        serverPort= self.port
        serverSocket=socket(AF_INET, SOCK_STREAM)
        serverSocket.bind((host, serverPort))
        serverSocket.listen(1)

        while True:
            connectionSocket, addr=serverSocket.accept()
            data=b""
            while True:
                packet=connectionSocket.recv(2048)
                if not packet: break
                data+=packet
            #command = pickle.loads(connectionSocket.recv(2048))
            command = pickle.loads(data)
            if command:
                if command["type"]=="Join_Peer":
                    #print(command["join_peer"])
                    # print(command["join_peer"])
                    # print("peer", self.peer)
                    # print("first_succ", self.first_successor)
                    # print("second_succ", self.second_successor)
                    if self.peer < command["join_peer"] and self.first_successor < command["join_peer"]:
                        new_peer = command["join_peer"]
                        print(f"Peer {new_peer} Join request forwarded to my successor")
                        message = pickle.dumps(
                            {"type": "Join_Peer", "join_peer": new_peer, "predecessor": self.peer})
                        self.forward(host, message,self.first_successor)

                    if self.peer > command["join_peer"] > self.first_successor:
                        new_peer = command["join_peer"]
                        print(f"Peer {new_peer} Join request forwarded to my successor")
                        message = pickle.dumps(
                            {"type": "Join_Peer", "join_peer": new_peer, "predecessor": self.peer})
                        self.forward(host, message, self.first_successor)

                    elif self.peer < command["join_peer"] < self.first_successor:
                        predecessor = command["predecessor"]
                        new_peer=command["join_peer"]
                        print(f"Peer {new_peer} Join request received")
                        print(f"My new first successor is Peer {new_peer}")
                        print(f"My new second successor is Peer {self.first_successor}")
                        # new_peer are listening
                        last_message = pickle.dumps({"first_successor": self.first_successor,
                                                     "second_successor": self.second_successor})
                        self.forward(host, last_message, new_peer)
                        # change the current peer's attribute
                        self.second_successor=self.first_successor
                        self.first_successor=new_peer
                        # send the changed message to predecessor
                        pre_message = pickle.dumps(
                            {"type": "Change_Peer", "join_peer": new_peer})
                        self.forward(host, pre_message, predecessor)


                if command["type"]=="Change_Peer":
                    new_peer=command["join_peer"]
                    print(f"Successor Change request received")
                    print(f'My new first successor is Peer {self.first_successor}')
                    print(f"My new second successor is Peer {new_peer}")
                    self.second_successor=new_peer

                if command["type"]=="Quit":
                    quit_peer = command["Quit_Peer"]
                    if self.first_successor==command["Quit_Peer"]:
                        self.first_successor = command["FS"]
                        self.second_successor = command["SC"]
                        print(f"Peer {quit_peer} will depart from the network")
                        print(f"My new first successor is Peer {self.first_successor}")
                        print(f"My new second successor is Peer {self.second_successor}")

                    elif self.second_successor==command["Quit_Peer"]:
                        self.second_successor = command["FS"]
                        print(f"Peer {quit_peer} will depart from the network")
                        print(f"My new first successor is Peer {self.first_successor}")
                        print(f"My new second successor is Peer {self.second_successor}")

                if command["type"]=="Request_Successor":
                    raw_message = {"type": "Response_Successor", "Peer": self.peer, "Kill_Peer": command["Kill_Peer"],
                                   "FS": self.first_successor, "SC": self.second_successor}
                    message = pickle.dumps(raw_message)
                    #print("des", command["Peer"])
                    #print("current peer", self.peer)
                    self.forward(host, message, command["Peer"])

                if command["type"]=="Response_Successor":
                    # first successor is the killed peer
                    #print("first", self.first_successor)
                    #print("kill", command['Kill_Peer'])

                    if self.first_successor == command['Kill_Peer']:
                        self.first_successor = self.second_successor
                        self.second_successor = command['FS']
                        print(f"My new first successor is Peer {self.first_successor}")
                        print(f"My new second successor is Peer {self.second_successor}")
                    # second successor is the killed peer
                    if self.second_successor == command['Kill_Peer']:
                        print(f"My new first successor is Peer {self.first_successor}")
                        if command["Kill_Peer"] == command["FS"]:
                            self.second_successor = command["SC"]
                        else:
                            self.second_successor = command["FS"]
                        print(f"My new second successor is Peer {self.second_successor}")

                if command["type"]=="Store_file":
                    des_peer=command["des_peer"]
                    filename=command["file_name"]
                    if des_peer==self.peer:
                        print(f"Store {filename} request accepted")
                    else:
                        print(f"Store {filename} request forwarded to my successor")
                        message = pickle.dumps({"type": "Store_file", "des_peer": des_peer,"file_name":filename})
                        self.forward(host, message, self.first_successor)

                if command["type"]=="Request_file":
                    visit_peer=command["visitedPeer"]
                    filename = command["file_name"]
                    location=command["location"]
                    des_peer=command["Peer"]
                    if self.peer not in visit_peer and self.peer!=des_peer:
                        visit_peer.append(self.peer)
                        if location==-1 and self.find_loc(filename)>-1:
                            location=self.find_loc(filename)
                        if location==self.peer:
                            print(f"File {filename} is stored here")
                            pickle_out = pickle.dumps({"type": "FileFound_response", "SendingPeer": self.peer,"RequestingPeer": des_peer,"filename":filename})
                            self.forward(host,pickle_out,des_peer)
                            print(f"Sending file {filename} to Peer {des_peer}")
                            self.file_transfer(host,self.peer,filename,des_peer)

                        else:
                            print(f"Request for File {filename} has been received, but the file is not stored here")
                            message=pickle.dumps({"type":"Request_file","file_name":filename,"Peer": des_peer, "location": location,"visitedPeer":visit_peer})
                            self.forward(host,message,self.first_successor)
                if command["type"]=="FileFound_response":
                    send_peer=command["SendingPeer"]
                    filename=command["filename"]
                    print(f"Peer {send_peer} had File {filename}")
                    # print(f"Receiving File 4103 from Peer 8")
                    file=open("received_"+str(filename)+".pdf","wb")
                    if file:
                        print(f"Receiving File {filename} from Peer {send_peer}")
                if command["type"]=="File_transfer":
                    filename=command["filename"]
                    file = open("received_" + str(filename) + ".pdf", "wb")
                    file.write(command["data"])
                    print(f"File {filename} received")
            connectionSocket.close()


    def forward(self,host,message,dest):
        #print(message, '------', dest)
        serverName = host
        serverPort = dest + 12000
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((serverName, serverPort))
        clientSocket.send(message)
        clientSocket.close()

    def Hashmod(self,filename):
        hash=filename% 256
        return hash

    def find_loc(self,filename):
        hash=self.Hashmod(filename)
        location = self.first_successor
        if self.peer< hash <= self.first_successor:
            return location
        elif self.first_successor<self.peer:
            if self.peer< hash <=255 or hash <=self.first_successor:
                return location
        return -1

    def file_transfer(self,host,peer,filename,dest):
        tcp_Port=dest+12000
        tcp_server_socket=socket(AF_INET,SOCK_STREAM)
        tcp_server_socket.connect((host,tcp_Port))
        file=open(str(filename)+".pdf","rb")
        data=file.read()
        file.close()
        message=pickle.dumps({"type":"File_transfer","filename":filename,"data":data})
        tcp_server_socket.sendto(message,(host,tcp_Port))
        print(f"The file has been sent")
        tcp_server_socket.close()

    def CommandInput(self,host):
        while True:
            command=sys.stdin.readline()
            if command.startswith("Quit"):
                self.isAlive = False
                message = pickle.dumps(
                    {"type": "Quit", "Quit_Peer": self.peer, "FS": self.first_successor, "SC": self.second_successor})
                #print("first_pre", self.first_predecessor)
                #print("second_pre", self.second_predecessor)
                self.forward(host, message, self.first_predecessor)
                self.forward(host, message, self.second_predecessor)
            if command.startswith("Store"):
                command=command.split()
                #print(command)
                filename=int(command[1])
                des_peer=self.Hashmod(filename)
                if des_peer==self.peer:
                    print (f"Store {filename} request accepted")
                else:
                    print(f"Store {filename} request forwarded to my successor")
                    message=pickle.dumps({"type":"Store_file", "des_peer":des_peer,"file_name":filename})
                    self.forward(host,message,self.first_successor)
            elif command.startswith("Request"):
                location=-1
                command = command.split()
                filename = int(command[1])
                if self.first_successor<self.peer:
                    location=self.find_loc(filename)
                message=pickle.dumps({"type":"Request_file","file_name":filename,"Peer":self.peer, "location":location,"visitedPeer":[]})
                self.forward(host, message, self.first_successor)
                print(f"File request for {filename} has been sent to my successor")


# learn the two successors
def search(join_peer, know_peer):
    client_Socket = socket(AF_INET, SOCK_STREAM)
    client_Socket.connect(('localhost', 12000+know_peer))
    message=pickle.dumps({"type":"Join_Peer", "join_peer":join_peer})
    client_Socket.sendto(message,(host, 12000+know_peer))
    client_Socket.close()


    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('localhost', 12000+join_peer))
    serverSocket.listen(1)
    connectionSocket, addr = serverSocket.accept()
    successor_list = pickle.loads(connectionSocket.recv(1024))
    #print(successor_list)
    print(f"Join request has been accepted")
    print(f"My first successor is Peer {successor_list['first_successor']}")
    print(f"My second successor is Peer {successor_list['second_successor']}")
    serverSocket.close()

    return successor_list

if __name__ == '__main__':
    host = 'localhost'
    type = sys.argv[1]
    p2p = DHTNode()
    if type == "init":
        peer = int(sys.argv[2])
        first_successor = int(sys.argv[3])
        second_successor = int(sys.argv[4])
        ping_interval = int(sys.argv[5])
        p2p.initDHT(peer, first_successor, second_successor, ping_interval)
        print(f"Start peer {peer} at port {peer + 12000}")
        print(f"Peer {peer} can find first successor on port {first_successor + 12000} and second successor on port {second_successor + 12000}.")



    elif type == "join":
        join_peer = int(sys.argv[2])
        know_peer = int(sys.argv[3])
        ping_interval = int(sys.argv[4])
        successor_list = search(join_peer, know_peer)

        p2p.initDHT(join_peer, successor_list['first_successor'], successor_list['second_successor'], ping_interval)

    Thred1 = threading.Thread(target=p2p.UDPServer, args=(host,))
    Thred2 = threading.Thread(target=p2p.UDPClient, args=(host,))
    Thred3 = threading.Thread(target=p2p.TCPserver, args=(host,))
    Thred4 = threading.Thread(target=p2p.CommandInput, args=(host,))

    Thred1.start()
    Thred2.start()
    Thred3.start()
    Thred4.start()
