import socket
from time import sleep
import threading
import selectors
import traceback
import struct
import numpy as np



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
        #print("closing connection to", self.addr)
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
    





class ServerThread(object):
    def __init__(self, socket, callback):
        self._socket = socket
        self._callback = callback
        self._thread = None
        self._stopSignal = None
        self.sel = selectors.DefaultSelector()
    
    def start(self):
        if self._thread is not None:
            return
        
        self._stopSignal = False
        self._thread = threading.Thread(target=self._process_thread, args=[self._socket, self._callback])
        self._thread.daemon = True
        self._thread.start()
    
    def stop(self):
        self._stopSignal = True
        self._thread.join(timeout=1)

    def isAlive(self):
        # Hard to find out :)
        # ToDo: Implement
        return True

    def accept_wrapper(self, sock, callback):
        conn, addr = sock.accept()  # Should be ready to read
        #print("accepted connection from", addr)
        conn.setblocking(False)
        message = OPCMessage(self.sel, conn, addr, callback)
        self.sel.register(conn, selectors.EVENT_READ, data=message)

    def _process_thread(self, lsock, callback):
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        print("FadeCandy Server: Background thread started")
        try:
            while not self._stopSignal:
                #print('Process')
                events = self.sel.select(timeout=0.1)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj, callback)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            message.close()
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            print("Closing socket")
            self.sel.close()
            self._socket.close()
        


class Server(object):

    # Using static methods here since sockets can be used only once
    sockets = []
    all_threads = []

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._socket = None
        self._thread = None
        self._lastMessage = None

    def __del__(self):
        # Destructors in python... I'm never complaining about C++ again...

        # Basically this thing is (maybe) called at some point, 
        # except if anyone manages to build cyclic references.
        if self._thread is not None:
            self._stopThread()
    
    def _stopThread(self):
        # Stopping gracefully...
        # ToDo: Error handling
        self._thread.stop()
        if self._thread in self.all_threads:
            self.all_threads.remove(self._thread)

    def stop(self):
        self._stopThread()
    
    def _clean_threads(self):
        toCleanup = []
        for thread in self.all_threads:
            try:
                thread._socket.getpeername()
            except:
                toCleanup.append(thread)
        
        for thread in toCleanup:
            # ToDo: Error handling
            print("Cleaning up stale thread")
            thread.stop()
            self.all_threads.remove(thread)
            
    def _get_threads(self, host, port):
        """
        Returns sockets with same host and port.
        """
        self._clean_threads()
        sameThreads = []
        for thread in self.all_threads:
            try:
                (host, port) = thread._socket.getpeername()
                if host == host and port == port:
                    sameThreads.append(thread)
            except:
                pass
        
        return sameThreads

    def _ensure_listening(self):
        # We want to ensure that anyone who expects pixel information gets the data.
        # Due to garbage collection and timing issues a corresponding thread for the same host and port
        # may still be active and the socket may still be bound
        if self._thread and self._thread.isAlive():
            return True
        try:
            same_socket_threads = self._get_threads(self._host, self._port)
            for thread in same_socket_threads:
                thread.stop()
                self.all_threads.remove(thread)
            
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _socket.bind((self._host, self._port))
            _socket.listen()
            print("FadeCandy Server listening on {}:{}".format(self._host, self._port))
            self._thread = ServerThread(_socket, self._pixelCallback)
            self.all_threads.append(self._thread)
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