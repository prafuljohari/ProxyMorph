import socket     #import the socket library
import base64

proxy_auth = "Proxy-Authorization: Basic "+base64.encodestring("username:password")
PROXY_ADDR = ("202.141.80.22", 3128)


##let's set up some constants
HOST = ''    #we are the host
PORT = 8000    #arbitrary port not currently in use
ADDR = (HOST,PORT)    #we need a tuple for the address
BUFSIZE = 4096    #reasonably sized buffer for data
 
serv = socket.socket( socket.AF_INET,socket.SOCK_STREAM)    
 

serv.bind((ADDR))    #the double parens are to create a tuple with one element
serv.listen(5)    #5 is the maximum number of queued connections we'll allow

while(1):
    conn,addr = serv.accept()

    data = conn.recv(BUFSIZE)
    data_new = data.split()
    #print data
    if data_new[0] == 'CONNECT':
        data = data[:-2]
        data = data + proxy_auth + '\r\n\r\n'
        #print data
        sock = socket.socket( socket.AF_INET,socket.SOCK_STREAM)
        sock.connect(PROXY_ADDR)
        sock.send(data)
        new_data = sock.recv(BUFSIZE)
        print new_data, data_new[1]
        data= new_data
        while(data):
            data = conn.recv(BUFSIZE)
            sock.send(data)
            data = sock.recv(BUFSIZE)
            conn.send(data)
    
        
