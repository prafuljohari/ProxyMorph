#!/bin/sh -
"exec" "python" "-O" "$0" "$@"

import threading
import BaseHTTPServer, select, socket, SocketServer, urlparse, base64, time, ssl


proxy_user_pass = "Some_User:Some_Pass"



class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    __base = BaseHTTPServer.BaseHTTPRequestHandler
    __base_handle = __base.handle

    rbufsize = 4096
    verbosity = 0

    def handle(self):
        (ip, port) =  self.client_address
        if hasattr(self, 'allowed_clients') and ip not in self.allowed_clients:
            self.raw_requestline = self.rfile.readline()
            if self.parse_request(): self.send_error(403)
        else:
            self.__base_handle()




    def _connect_to(self, netloc, soc):


        #This proxy host refers to normal request i.e. requests other than HTTPS connect requests
        
        try: soc.connect(self.proxy_tuple)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return 0
        return 1




    def do_CONNECT(self):

        if self.verbosity >= 1:
            self.log_request()

        CONNECT = "CONNECT %s HTTP/1.0\r\n" % (self.path)

        if self.isAuth:
            CONNECT += self.encoded_user_pass

        CONNECT += "Connection: close\r\n\r\n"

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            s.connect(self.proxy_tuple)
        except socket.error:
            s.close()
            return 1
        s.send(CONNECT)
            
        data = s.recv(4096)

        if self.verbosity >=2:
            print "Proxy response for a connect request: "
            print data                  #Should get a 200
            
        if data:
            try:
                confirm = "HTTP/1.0 200 Connection established\r\n\r\n"
                self.connection.send(confirm)
                s.recv(4096)
                #s = ssl.wrap_socket(s, server_side=False, do_handshake_on_connect=True, ssl_version=ssl.PROTOCOL_TLSv1)

                browserResp = self.connection.recv(4096)
                while browserResp:
                    s.send(browserResp)
                    browserResp = self.connection.recv(4096)

                webResp = s.recv(16)
                while webResp:
                    self.connection.send(webResp)
                    webResp = s.recv(16)

                #self._read_write(s, 100)
                
            finally:
                if self.verbosity >= 3:
                    print "\t" "End of connect request"
                s.close()
                self.connection.close()




    def do_GET(self):
        
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(self.path)
        if (scm != 'http' and scm != 'https') or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            if self._connect_to(netloc, soc):
                if self.verbosity == 1:
                    self.log_request()
                soc.send("%s %s %s\r\n" % (
                    self.command,
                    self.path,
                    self.request_version))

                self.headers['Connection'] = 'Keep-Alive'
                #del self.headers['Proxy-Connection']
                for key_val in self.headers.items():
                    soc.send("%s: %s\r\n" % key_val)

                if self.isAuth:
                    soc.send(self.encoded_user_pass)
                soc.send("\r\n")
                self._read_write(soc)
        finally:
            if self.verbosity >= 3:
                print "\t" "bye"
            #soc.close()
            self.connection.close()





    def _read_write(self, soc, max_idling=20):
        iw = [self.connection, soc]
        ow = []
        count = 0
        while 1:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 3)
            if exs: break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc

                    try:
                        if i == soc:
                            data = i.recv(4096)
                        else:
                            data = i.recv(1024)
                    except socket.error, arg:
                        continue
                    
                    if data:
                        if self.verbosity >= 2:
                            print "Browser data is : "
                            print data
                        if data != "":
                            try:
                                out.send(data)
                            except socket.error, arg:
                                if out == soc:
                                    print "Proxy receive error\n"
                                else:
                                    print "Output to Browser is faulty?\n"
                            
                        count = 0
            else:
                pass
            if count == max_idling: break
    
    do_HEAD     =   do_GET
    do_POST     =   do_GET
    do_PUT      =   do_GET
    do_DELETE   =   do_GET

class ThreadedHTTPServer (SocketServer.ThreadingMixIn,
                           BaseHTTPServer.HTTPServer): pass


class ProxyObject:
    def __init__(self, proxy_host, proxy_port, isAuth, username=None, password=None):
        self.proxyHost = proxy_host
        self.proxyPort = proxy_port
        self.proxy_tuple = (proxy_host, proxy_port)
        self.isAuth = isAuth
        if isAuth:
            self.encoded_user_pass = "Proxy-Authorization: Basic " + base64.encodestring(username + ":" + password) + "\r\n"
        else:
            self.encoded_user_pass = ""


def setupParameters():
    allowed = ["10.9.11.13", "172.16.27.25"]
    ProxyHandler.allowed_clients = allowed

    A = ProxyObject("172.16.27.25", 7995, False)
    B = ProxyObject("202.141.80.22", 3128, True, "username", "password")

    defaultProxy = B

    ProxyHandler.proxyList = [A,B]

    ProxyHandler.proxy_host = defaultProxy.proxyHost
    ProxyHandler.proxy_port = defaultProxy.proxyPort
    ProxyHandler.proxy_tuple = defaultProxy.proxy_tuple
    ProxyHandler.isAuth = defaultProxy.isAuth

    ProxyHandler.encoded_user_pass = defaultProxy.encoded_user_pass
    

def timedProxySelect():
    timeout = 3
    for x in ProxyHandler.proxyList:
        print x.proxyHost, x.proxyPort, "\n"

    print "Enter the proxy which you want to select:",
    rlist, _, _ = select([sys.stdin], [], [], timeout)
    if rlist:
        s = sys.stdin.readline()
        print s
    else:
        print "No input. Moving on..."

class AsyncTest(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.port = port

    def run(self):
        testSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSocket.connect(('172.16.27.25', port))

        time.sleep(2)

        testHeader = "GET http://www.google.com HTTP/1.1\r\n\r\n"
        testSocket.send(testHeader)
        sockResponse = testSocket.recv(4096)

        result = testSocket.recv(4096)

        if result[:6] == "<HTML>":
            print "Proxy working successfully. Enjoy"
        else:
            print "No response from proxy. Check the settings again"

if __name__ == '__main__':
    setupParameters()
    port = 8080
    server = ThreadedHTTPServer(('', port), ProxyHandler)
    print 'Starting web server on port: ' + str(port) + ". Use kill.py to stop the server."
    async = AsyncTest(port)
    async.start()
    server.serve_forever()