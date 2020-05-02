import selectors
import socket
import threading
from typing import List
from time import sleep

import numpy as np


class OPCMessage:
    """
    Class for handling OPC messages (http://openpixelcontrol.org/).

    Suppports multiple connections by using selectors.
    Based on https://realpython.com/python-sockets/
    """
    def __init__(self, selector, sock, addr, callback, verbose=False):
        """Constructor

        Arguments:
            selector {[type]} -- Selector to use
            sock {[type]} -- A TCP Socket (from socket.accept())
            addr {[type]} -- Address of the client (from socket.accept())
            callback {function} -- Callback to be called once a message is fully read
        """
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self.callback = callback  # this callback is called once a message is fully read
        self._verbose = verbose
        self._recv_buffer = b""
        self._send_buffer = b""
        self._resetData()

    def _debug(self, message):
        if self._verbose:
            print(message)

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

    def _resetData(self):
        """Reset all state information in order to re-use the message instance"""

        self.opc_header = None
        self._opc_header_len = None
        self.channel = None
        self.message = None
        self.payload_expected = None
        self.messageData = None

    def process_events(self, mask):
        """Main function to handle new events on the selector"""
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            # don't think we need a write event...
            # self.write()
            # Support long connections -> enter read mode again
            self._resetData()
            self._set_selector_events_mask('r')

    def _read(self):
        """Read data from socket and store in self._recv_buffer"""
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError as e:
            print("Error reading from socket: {}".format(e))
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")

    def processOpcHeader(self):
        """Process OPC Header information and strip from self._recv_buffer if successful"""
        hdrlen = 4
        if len(self._recv_buffer) >= hdrlen:
            header = self._recv_buffer[:hdrlen]
            # Store state information
            self.opc_header = header
            self.channel = header[0]
            self.message = header[1]
            self.payload_expected = (header[2] << 8) | header[3]
            # Strip header from buffer
            self._recv_buffer = self._recv_buffer[hdrlen:]

    def processMessageData(self):
        """Process OPC Data part of the message"""
        content_len = self.payload_expected
        if not len(self._recv_buffer) >= content_len:
            return
        self._debug("Message fully read")
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        # Store state information
        self.messageData = data
        # Call the callback
        if self.callback is not None:
            self.callback(data)

    def read(self):
        """Method to handle the read event"""
        self._read()
        run = 0
        # store the callback function
        store_callback = self.callback
        needMoreData = False
        run = 0
        while not needMoreData:
            needMoreData = True

            if self.opc_header is None:
                self.processOpcHeader()

            if self.opc_header:
                if self.messageData is None:
                    self.processMessageData()

            # message successfully read
            if self.opc_header and self.messageData:
                needMoreData = False
                self._resetData()

            # disable callback
            self.callback = None
            if run > 0:
                self._debug("Frame skipped")
            run += 1

        # enable callback again
        self.callback = store_callback

        if self.opc_header and self.messageData:
            # Set selector to listen for write events, we're done reading.
            self._set_selector_events_mask("w")

    def close(self):
        self._debug("closing connection to".format(self.addr))
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print("error: selector.unregister() exception for {}: {}".format(self.addr, repr(e)))

        try:
            self.sock.close()
        except OSError as e:
            print("error: socket.close() exception for {}: {}".format(self.addr, repr(e)))
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None


