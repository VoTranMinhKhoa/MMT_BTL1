import socket
import threading
import json
import os
import time
from utils import create_metainfo_hashtable
import argparse
import bencodepy


import hashlib
import sys
# https://www.geeksforgeeks.org/file-transfer-using-tcp-socket-in-python/

class Tracker:
    def __init__(self, ip,port:int =5050, peer_list:set = {}, header_length = 1024,metainfo_storage="metainfo") -> None:
        self.ip = ip
        self.port = port
        self.id = hashlib.sha1(f"{self.ip}:{self.port}".encode()).hexdigest()
        self.header_length = header_length
        self.peer_list = set(peer_list)
        self.metainfo_storage = metainfo_storage
        if not os.path.exists(self.metainfo_storage):
            os.makedirs(self.metainfo_storage)
            
        self.peer_list_semaphore = threading.Semaphore()
        self.socket_tracker = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket_tracker.bind((self.ip,self.port))
        self.socket_tracker.listen(10)
        self.metainfo_hashtable = create_metainfo_hashtable(self.metainfo_storage)
        self.metainfo_hashtable_semaphore = threading.Semaphore()
        print(f"[TRACKER] Socket is binded to {self.port}")
        self.running = True
        self.run()
        
    def run(self):
        thread = threading.Thread(target=self.start)
        thread.daemon = True
        thread.start()
        while True:
            try:
                # print("still working")
                time.sleep(1)
            except KeyboardInterrupt:
                # self.socket_tracker.close()
                self.running = False
                # sys.exit()
                print("EXIT")
                break
        
    def start(self):
        print("[STARTING] Server is starting ...")
        while self.running:
            connection, address = self.socket_tracker.accept()
            thread = threading.Thread(target=self.handle_peer, args=(connection, address))
            thread.daemon = True
            print(f"[ACTIVE CONNECTION] {threading.active_count() - 1}")
            thread.start()    
            
    def handle_peer(self, connection, address):
        print(f"[NEW CONNECTION] {address} connected")
        message = self.recieve_message(connection, address)
        response = self.process_message(message)
        self.response_action(connection,address, response)    
        connection.close()
             
    def parse_metainfo(self,hash_info) -> dict:
        decoder = bencodepy.Bencode(
            encoding='utf-8'
        )
        metainfo_path = self.metainfo_hashtable.get(hash_info)
        if metainfo_path:
            with open(metainfo_path, "r") as torrent:
                metainfo = torrent.read()
                # metainfo = json.loads(metainfo)
                # metainfo = bencodepy.decode(metainfo)
                metainfo = decoder.decode(metainfo)
                return metainfo
        else:
            return None
    
    def add_peer(self, peer: tuple)-> None:
        with self.peer_list_semaphore:
            try:
                print(f"[TRACKER] Add peer {peer} to list tracking")
                self.peer_list.add(peer)
                print(self.peer_list)
            except Exception as e:
                print(e)
                          
    def remove_peer(self,peer: tuple)-> None:
        with self.peer_list_semaphore:
            try:
                print(f"[TRACKER] remove peer {peer} in list tracking")
                if self.peer_list:
                    self.peer_list.discard(peer)
                print(self.peer_list)
            except Exception as e:
                print(e)
    
    def update_metaifo_hash_table(self,key: str,metainfo_path: str):
        with self.metainfo_hashtable_semaphore:
            self.metainfo_hashtable.update({key:metainfo_path})
        
    def send_message(self,connection,mess: dict):
        """
        send message on connection to another peer

        Args:
            connection (socket): socket connection
            mess (dict): message need send 
        """
        message = json.dumps(mess)
        # print(f"[SEND MESSAGE]")
        message = message.encode("utf-8")
        message_length = str(len(message)).encode("utf-8")
        message_length += b' '*(self.header_length - len(message_length))
        connection.sendall(message_length)
        connection.sendall(message)
        
    def recieve_message(self, connection, address= None) -> dict:
        """
        recieve message on connection from another peer

        Args:
            connection (socket): socket connection
            address ((ip, port), optional): address of this connection host. Defaults to None.

        Returns:
            dict: message need recieve
        """
        message_length = connection.recv(self.header_length).decode("utf-8")
        if not message_length:
            return None
        message_length = int(message_length)
        message = b''
        while len(message) < message_length:
            data = connection.recv(min(message_length - len(message), 1024))  # Adjust buffer size as needed
            if not data:
                return None  # Handle unexpected connection termination
            message += data        
        # print(f"[RECIEVE MESSAGE]")

        return json.loads(message)
   
    def send_file(self, connection,file_path,chunk= 512*1024):
        """
        send all data of file to other peer which is connected with

        Args:
            connection (socket): connnection to other peer
            file_path (string): file path of file which need to send
            chunk (int, optional): chunk size. Defaults to 512*1024 (521kB)
        """
        # with self.send_file_semaphore:
        with open(file_path,"rb") as item:
            try:
                while True:
                    data = item.read(chunk)
                    if not data: 
                        connection.sendall(b'done')
                        break
                    connection.sendall(data)
                    # self.update_upload(sys.getsizeof(data))
                if connection.recv(chunk) == b'ok':
                    print(f"[SEND PIECE] send successfully : {file_path}")
                    

            except Exception as e:
                print(e)
       
    def recieve_file(self,connection, out_path,chunk=1024, test = 0):
        """
        recieve file from other peer which is connected with

        Args:
            connection (socket):connnection to other peer
            out_path (str): file output path
            chunk (int, optional): chunk size. Defaults to 512*1024 (521kB)
            
        """
        message = self.recieve_message(connection)
        file_name = message.get("file_name")
        print(f"[RECIEVING PIECE]:{file_name}")
        with open(out_path,"wb") as item:
            total = 0
            while True:
                data = connection.recv(chunk)
                # print(data)
                if b"done" in data:
                    # print(data)
                    idx = data.find(b"done")
                    if idx != -1:
                        remain = data[:idx]
                        item.write(remain)
                        total += len(remain)
                    connection.sendall(b"ok")
                    break
                item.write(data)
                total += len(data)
                    # print(sys.getsizeof(data))
            print(f"recieve: {total} Kbs data" )
    
    def process_message(self, mess)-> str:
        try:
            print(mess)
            if mess.get("type") == "join":
                peer = (mess.get("id"),mess.get("ip"),mess.get("port"))
                self.add_peer(peer)
                response = {
                    "action":"accept join",
                    "result":True,
                }
                return response
            if mess.get("type") == "download":
                # if mess.get("event") == "started":
                ip = mess.get("ip")
                port = mess.get("port")
                metainfo_hash = mess.get("metainfo_hash")
                # parse metainfo from hash of metainfo
                meta_info = self.parse_metainfo(metainfo_hash)
                
                if not meta_info:
                    response = {
                        "action":"error",
                        "error": "tracker does not hold this metainfo"
                    }
                    return response
                # send broadcast to ask all peer in list to find who is keept pieces of this file
                peer_list_response = self.find_peers_hold_Torrent(meta_info)
                response = {
                    "action":"response download",
                    "peers": peer_list_response
                }
                return response
                
                
            if mess.get("type") == "upload":
                id = len(self.peer_list)
                self.add_peer((mess.get("id"),mess.get("ip"), mess.get("port")))
                response = {
                    "action":"response upload",
                    "metainfo_hash": mess.get("metainfo_hash"),
                    "metainfo_name":mess.get("metainfo_name"),
                    "id":id
                }
                return response
            
            if mess.get("type") == "disconnect":
                response = {
                    "action":"disconnect",
                    "id":mess.get("id"),
                    "ip":mess.get("ip"),
                    "port":mess.get("port")
                }
                return response
        except json.JSONDecodeError as e:
            print("Error: Invalid JSON string")
            print(e)
            response ={
                "action": "error",
                "Error": e
            }
            return response
                
    def response_action(self,connection,address,command: dict):
        if (command.get("action") == "response download"):
            self.send_message(connection, command)
            print(f"[TRACKER] Response peer need to contact")
            print(json.dumps(command,indent=4))
            return False
        
        if command.get("action") == "response upload":
            metainfo_hash = command.get("metainfo_hash")
            metainfo_name = command.get("metainfo_name")
            if metainfo_hash in self.metainfo_hashtable:
                response = {
                    "notification": "tracker was contain this metainfo file",
                    "hit": True
                }
                self.send_message(connection, response)
            else:
                response ={
                    "notification":"tracker want to get this metainfo file",
                    "hit": False
                }
                self.send_message(connection, response)
                self.recieve_file(connection,f"{self.metainfo_storage}/{metainfo_name}",chunk=1024)
                self.update_metaifo_hash_table(metainfo_hash,f"{self.metainfo_storage}/{metainfo_name}")
            return False
                
        # self.send_message(connection,"oke")
        if command.get("action") == "accept join":
            if command.get("error"):
                return command
            
            response = {
                "notification": "success" if command.get("result") else "failed",
                "id" : command.get("id")
            }
            self.send_message(connection, response)
            return False
            
        if command.get("action") == "disconnect":
            peer = (command.get("id"),command.get("ip"),command.get("port"))
            print(peer)
            self.remove_peer(peer)
            # connected = False
            return False
            
            
        if command.get("action") == "error":
            self.send_message(connection, command)
            # connected = False
            return False
                
    def find_peers_hold_Torrent(self,metainfo):
        print("[Broadcast] find peers which obtain Torrent pieces in peer list")
        peer_list_for_client = []
        file_name = metainfo.get("info").get("name") 
        # print(self.peer_list)
        for peer in self.peer_list:
            
            print( f"[ASK] Peer {peer} about torren of file { file_name } ")
            client_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_connection.connect((peer[1],peer[2]))
            # client_connection.settimeout(60)
            message = {
                "type": "findTorrent",
                "tracker_id": self.id,
                "file_name": file_name
            }
            
            self.send_message(client_connection, message)
            response = self.recieve_message(client_connection, peer)
            # print(json.dumps(response,indent=4))
            if response.get("hit") == True:
                peer_list_for_client.append({"id":response.get("id"),"ip":response.get("ip"), "port":response.get("port")})
            client_connection.close()
            # except:
            #     print(f"[ASK Timeout] ")
            #     client_connection.close()
        print(peer_list_for_client)
        return peer_list_for_client
                           
####################################################### test ##############################################################
def test_meta_info():    
    tracker = Tracker()  
    message = {
        "info_hash": "62f518eaaff4903ea10163eee1d98e3c7691d1fe",
        "peer_id": 1,
        "port": 4040,
        "event": "started",
        "ip": "192.168.31.119"
    }  
    tracker.process_message(json.dumps(message))
    
def main():
    parser = argparse.ArgumentParser(description='Tracker script')
    parser.add_argument("--ip",type=str,help="tracker ip")
    parser.add_argument("--port",type=int,help="tracker port", default=5050 )
    parser.add_argument("--metainfo-storage",type=str, help="directory hold metainfo", default="metainfo" )
    parser.add_argument("--header-length",type=int, help="header length of message", default=1024 )
    args = parser.parse_args()
    # for key, value in vars(args).items():
    #     print(f"{key}: {value}")
    ip = args.ip
    port = args.port
    metainfo_storage = args.metainfo_storage
    header_length = args.header_length
    
    
    tracker = Tracker(ip= ip,port = port, metainfo_storage= metainfo_storage, header_length= header_length)
    # tracker.start()
    
if __name__ == "__main__":
    main()
    