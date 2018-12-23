import unittest
from audioled import opc_server
from audioled import opc
import numpy as np
import time
import random
import socket


class Test_OPC_Server(unittest.TestCase):
    def test_serverReceives(self):
        # create server
        server = opc_server.Server('127.0.0.1', 7891)
        # start receiving without blocking
        server.get_pixels(block=False)

        # construct client
        client = opc.Client('127.0.0.1:7891',long_connection=True)

        # transfer some data
        for i in range(2):
            pixels_in = np.array([[random.randint(0,255),random.randint(0,255),random.randint(0,255)] for i in range(10)]).T.clip(0,255)
            print("Pixels sent: {}".format(pixels_in))
            client.put_pixels(pixels_in.T.clip(0, 255).astype(int).tolist())
            # give some time for networking
            time.sleep(0.1)
            # receive again (this will return last_message)
            pixels_out = server.get_pixels(block=False)
            # assert in and out are equal
            print("Pixels received: {}".format(pixels_out))
            np.testing.assert_array_equal(pixels_in, pixels_out)

    def test_serverClosesSocket(self):
        # create server
        server = opc_server.Server('127.0.0.1', 7892)
        # start receiving
        server.get_pixels(block=False)

        # construct client
        client = opc.Client('127.0.0.1:7892', long_connection=True, verbose=False)

        # transfer some data
        pixels_in = np.array([[random.randint(0,255),random.randint(0,255),random.randint(0,255)] for i in range(10)]).T.clip(0,255)
        client.put_pixels(pixels_in.T.clip(0, 255).astype(int).tolist())
        time.sleep(0.1)
        # receive again (this will return last_message)
        pixels_out = server.get_pixels(block=False)
        # assert in and out are equal
        print("Pixels received: {}".format(pixels_out))
        np.testing.assert_array_equal(pixels_in, pixels_out)

        # now close server, we need the socket to be closed as well
        server = None
        time.sleep(1)
        print("Proceeding")
        # start new server on the same port
        newServer = opc_server.Server('127.0.0.1', 7892)
        # start receiving
        newServer.get_pixels(block=False)
        # transfer some data
        pixels_in = np.array([[random.randint(0,255),random.randint(0,255),random.randint(0,255)] for i in range(10)]).T.clip(0,255)
        # needs range since client realizes at some point that he's disconnected
        for i in range(10):
            client.put_pixels(pixels_in.T.clip(0, 255).astype(int).tolist())
            time.sleep(0.01)
        # receive again (this will return last_message)
        pixels_out = newServer.get_pixels(block=False)
        # assert in and out are equal
        print("Pixels received: {}".format(pixels_out))
        np.testing.assert_array_equal(pixels_in, pixels_out)

    def test_backgroundThreadExitsIfSocketIsClosed(self):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _socket.bind(('127.0.0.1', 7890))
        thread = opc_server.ServerThread(_socket, None, verbose=True)
        thread.start()
        self.assertTrue(thread.isAlive)
        time.sleep(1)
        _socket.close()
        time.sleep(1)
        self.assertTrue(not thread.isAlive())

    def test_serverErrorHandlingSameSocket(self):
        # create servers
        serverA = opc_server.Server('127.0.0.1', 7892, verbose=True)
        serverB = opc_server.Server('127.0.0.1', 7892, verbose=True)

        # create client
        client = opc.Client('127.0.0.1:7892', long_connection=True, verbose=False)
        # Run for some time...
        for i in range(10):
            # init serverA thread
            print("Activating serverA")
            serverA.get_pixels(block=False)
            pixels_in = np.array([[random.randint(0,255),random.randint(0,255),random.randint(0,255)] for i in range(10)]).T.clip(0,255)
            for j in range(5):
                client.put_pixels(pixels_in.T.clip(0, 255).astype(int).tolist())
                time.sleep(0.1)

            pixels_out = serverA.get_pixels(block=False)
            print("Checking output serverA")
            np.testing.assert_array_equal(pixels_in, pixels_out)
                
            time.sleep(0.1)
            # init serverB thread
            print("Activating serverB")
            serverB.get_pixels(block=False)
            pixels_in = np.array([[random.randint(0,255),random.randint(0,255),random.randint(0,255)] for i in range(10)]).T.clip(0,255)
            for j in range(5):
                client.put_pixels(pixels_in.T.clip(0, 255).astype(int).tolist())
                time.sleep(0.1)

            pixels_out = serverB.get_pixels(block=False)
            print("Checking output serverB")
            np.testing.assert_array_equal(pixels_in, pixels_out)
