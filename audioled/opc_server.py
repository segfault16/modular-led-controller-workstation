import socket
from time import sleep
import threading
import selectors
import traceback
import struct
import numpy as np

sel = selectors.DefaultSelector()

class OPCMessage:
    def __init__(self, selector, sock, addr, callback):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.callback = callback # this callback is called once a message is fully read
        self.resetData()
    
    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError("Invalid events mask mode {}".format(mode))
        self.selector.modify(self.sock, events, data=self)

    def resetData(self):
        self._recv_buffer = b""
        self._send_buffer = b""
        self.opc_header = None
        self._opc_header_len = None
        self.channel = None
        self.message = None
        self.payload_expected = None
        self.messageData = None

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            # don't think we need a write event...
            #self.write()
            # Support long connections -> enter read mode again
            self.resetData()
            self._set_selector_events_mask('r')

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def processOpcHeader(self):
        hdrlen = 4
        #print("processing header... buffer size: {}".format(len(self._recv_buffer)))
        if len(self._recv_buffer) >= hdrlen:
            #print("Can process header")
            header = self._recv_buffer[:hdrlen]
            self.opc_header = header
            self.channel = header[0]
            self.message = header[1]
            self.payload_expected = (header[2] << 8) | header[3]
            # Strip header from buffer
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def processMessageData(self):
        content_len = self.payload_expected
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        self.messageData = data

        if self.callback is not None:
            self.callback(data)
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")
        

    def read(self):
        self._read()

        
        if self.opc_header is None:
                self.processOpcHeader()

        if self.opc_header:
            if self.messageData is None:
                self.processMessageData()

    def close(self):
        print("closing connection to", self.addr)
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                "error: selector.unregister() exception for {}: {}".format(self.addr, repr(e))
            )

        try:
            self.sock.close()
        except OSError as e:
            print(
                "error: socket.close() exception for {}: {}".format(self.addr, repr(e))
            )
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None
    

def accept_wrapper(sock, callback):
    conn, addr = sock.accept()  # Should be ready to read
    #print("accepted connection from", addr)
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
        self._lastMessage = None

    

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

    def _pixelCallback(self, data):
        #print("Callback received: {}".format(data))
        pixels = np.frombuffer(data,dtype=np.uint8).reshape((-1,3)).T
        #print("Pixels are: {}".format(pixels))
        self._lastMessage = pixels

    def get_pixels(self, block=False):
        isListening = self._ensure_listening()
        if not isListening:
            raise Exception("Server cannot listen")
        if block:
            while self._lastMessage is None:
                print("Waiting for message...")
                sleep(0.01)
        return self._lastMessage