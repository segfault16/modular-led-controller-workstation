import unittest
from audioled import opc_server

class Test_OPC_Server(unittest.TestCase):
    def test_server(self):
        server = opc_server.Server('127.0.0.1', 7891)
        server.get_pixels()