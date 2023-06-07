import sys
import os
import json
import uuid
import logging
from queue import  Queue
import threading 
import socket

class RealmThread(threading.Thread):
    def __init__(self, chats, realm_address, realm_port):
        self.chats = chats
        self.chat = {}
        self.realm_address = realm_address
        self.realm_port = realm_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.realm_address, self.realm_port))
        threading.Thread.__init__(self)
    def sendstring(self,string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                print("diterima dari server",data)
                if (data):
                    receivemsg = "{}{}" . format(receivemsg,data.decode())
                    if receivemsg[-4:]=='\r\n\r\n':
                        print("end of string")
                        return json.loads(receivemsg)
        except:
            self.sock.close()
            return { 'status' : 'ERROR', 'message' : 'Gagal'}
    
    def put(self, message):
        dest = message['msg_to']
        try:
            self.chat[dest].put(message)
        except KeyError:
            self.chat[dest]=Queue()
            self.chat[dest].put(message)

class Chat:
    def __init__(self):
        self.sessions={}
        self.users = {}
        self.users['messi']={ 'nama': 'Lionel Messi', 'negara': 'Argentina', 'password': 'surabaya', 'incoming' : {}, 'outgoing': {}}
        self.users['henderson']={ 'nama': 'Jordan Henderson', 'negara': 'Inggris', 'password': 'surabaya', 'incoming': {}, 'outgoing': {}}
        self.users['lineker']={ 'nama': 'Gary Lineker', 'negara': 'Inggris', 'password': 'surabaya','incoming': {}, 'outgoing':{}}
        self.realms = {}
    def proses(self,data):
        j=data.split(" ")
        try:
            command=j[0].strip()
            if (command=='auth'):
                username=j[1].strip()
                password=j[2].strip()
                logging.warning("AUTH: auth {} {}" . format(username,password))
                return self.autentikasi_user(username,password)
            elif (command=='realm'):
                realmid = j[1].strip()
                if realmid in self.realms:
                    return self.realms[realmid].proses(" ".join(j[2:]))
                else:
                    return {'status': 'ERROR', 'message': 'Realm Tidak Ada'}
            elif (command=='addrealm'):
                realmid = j[1].strip()
                realm_address = j[2].strip()
                realm_port = int(j[3].strip())
                return self.add_realm(realmid, realm_address, realm_port, data)
            elif (command=='recvrealm'):
                realmid = j[1].strip()
                realm_address = j[2].strip()
                realm_port = int(j[3].strip())
                return self.recv_realm(realmid, realm_address, realm_port, data)
            elif (command=='send'):
                sessionid = j[1].strip()
                usernameto = j[2].strip()
                message=""
                for w in j[3:]:
                    message="{} {}" . format(message,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernameto))
                return self.send_message(sessionid,usernamefrom,usernameto,message)
            elif (command=='sendgroup'):
                sessionid = j[1].strip()
                usernamesto = j[2].strip().split(',')
                message=""
                for w in j[3:]:
                    message="{} {}" . format(message,w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SEND: session {} send message from {} to {}" . format(sessionid, usernamefrom,usernamesto))
                return self.send_group_message(sessionid,usernamefrom,usernamesto,message)
            elif (command == 'sendrealm'):
                sessionid = j[1].strip()
                realmid = j[2].strip()
                usernameto = j[3].strip()
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                print(message)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDREALM: session {} send message from {} to {} in realm {}".format(sessionid, usernamefrom, usernameto, realmid))
                return self.send_realm_message(sessionid, realmid, usernamefrom, usernameto, message, data)
            elif (command == 'recvrealmmsg'):
                usernamefrom = j[1].strip()
                realmid = j[2].strip()
                usernameto = j[3].strip()
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                print(message)
                logging.warning("RECVREALMMSG: recieve message from {} to {} in realm {}".format( usernamefrom, usernameto, realmid))
                return self.recv_realm_message(realmid, usernamefrom, usernameto, message, data)
            elif (command == 'sendgrouprealm'):
                sessionid = j[1].strip()
                realmid = j[2].strip()
                usernamesto = j[3].strip().split(',')
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w)
                usernamefrom = self.sessions[sessionid]['username']
                logging.warning("SENDGROUPREALM: session {} send message from {} to {} in realm {}".format(sessionid, usernamefrom, usernamesto, realmid))
                return self.send_group_realm_message(sessionid, realmid, usernamefrom,usernamesto, message,data)
            elif (command == 'recvrealmgroupmsg'):
                usernamefrom = j[1].strip()
                realmid = j[2].strip()
                usernamesto = j[3].strip().split(',')
                message = ""
                for w in j[4:]:
                    message = "{} {}".format(message, w) 
                logging.warning("RECVGROUPREALM: send message from {} to {} in realm {}".format(usernamefrom, usernamesto, realmid))
                return self.recv_group_realm_message(realmid, usernamefrom,usernamesto, message,data)
            elif (command=='inbox'):
                sessionid = j[1].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("INBOX: {}" . format(sessionid))
                return self.get_inbox(username)
            elif (command == 'realminbox'):
                sessionid = j[1].strip()
                realmid = j[2].strip()
                username = self.sessions[sessionid]['username']
                logging.warning("REALMINBOX: {} from realm {}".format(sessionid, realmid))
                return self.get_realm_inbox(username, realmid)
            elif (command == 'getrealmchat'):
                realmid = j[1].strip()
                username = j[2].strip()
                logging.warning("GETREALMCHAT: from realm {}".format(realmid))
                return self.get_realm_chat(realmid, username)
            elif (command=='logout'):
                return  self.logout()
            elif (command=='info'):
                return self.info()
            else:
                print(command)
                return {'status': 'ERROR', 'message': '**Protocol Tidak Benar'}
        except KeyError:
            return { 'status': 'ERROR', 'message' : 'Informasi tidak ditemukan'}
        except IndexError:
            return {'status': 'ERROR', 'message': '--Protocol Tidak Benar'}

    def autentikasi_user(self,username,password):
        if (username not in self.users):
            return { 'status': 'ERROR', 'message': 'User Tidak Ada' }
        if (self.users[username]['password']!= password):
            return { 'status': 'ERROR', 'message': 'Password Salah' }
        tokenid = str(uuid.uuid4()) 
        self.sessions[tokenid]={ 'username': username, 'userdetail':self.users[username]}
        return { 'status': 'OK', 'tokenid': tokenid }

    def get_user(self,username):
        if (username not in self.users):
            return False
        return self.users[username]

    def add_realm(self, realmid, realm_address, realm_port, data):
        j = data.split()
        j[0] = "recvrealm"
        data = ' '.join(j)
        data += "\r\n"
        if realmid in self.realms:
            return {'status': 'ERROR', 'message': 'Realm sudah ada'}
          
        self.realms[realmid] = RealmThread(self, realm_address, realm_port)
        result = self.realms[realmid].sendstring(data)
        return result

    def recv_realm(self, realmid, realm_address, realm_port, data):
        self.realms[realmid] = RealmThread(self, realm_address, realm_port)
        return {'status':'OK'}

    def send_message(self,sessionid,username_from,username_dest,message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)

        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}

        message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
        outqueue_sender = s_fr['outgoing']
        inqueue_receiver = s_to['incoming']
        try:	
            outqueue_sender[username_from].put(message)
        except KeyError:
            outqueue_sender[username_from]=Queue()
            outqueue_sender[username_from].put(message)
        try:
            inqueue_receiver[username_from].put(message)
        except KeyError:
            inqueue_receiver[username_from]=Queue()
            inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'Message Sent'}

    def send_realm_message(self, sessionid, realmid, username_from, username_dest, message, data):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if (realmid not in self.realms):
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
        self.realms[realmid].put(message)
        
        j = data.split()
        j[0] = "recvrealmmsg"
        j[1] = username_from
        data = ' '.join(j)
        data += "\r\n"
        self.realms[realmid].sendstring(data)
        return {'status': 'OK', 'message': 'Message Sent to Realm'}

    def recv_realm_message(self, realmid, username_from, username_dest, message, data):
        if (realmid not in self.realms):
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        s_to = self.get_user(username_dest)
        if (s_fr==False or s_to==False):
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        message = { 'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
        self.realms[realmid].put(message)
        return {'status': 'OK', 'message': 'Message Sent to Realm'}

    def send_group_realm_message(self, sessionid, realmid, username_from, usernames_to, message, data):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        if realmid not in self.realms:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
            self.realms[realmid].put(message)
        
        j = data.split()
        j[0] = "recvrealmgroupmsg"
        j[1] = username_from
        data = ' '.join(j)
        data +="\r\n"
        self.realms[realmid].sendstring(data)
        return {'status': 'OK', 'message': 'Message Sent to Group in Realm'}


    def recv_group_realm_message(self, realmid, username_from, usernames_to, message, data):
        if realmid not in self.realms:
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        for username_to in usernames_to:
            s_to = self.get_user(username_to)
            message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message }
            self.realms[realmid].put(message)
        return {'status': 'OK', 'message': 'Message Sent to Group in Realm'}

    def send_group_message(self, sessionid, username_from, usernames_dest, message):
        if (sessionid not in self.sessions):
            return {'status': 'ERROR', 'message': 'Session Tidak Ditemukan'}
        s_fr = self.get_user(username_from)
        if s_fr is False:
            return {'status': 'ERROR', 'message': 'User Tidak Ditemukan'}
        for username_dest in usernames_dest:
            s_to = self.get_user(username_dest)
            if s_to is False:
                continue
            message = {'msg_from': s_fr['nama'], 'msg_to': s_to['nama'], 'msg': message}
            outqueue_sender = s_fr['outgoing']
            inqueue_receiver = s_to['incoming']
            try:    
                outqueue_sender[username_from].put(message)
            except KeyError:
                outqueue_sender[username_from]=Queue()
                outqueue_sender[username_from].put(message)
            try:
                inqueue_receiver[username_from].put(message)
            except KeyError:
                inqueue_receiver[username_from]=Queue()
                inqueue_receiver[username_from].put(message)
        return {'status': 'OK', 'message': 'Message Sent'}


    def get_inbox(self,username):
        s_fr = self.get_user(username)
        incoming = s_fr['incoming']
        msgs={}
        for users in incoming:
            msgs[users]=[]
            while not incoming[users].empty():
                msgs[users].append(s_fr['incoming'][users].get_nowait())
        return {'status': 'OK', 'messages': msgs}

    def get_realm_inbox(self, username,realmid):
        if (realmid not in self.realms):
            return {'status': 'ERROR', 'message': 'Realm Tidak Ditemukan'}
        s_fr = self.get_user(username)
        result = self.realms[realmid].sendstring("getrealmchat {} {}\r\n".format(realmid, username))
        return result
    def get_realm_chat(self, realmid, username):
        s_fr = self.get_user(username)
        msgs = []
        while not self.realms[realmid].chat[s_fr['nama']].empty():
            msgs.append(self.realms[realmid].chat[s_fr['nama']].get_nowait())
        return {'status': 'OK', 'messages': msgs}
    def logout(self):
        if (bool(self.sessions) == True):
            self.sessions.clear()
            return {'status': 'OK'}
        else:
            return {'status': 'ERROR', 'message': 'Belum Login'}
    def info(self):
        return {'status': 'OK', 'message': self.sessions}

if __name__=="__main__":
    j = Chat()
    sesi = j.proses("auth messi surabaya")
    print(sesi)
    #sesi = j.autentikasi_user('messi','surabaya')
    #print sesi
    tokenid = sesi['tokenid']
    print(j.proses("send {} henderson hello gimana kabarnya son " . format(tokenid)))
    print(j.proses("send {} messi hello gimana kabarnya mess " . format(tokenid)))

    #print j.send_message(tokenid,'messi','henderson','hello son')
    #print j.send_message(tokenid,'henderson','messi','hello si')
    #print j.send_message(tokenid,'lineker','messi','hello si dari lineker')


    print("isi mailbox dari messi")
    print(j.get_inbox('messi'))
    print("isi mailbox dari henderson")
    print(j.get_inbox('henderson'))

    #print(j.proses("addrealm realm1 127.0.0.1 8889"))
    #print(j.proses("sendrealm {} realm1 henderson hello gimana kabarnya son " . format(tokenid)))
    #print(j.proses("getrealminbox {} realm1" . format(tokenid)))
