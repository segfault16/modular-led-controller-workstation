import socket
from time import sleep
import threading
import selectors
import traceback

sel = selectors.DefaultSelector()

class OPCMessage:
    def __init__(self, selector, sock, addr, callback):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.callback = callback # this callback is called once a message is fully read
        self._recv_buffer = b""
        self._send_buffer = b""
    
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
    def read(self):
        self._read()
    

def accept_wrapper(sock, callback):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    message = OPCMessage(sel, conn, addr, callback)
    sel.register(conn, selectors.EVENT_READ, data=message)

def _process_thread(lsock, callback):
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    print("FadeCandy Server: Background thread started")
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj, callback)
                else:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        message.close()
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()

class Server(object):
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._socket = None
        self._thread = None

    

    def _ensure_listening(self):
        if self._socket:
            return True
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.bind((self._host, self._port))
            self._socket.listen()
            print("FadeCandy Server listening on {}:{}".format(self._host, self._port))
            self._thread = threading.Thread(target=_process_thread, args=[self._socket, self._pixelCallback])
            self._thread.daemon = True
            self._thread.start()
            return True
        except socket.error as e:
            print("FadeCandy Server error listening on {}:{}".format(self._host, self._port))
            print(e)
            self._socket = None
            return False

    def get_pixels(self):
        isListening = self._ensure_listening()
        if not isListening:
            raise Exception("Server cannot listen")

        conn, addr = self._socket.accept()
        with conn:
            print("")