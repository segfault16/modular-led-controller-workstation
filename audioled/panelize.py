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

    def __init__(self, displacement=0.5):
        super().__init__()
        self.displacement = displacement
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._mapMask = None

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def getNumInputPixels(self, channel):
        if self._num_pixels is not None:
            cols = int(self._num_pixels / self._num_rows)
            return cols
        return None

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("displacement", [0.5, 0.0, 1.0, .001]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['displacement'][0] = self.displacement
        return definition

    async def update(self, dt):
        await super().update(dt)
        if self._mapMask is None or np.size(self._mapMask, 1) != self._num_pixels:
            self._mapMask = self._genMapMask(self._num_pixels, self._num_rows, self.displacement)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        buffer = np.tile(self._inputBuffer[0], np.size(self._inputBuffer[0], axis=1))
        self._outputBuffer[0] = buffer[self._mapMask[:, :, 0], self._mapMask[:, :, 1]]

    def _genMapMask(self, num_pixels, num_rows, displacement):
        num_cols = int(num_pixels / num_rows)
        print("Generating map mask for {}x{} pixels".format(num_rows, num_cols))
        dp = int(displacement * num_cols)
        mapMask = np.array(
            [[[0, self._indexFor(i, j + dp, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)],
             [[1, self._indexFor(i, j + dp, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)],
             [[2, self._indexFor(i, j + dp, num_rows, num_cols)] for i, j in np.ndindex(num_rows, num_cols)]],
            dtype=np.int64)
        return mapMask

    def _indexFor(self, row, col, num_rows, num_cols):
        adjusted_row = row
        adjusted_col = col
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col

        row_offset = int(abs(num_rows / 2 - adjusted_row - 1))
        index = min(max(0, adjusted_col - row_offset), num_cols - 1)
        return index