class ServerThread(object):
    """Thread object to continuously read messages from socket
    """
    def __init__(self, host, port, socket, callback, verbose=False):
        """Constructor for thread object

        Arguments:
            socket {[type]} -- Socket to connect (must be in listening state)
            callback {function} -- Callback to call when OPC messages have been fully read
        """
        self._host = host
        self._port = port
        self._socket = socket
        self._callback = callback
        self._thread = None  # type: threading.Thread
        self._stopSignal = None
        self._verbose = verbose
        self.sel = selectors.DefaultSelector()

    def _debug(self, message):
        if self._verbose:
            print(message)

    def start(self):
        """Start the server thread"""
        if self._thread is not None:
            return

        self._stopSignal = False
        self._socket.listen()
        print("FadeCandy Server thread listening.")
        self._thread = threading.Thread(target=self._process_thread, args=[self._socket, self._callback])
        self._thread.daemon = True
        self._thread.start()

    def stop(self, timeout=1):
        """Stop the server thread
        Raises TimeoutError """
        self._stopSignal = True
        self._thread.join(timeout=timeout)
        if self._thread.isAlive():
            raise TimeoutError("thread.join timed out")

    def isAlive(self):
        """Check whether the thread is alive.
        Alive means that the background thread is running.
        If the socket is closed, the background thread will exit
        """
        if self._thread is None:
            return False
        if not self._thread.isAlive():
            return False
        return True

    def isConnected(self):
        """Check wether there is an active connection
        """
        try:
            self._socket.getpeername()
            return True
        except Exception as e:
            print("Error getting peername: {}".format(e))
            return False

    def getHost(self):
        return self._host

    def getPort(self):
        return self._port

    def _accept_wrapper(self, sock, callback):
        conn, addr = sock.accept()  # Should be ready to read
        self._debug("accepted connection from {}".format(addr))
        conn.setblocking(False)
        message = OPCMessage(self.sel, conn, addr, callback)
        self.sel.register(conn, selectors.EVENT_READ, data=message)

    def _process_thread(self, lsock, callback):
        # Method to run in background thread
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        self._debug("FadeCandy Server: Background thread started")
        try:
            while not self._stopSignal:
                # For error handling: unregister and register again so we can detect closed sockets
                # Don't know if this can be done better...
                self.sel.unregister(lsock)
                self.sel.register(lsock, selectors.EVENT_READ, data=None)

                # Use timeout in order to periodically check stop signal
                events = self.sel.select(timeout=0.1)
                for key, mask in events:
                    if key.data is None:
                        self._accept_wrapper(key.fileobj, callback)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception as e:
                            message.close()
                            self._debug("FadeCandy Server: Background thread exiting due to message exception: {}".format(e))
                            self._stopSignal = True
        except Exception as e:
            self._debug("FadeCandy Server: Background thread exiting due to exception: {}".format(e))
        finally:
            self._debug("FaceCandy Server: Background thread closing socket")
            self.sel.close()
            self._socket.close()


class Server(object):

    # Using static methods here since sockets can be used only once
    sockets = []  # type: List[socket.socket]
    all_threads = []  # type: List[ServerThread]

    def __init__(self, host, port, verbose=True):
        self._host = host
        self._port = port
        self._socket = None  # type: socket.socket
        self._thread = None
        self._lastMessage = None
        self._verbose = verbose

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

    def _get_threads(self, host, port):
        """
        Returns sockets with same host and port.
        """
        sameThreads = []
        for thread in self.all_threads:
            if thread.getPort() == port and thread.getHost() == host and thread is not self._thread:
                sameThreads.append(thread)
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
            print("FadeCandy Server begin listening on {}:{}".format(self._host, self._port))
            self._thread = ServerThread(self._host, self._port, _socket, self._pixelCallback, self._verbose)
            self.all_threads.append(self._thread)
            self._thread.start()
            return True
        except socket.error as e:
            print("FadeCandy Server error listening on {}:{}".format(self._host, self._port))
            print(e)
            self._socket = None
            return False

    def _pixelCallback(self, data):
        # Transform byte array to pixel shape
        array = np.frombuffer(data, dtype=np.uint8)
        # make sure array can be reshaped
        # size = int(int(len(array)/3)*3)
        # array = array[:size]
        try:
            pixels = array.reshape((-1, 3)).T
            self._lastMessage = pixels
        except Exception as e:
            print("Error decoding to pixels. array length: {}, error: {}".format(len(array), e))

    def get_pixels(self, block=False):
        isListening = self._ensure_listening()
        if not isListening:
            raise Exception("Server cannot listen")
        if block:
            while self._lastMessage is None:
                print("Waiting for message...")
                sleep(0.01)
        return self._lastMessage
