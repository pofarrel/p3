#This will make nodes send all their peers on to new peer
#input port num
#should be able to connect  other nodes to network with same file 
import socket
import threading
import sys
import hashlib
from datetime import datetime
import random
import math
import time

global num_nodes 
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

    
class Nodes:
        #initialising client node, automatically done when node created 
    def  __init__(self,port,password):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # initiate port no., above 1024
        self.host = socket.gethostbyname(socket.gethostname())  #ip address of the node,will change to pi ip address
        #self.host = self.server.getsockname()  #ip address of the node,will change to pi ip address
        print(self.host)
        self.server.bind((self.host,port)) 
        self.address = (self.host,port)
        self.peers = []
        self.password = hash_password(password)
        #assigning random starting coordinates
        self.xcoord = random.uniform(32.074822,33.121270)
        self.ycoord = random.uniform(46.406928,46.848291)
        threading.Thread(target=self.timer_func, args=()).start()
        print("starting Node %s \n" %num_nodes)
        print("Starting coordinates: " + str(self.xcoord) + " " + str(self.ycoord))

    def timer_func(self):
        #to have peers completing blocks after 5 seconds
        while True:
            time.sleep(5)
            self.next_block()
        
    #function to allow nodes to connect 
    def listen_for_nodes(self):
        self.server.listen(4)
        while True:
            connection,addr = self.server.accept() 
            received_password = connection.recv(1024).decode()
            if received_password == self.password:
                connection.send(b'OK')     
                print("Connection from: " + str(addr))
                data = connection.recv(1024).decode()
                data = data.split()        #storing the port number the node is listening on so other peers can connect
                port_num = int(data[0])
                print(data)
                if(data[1]== "New"):
                    print("New node found, sending peers")
                    self.handle_new_node(connection)
                self.peers.append((connection,addr,port_num))
                self.next_block() #example
                # self.connect_nodes(address[1])  #need connection to go both ways 
                # connection.send(str(self.num).encode())
                #want to start another thread to handle incoming msgs, putting here so it starts when connectino made
                threading.Thread(target=self.handle_msgs, args=(connection,)).start()
            else:
                connection.send(b'INVALID')
                print("Attempted unauthorised connection, closing connection")
                connection.close()


    def handle_new_node(self,connection):
            #handling new node connecting to network 
            if self.peers:
                for peer in self.peers:
                    #sending all peers to new node
                    #only need to send ip and port
                    message = str(peer[1][0]) + " " + str(peer[1][1]) + " " + str(peer[2]) + " "

                    connection.send(message.encode())
                print("Sent peers to new node")
            else:
                print("No peers to send")
                connection.send("Just me".encode())
            response = connection.recv(1024).decode()
            if response == "received":
                #Now need to send map coordinates to new node
                print("Sending map coordinates to new node")
                with open("dividedmap.txt", "r") as map:
                    lines = map.readlines()
                    for line in lines:
                        mappedx = line.split(",")
                        message = str(mappedx[0]) + " " + str(mappedx[1]) + " " + str(mappedx[2]) + " " 
                        connection.send(message.encode())
                        response = connection.recv(1024).decode()
                        if response != "received":
                            print("Error sending map coordinates")
                            break
                    connection.send("end".encode())
                    print("Sent remaining blocks")          
            
    def handle_msgs(self,connection):
            #runs when message comes in
            #print("Node%s handling"%self.num)
            while True:
                data = connection.recv(1024).decode()
                if not data:
                    #connection lost
                    break
                data = str(data)
                print(data)
                print("Message received: %s "%(data))
                if data.startswith("COVERED"):
                    data = data.split()
                    print("Block %s is being covered, removing from list"%data[1])
                    self.remove_block(data[1])
            connection.close()
            print("Connection closed")
            #want to remove from peer list
            for peer in self.peers:
                if peer[0] == connection:
                    self.peers.remove(peer)
                    print("Peer removed")
                    break
            # End thread
            return

            
            
    def send_all(self,msg):

        for peer in self.peers:
            #print("peer %s sending"%self.num)
            peer[0].send(msg.encode())
        
    def connect_nodes(self,port,host):
        #connecting to other nodes in network
        print("Connecting to node on port %s"%port)
        print("With ip: %s"%host)
        connection = socket.socket()
        message = str(self.address[1]) + " " #port number I am listening on
        connection.connect((host,port))
        connection.send(self.password.encode())
        auth_response = connection.recv(1024).decode()
        if auth_response == "OK":
            print("Connection authorised")
            #if this is a new node, it will have no peers. 
            if self.peers:
                #not a new node, adding peer to list
                message += "Not new"
                connection.send(message.encode())
                self.peers.append((connection, (self.host, port),port))
            else:
                #new node, adding peer to list and requesting info about other nodes
                self.peers.append((connection, (self.host, port),port))
                self.network_join(connection)
                #starting thread to handle incoming messages from this connection
            threading.Thread(target=self.handle_msgs, args=(connection,)).start()  
        else:
            print("Connection unauthorised")
            connection.close()      

    
    def network_join(self,connection):
        #when a new node joins the network, it requests informatino to make connection with other nodes
            #New node is keyword
            message = str(self.address[1]) + " " #port number I am listening on
            message += "New node "
            connection.send(message.encode())
            new_peers_info = list() #peers are list in a list so need to send each item individually 
            new_peers = list()
            odds = 1
            evens = 0
            #data contains info about other nodes to connect to in form (connection, (self.host, port),int(num))
            #important parts are the ip address and port number
            #for now only need port number because same ip but will need to update connect nodes to take ip address
            while True:
                #receving peers 1 by 1
                #should be in form of (ip,port)
                data = connection.recv(1024).decode()
            
                if data and data == 'Just me':
                    connection.send("received".encode())
                    print('No other nodes in network')
                    self.recv_map(connection)
                    break
                
                elif data:
                    data = data.split()
                    for i in range(len(data)):
                        #want in form (ip,port,nodenum)) 
                        new_peers_info.append(data[i])
                        if((i+1)%3 == 0):
                            new_peers.append(new_peers_info)
                            print('found peer: "%s"' %new_peers_info) 
                            new_peers_info = list()
                    connection.send("received".encode())
                    if new_peers:
                        for peer in new_peers:
                            self.connect_nodes(int(peer[2]),peer[0]) 
                    self.recv_map(connection)
                    break
                    

    def recv_map(self,connection):
        write = ""
        while True:
            data = connection.recv(1024).decode()
            if data and data != "end":

                data = data.split()
                for i in range(len(data)):
                    #want in form(block,lat,long)
                    write+=data[i] + ","
                    if((i+1)%3 == 0):
                        write+="\n"
                connection.send("received".encode())
            else:
                break
        with open("dividedmap.txt", "w") as map2:
            map2.write(write)
            print("received remaining blocks, stored in file divided.txt")
                 

    #send message to specific node
    def send_to(self,msg,node):
        #finding the connection to the node
        connection = self.find_connection(node)
        connection.send(msg.encode())
        


    def remove_block(self,msg):
    #This is called when another block is being covered by a peer, removing from stored list
        write = ""
        with open("dividedmap.txt", "r") as map:
            lines = map.readlines()
            for line in lines:
                mapped = line.split(",")
                block = mapped[0]
                if not block == msg:
                    write += line
                    
        with open("dividedmap.txt", "w") as map2:
            map2.write(write)


    def next_block(self):
        #finding next block to cover
        dest = []
        try:
            print("Finding next block")
            with open('dividedmap.txt','r') as map:
                next(map)
                distance1 = 50
                for line in map:
                    mappedx = line.split(",")
                    math1 = (self.xcoord - float(mappedx[1]))**2 
                    math2 = (self.ycoord - float(mappedx[2]))**2
                    distance = math.sqrt(math1 + math2)
                    if distance < distance1:
                        distance1 = distance
                        dest = mappedx
                        
            self.xcoord = float(dest[1])
            self.ycoord = float(dest[2])
            self.send_block(dest[0])
            self.remove_block(dest[0])
            print("I am going to block: {}, latitude:{}, longitude:{}".format(dest[0], dest[1], dest[2]))
        except:
            print("No more blocks to cover")
            sys.exit()

    def send_block(self,block):
        #alerting nodes of plan to cover certain box
        message = "COVERED " + block
        self.send_all(message)


