from collections import OrderedDict

from audioled import effect, opc_server


class CandyServer(effect.Effect):

    @staticmethod
    def getEffectDescription():
        return \
            "Candy server for receiving OPC data."

    def __init__(self, num_pixels=300, host='', port=7891):
        self.num_pixels = num_pixels
        self.host = host
        self.port = port
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._server = opc_server.Server(self.host, self.port)

    def numInputChannels(self):
        return 0

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("port", [7891, 1000, 10000, 1])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "num_pixels": "Number of pixels.",
                "port": "Port of the server"
            }
        }
        return help

    def process(self):
        if self._outputBuffer is None:
            return
        pixels = self._server.get_pixels()
        self._outputBuffer[0] = pixels
