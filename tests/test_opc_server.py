import unittest
from audioled import opc_server
from audioled import opc
import numpy as np
import time
import random

class Test_OPC_Server(unittest.TestCase):
    def test_server(self):
        server = opc_server.Server('127.0.0.1', 7891)
        # start receiving without blocking
        server.get_pixels(block=False)


        # construct client
        client = opc.Client('127.0.0.1:7891',long_connection=True)
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