def map_divider():
    #splitting up map at the start of the program
    mappedx = []
    mapped = []
    mapped2 = []

    
    with open('map.txt','r') as map:
        for line in map:
            mappedx = line.split(",")
            mapped.append(mappedx)



    lengthx = (float(mapped[4][1])) - (float(mapped[2][1]))
    lengthy = (float(mapped[4][2])) - (float(mapped[3][2]))

    boxlengthx = lengthx / 10
    boxlengthy = lengthy / 10


    #n = 0
    startingx = float(mapped[2][1])
    startingy = float(mapped[3][2])
    startingxx = float(mapped[2][1])
    startingyy = float(mapped[3][2])

    for i in range(10):
        mapped2x = [] * 10
        startingy = startingy + boxlengthy
        startingx = startingxx
        for i in range(10):
            startingx = startingx + boxlengthx
            mapped2x.append(startingx)
            mapped2x.append(startingy)   
            
            
        mapped2.append(mapped2x)    


    with open("dividedmap.txt",'w') as map:
        pass
    alpha = (["A"]+["B"]+["C"]+["D"]+["E"] + ["F"]+["G"]+["H"]+["I"]+["J"])
    nums = (["1"]+["2"]+["3"]+["4"]+["5"] + ["6"]+["7"]+["8"]+["9"]+["10"])
    with open('dividedmap.txt', 'a+') as f:
        f.write("{}, {}, {},".format("block", "latitude", "longitude"))
        for i in range(10):   
            for j in range(10):
                f.write("\n{}{}, {}, {},".format(alpha[i], nums[j], mapped2[i][j], mapped2[i][j+1]))


if __name__ == '__main__':
    num_nodes = 1
    #password = "mypassword"  # Set the password here
    port_num = input("input port number-> ")  # take input
    connect_to = input("input port number to connect to-> ")
    ip = input("input ip address to connect to-> ")
    user_password = input("input password-> ")
    port_num = int(port_num)
    connect_to = int(connect_to)
    Node1 = Nodes(port_num,user_password)
    try:
        Node1.connect_nodes(connect_to,ip)
    except:
        print("no node to connect to, I am the first node, splitting up map \n")
        map_divider()
    threading.Thread(target=Node1.listen_for_nodes).start()
    
    message = input("send to all Nodes-> ")  # take input
    while message.lower().strip() != 'bye':
        Node1.send_all(message)
        message = input("send to all Nodes-> ")
 
    sys.exit()


        
