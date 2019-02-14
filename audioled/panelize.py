from audioled.effect import Effect
from collections import OrderedDict
import numpy as np


class MakeSquare(Effect):
    def __init__(self):
        super().__init__()
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._mapMask = None

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def getNumInputCols(self, channel):
        # strip as input
        return 1

    def getNumInputPixels(self, channel):
        if self._num_pixels != None:
            rows = int(self._num_pixels / self._num_cols)
            return max(rows, self._num_cols)
        return None

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                # ("speed", [100.0, -1000.0, 1000.0, 1.0]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        # definition['parameters']['speed'][0] = self.speed
        return definition

    async def update(self, dt):
        await super().update(dt)
        if self._mapMask is None or np.size(self._mapMask, 1) != self._num_pixels:
            self._mapMask = self._genMapMask(self._num_pixels, self._num_cols)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        buffer = self._inputBuffer[0]
        self._outputBuffer[0] = buffer[self._mapMask[:, :, 0], self._mapMask[:, :, 1]]

    def _genMapMask(self, num_pixels, num_cols):
        num_cols = 2
        num_rows = int(num_pixels / num_cols)
        mapMask = np.array([[[0, i] for i, j in np.ndindex(num_rows, num_cols)], 
            [[1, i] for i, j in np.ndindex(num_rows, num_cols)], 
            [[2, i] for i, j in np.ndindex(num_rows, num_cols)]],
            dtype=np.int64)
        print(np.shape(mapMask))
        print(np.shape(mapMask))
        return mapMask
