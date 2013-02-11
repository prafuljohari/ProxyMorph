#!/bin/sh -
"exec" "python" "-O" "$0" "$@"

import BaseHTTPServer, select, socket, SocketServer, urlparse, base64


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

        proxy_host = "202.141.80.22"
        proxy_port = "3128"
        
        host_port = proxy_host, int(proxy_port)
        
        try: soc.connect(host_port)
        except socket.error, arg:
            try: msg = arg[1]
            except: msg = arg
            self.send_error(404, msg)
            return 0
        return 1




    def do_CONNECT(self):

        if self.verbosity >= 1:
            self.log_request()
        PROXY_ADDR = ("172.16.27.25", 7997)
        CONNECT = "CONNECT %s HTTP/1.0\r\n\r\n" % (self.path)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            s.connect(PROXY_ADDR)
        except socket.error:
            s.close()
            return 1
        s.send(CONNECT)
            
        data = s.recv(4096)
        if self.verbosity >=2:
            print "Proxy response: "
            print data
            
        if data:
            try:
                confirm = "HTTP/1.0 200 Connection established\r\n\r\n"
                self.connection.send(confirm)
                self._read_write(s, 100)
                
            finally:
                if self.verbosity >= 3:
                    print "\t" "byeHttps"
                s.close()
                self.connection.close()




    def do_GET(self):
        
        (scm, netloc, path, params, query, fragment) = urlparse.urlparse(self.path)
        if (scm != 'http' and scm != 'https') or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        encoded_user_pass=base64.encodestring(proxy_user_pass)
        
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
                proxy_auth = "Proxy-Authorization: Basic " + str(encoded_user_pass) + "\r\n"
                soc.send(proxy_auth)
                soc.send("\r\n")
                self._read_write(soc)
        finally:
            if self.verbosity >= 3:
                print "\t" "bye"
            #soc.close()
            self.connection.close()





    def _read_write(self, soc, max_idling=20, https=False):
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
                            data = i.recv(40960)
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
                                    print "Socket to proxy is the culprit!\n"
                                else:
                                    print "Browser!! How come?\n"
                            
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

if __name__ == '__main__':
    '''
    from sys import argv
    if argv[1:] and argv[1] in ('-h', '--help'):
        print argv[0], "[port [allowed_client_name ...]]"
    else:
        if argv[2:]:
            allowed = []
            for name in argv[2:]:
                client = socket.gethostbyname(name)
                allowed.append(client)
                print "Accept: %s (%s)" % (client, name)
            del argv[2:]
        else:
            print "All clients will be allowed to connect..."
        '''
    allowed = ["10.9.11.13", "172.16.27.25"]
    ProxyHandler.allowed_clients = allowed
    port = 8000
    server = ThreadedHTTPServer(('', port), ProxyHandler)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()
