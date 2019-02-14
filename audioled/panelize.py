from audioled.effect import Effect
from collections import OrderedDict
import numpy as np


class MakeSquare(Effect):
    """MakeSquare takes a 1d pixel array and fills the panel by the following pattern:

    1 2 3 4 5 6 7 8
    ->
    1 1 1 1 1 1 1 1
    1 2 2 2 2 2 2 1

    1 2 2 3 3 2 2 1
    1 2 3 4 4 3 2 1
    1 2 3 4 4 3 2 1
    1 2 2 3 3 2 2 1

    1 2 2 2 2 2 2 1
    1 1 1 1 1 1 1 1
    """

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
        # [1]             [1 2 3]
        # [1] * [1 2 3] = [1 2 3]
        # [1]             [1 2 3]
        print(self._inputBuffer[0])
        buffer = np.tile(self._inputBuffer[0],np.size(self._inputBuffer[0], axis=1))
        # print("buffer:")
        # print(buffer)
        # print("mask:")
        # print(self._mapMask)
        self._outputBuffer[0] = buffer[self._mapMask[:, :, 0], self._mapMask[:, :, 1]]

    def _genMapMask(self, num_pixels, num_cols):
        num_rows = int(num_pixels / num_cols)
        print("Generating map mask for {}x{} pixels".format(num_rows,num_cols))
        mapMask = np.array([
            [[0, self._indexFor(i, j, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)], 
            [[1, self._indexFor(i, j, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)], 
            [[2, self._indexFor(i, j, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)]],
            dtype=np.int64)
        print(np.shape(mapMask))
        print(np.shape(mapMask))
        return mapMask
    
    def _indexFor(self, row, col, num_rows, num_cols):
        adjusted_row = row
        adjusted_col = col
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col
        
        #index = min(adjusted_row,adjusted_col)
        row_offset = int(abs(num_rows/2 - adjusted_row - 1))
        index = max(0, adjusted_col-row_offset)
        print("index for {}, {}: {}".format(row, col, index))
        return index
