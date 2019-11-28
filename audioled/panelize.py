from audioled.effect import Effect
from collections import OrderedDict
import numpy as np


class MakeSquare(Effect):
    """MakeSquare takes a 1d pixel array and fills the panel by the following pattern:

    1 2 3 4 5 6 7 8
    ->
    1 1 1 1 1 1 1 1
    1 2 2 2 2 2 2 1
    1 2 3 3 3 3 2 1
    1 2 3 4 4 3 2 1
    1 2 3 4 4 3 2 1
    1 2 3 3 3 3 2 1
    1 2 2 2 2 2 2 1
    1 1 1 1 1 1 1 1
    """
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that converts the pixel input into a square pattern if displayed on a panel."

    def __init__(self, displacement=0.0, input_displacement=0.5):
        super().__init__()
        self.displacement = displacement
        self.input_displacement = input_displacement
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
            cols = int(2 * self._num_pixels / self._num_rows)
            return cols
        return None

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("displacement", [0.0, -1.0, 1.0, .001]),
                ("input_displacement", [0.5, 0.0, 1.0, .001]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "displacement": "Moves the pattern out of the center of the panel.",
                "input_displacement": "Adjusts size of the center of the pattern."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['displacement'][0] = self.displacement
        definition['parameters']['input_displacement'][0] = self.input_displacement
        return definition

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._mapMask is None or np.size(self._mapMask, 1) != self._num_pixels:
            self._mapMask = self._genMapMask(self._num_pixels, self._num_rows, self.displacement, self.input_displacement)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        buffer = np.tile(self._inputBuffer[0], np.size(self._inputBuffer[0], axis=1))
        self._outputBuffer[0] = buffer[self._mapMask[:, :, 0], self._mapMask[:, :, 1]]

    def _genMapMask(self, num_pixels, num_rows, displacement, input_displacement):
        num_cols = int(num_pixels / num_rows)
        print("Generating map mask for {}x{} pixels".format(num_cols, num_rows))
        dp = int(displacement * num_cols)
        mapMask = np.array([[[0, self._indexFor(i, j + dp, num_rows, num_cols, input_displacement)]
                             for i, j in np.ndindex(num_rows, num_cols)],
                            [[1, self._indexFor(i, j + dp, num_rows, num_cols, input_displacement)]
                             for i, j in np.ndindex(num_rows, num_cols)],
                            [[2, self._indexFor(i, j + dp, num_rows, num_cols, input_displacement)]
                             for i, j in np.ndindex(num_rows, num_cols)]],
                           dtype=np.int64)
        return mapMask

    def _indexFor(self, row, col, num_rows, num_cols, input_displacement=0.5):
        adjusted_row = row
        adjusted_col = col
        dp = int(input_displacement * num_cols)
        # Mirror row at the center
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        # Mirror col at the center
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col

        row_offset = int(abs(num_rows / 2 - adjusted_row + 1))
        col_offset = int(abs(num_cols / 2 - adjusted_col + 1))
        index = min(max(0, int(max(num_rows, num_cols) / 2) - max(row_offset, col_offset) + dp), num_cols - 1)
        return index


class MakeBatman(MakeSquare):
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that converts the pixel input into a batman sign shaped pattern if displayed on a panel."

    def _indexFor(self, row, col, num_rows, num_cols, input_displacement=0.5):
        adjusted_row = row
        adjusted_col = col
        dp = int(input_displacement * num_cols)
        # Mirror row at the center
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        # Mirror col at the center
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col

        row_offset = int(abs(num_rows / 2 - adjusted_row - 1))
        col_offset = int(abs(num_cols / 2 - adjusted_col - 1))
        offset = min(row_offset, col_offset)
        index = min(max(0, min(adjusted_col - offset, adjusted_row - offset) + dp), num_cols - 1)
        return index


class MakeRuby(MakeSquare):
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that converts the pixel input into a ruby shaped pattern if displayed on a panel."

    def _indexFor(self, row, col, num_rows, num_cols, input_displacement=0.5):
        adjusted_row = row
        adjusted_col = col
        dp = int(input_displacement * num_cols)
        # Mirror row at the center
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        # Mirror col at the center
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col

        row_offset = int(abs(num_rows / 2 - adjusted_row - 1))
        col_offset = int(abs(num_cols / 2 - adjusted_col - 1))
        offset = max(row_offset, col_offset)
        index = min(max(0, min(adjusted_col - offset, adjusted_row - offset) + dp), num_cols - 1)
        return index


class MakeDiamond(MakeSquare):
    """MakeDiamond takes a 1d pixel array and fills the panel by the following pattern:

    1 2 3 4 5 6 7 8
    ->
    1 1 1 1 1 1 1 1
    1 1 1 2 2 1 1 1
    1 1 2 3 3 2 1 1
    1 2 3 4 4 3 2 1
    1 2 3 4 4 3 2 1
    1 1 2 3 3 2 1 1
    1 1 1 2 2 2 1 1
    1 1 1 1 1 1 1 1
    """
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that converts the pixel input into a diamond shaped pattern if displayed on a panel."

    def _indexFor(self, row, col, num_rows, num_cols, input_displacement=0.5):
        adjusted_row = row
        adjusted_col = col
        dp = int(input_displacement * num_cols)
        # Mirror row at the center
        if row >= num_rows / 2:
            adjusted_row = num_rows - 1 - row
        # Mirror col at the center
        if col >= num_cols / 2:
            adjusted_col = num_cols - 1 - col

        # Apply row offset, so that index is decreased for each row more away from the center
        row_offset = int(abs(num_rows / 2 - adjusted_row - 1))
        index = min(max(0, adjusted_col - row_offset + dp), num_cols - 1)
        return index


def toIdx(row, col, num_cols):
    return row * num_cols + col


def move(row, col, direction):
    if direction == 'l':
        return (row, col - 1)
    elif direction == 'r':
        return (row, col + 1)
    elif direction == 'u':
        return (row - 1, col)
    else:
        return (row + 1, col)


def next_dir_possible(cur_dir, cur_row, cur_col, visited, pref_dir, allowed_row_range):
    for i in range(0, len(pref_dir)):
        rows = np.size(visited, axis=0)
        cols = np.size(visited, axis=1)
        r, c = move(cur_row, cur_col, pref_dir[i])
        # check out of bounds
        if r < 0 or c < 0 or r >= rows or c >= cols:
            continue

        # check visited
        if visited[r, c]:
            continue
        # check in allowed row range
        if r < allowed_row_range[0] or r > allowed_row_range[1]:
            continue
        # found new direction
        print("next dir: {}, preference {}".format(pref_dir[i], i))
        return pref_dir[i]
    raise RuntimeError("Cannot determine new direction!")


def next_dir(cur_dir, cur_row, cur_col, visited, pref_dir, allowed_row_range):
    return next_dir_possible(cur_dir, cur_row, cur_col, visited, pref_dir, allowed_row_range)


class MakeLabyrinth(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that reorders pixels on a panel into a pattern that resembles a labyrinth."

    def __init__(self):
        super().__init__()
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._mapMask = None

    def numOutputChannels(self):
        return 1

    def numInputChannels(self):
        return 1

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._mapMask is None or np.size(self._mapMask, 1) != self._num_pixels:
            self._mapMask = self._genMapMask(self._num_pixels, self._num_rows)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        buffer = self._inputBuffer[0]
        self._outputBuffer[0] = buffer[self._mapMask[:, :, 0], self._mapMask[:, :, 1]]

    def _genMapMask(self, num_pixels, num_rows):

        num_cols = int(num_pixels / num_rows)
        mapMask = np.zeros((3, num_pixels, 2))
        visited = np.zeros((num_rows, num_cols), dtype=np.int64)  # array holding information if pixel was visited
        cur_idx_u = int(num_pixels / 2)  # current index counter upper half
        cur_idx_l = int(num_pixels / 2)  # current index counter lower half
        cur_row_u = int(num_rows / 2) - 1
        cur_col_u = int(num_cols / 2)
        cur_row_l = int(num_rows / 2)
        cur_col_l = int(num_cols / 2) - 1
        # visit first pixels
        for i in range(0, 1):
            mapMask[0, toIdx(cur_row_u, cur_col_u, num_cols), :] = [0, cur_idx_u]
            mapMask[1, toIdx(cur_row_u, cur_col_u, num_cols), :] = [1, cur_idx_u]
            mapMask[2, toIdx(cur_row_u, cur_col_u, num_cols), :] = [2, cur_idx_u]
            visited[cur_row_u, cur_col_u] = 1
            cur_idx_u -= 1
            cur_col_u -= 1
        for i in range(0, 1):
            mapMask[0, toIdx(cur_row_l, cur_col_l, num_cols), :] = [0, cur_idx_l]
            mapMask[1, toIdx(cur_row_l, cur_col_l, num_cols), :] = [1, cur_idx_l]
            mapMask[2, toIdx(cur_row_l, cur_col_l, num_cols), :] = [2, cur_idx_l]
            visited[cur_row_l, cur_col_l] = 1
            cur_idx_l += 1
            cur_col_l += 1
        dir_u = 'u'
        dir_l = 'd'
        last_hor_u = 'l'
        last_hor_l = 'r'
        allowed_range_u = [0, int(num_rows / 2) - 1]
        allowed_range_l = [int(num_rows / 2), num_rows - 1]
        for p in range(0, int(num_pixels / 2) - 2):
            # adjust indices
            cur_idx_u = int(cur_idx_u - 1)
            cur_idx_l = int(cur_idx_l + 1)
            # move
            cur_row_u, cur_col_u = move(cur_row_u, cur_col_u, dir_u)
            cur_row_l, cur_col_l = move(cur_row_l, cur_col_l, dir_l)
            # set new value
            mapMask[0, toIdx(cur_row_u, cur_col_u, num_cols), :] = [0, cur_idx_u]
            mapMask[1, toIdx(cur_row_u, cur_col_u, num_cols), :] = [1, cur_idx_u]
            mapMask[2, toIdx(cur_row_u, cur_col_u, num_cols), :] = [2, cur_idx_u]
            visited[cur_row_u, cur_col_u] = 1
            mapMask[0, toIdx(cur_row_l, cur_col_l, num_cols), :] = [0, cur_idx_l]
            mapMask[1, toIdx(cur_row_l, cur_col_l, num_cols), :] = [1, cur_idx_l]
            mapMask[2, toIdx(cur_row_l, cur_col_l, num_cols), :] = [2, cur_idx_l]
            visited[cur_row_l, cur_col_l] = 1
            # determine new direction upper
            try:
                cur_dir = dir_u
                if last_hor_u == 'l':
                    dir_u = next_dir(dir_u, cur_row_u, cur_col_u, visited, ['d', 'r', 'u', 'l'], allowed_range_u)
                elif last_hor_u == 'r':
                    dir_u = next_dir(dir_u, cur_row_u, cur_col_u, visited, ['d', 'l', 'u', 'r'], allowed_range_u)
                else:
                    dir_u = next_dir(dir_u, cur_row_u, cur_col_u, visited, ['d', 'r', 'l', 'u'], allowed_range_u)
                if dir_u == 'd' and (cur_dir == 'l' or cur_dir == 'r'):
                    last_hor_u = cur_dir
            except RuntimeError:
                # reset allowed range
                allowed_range_u = [0, num_rows]

            # determine new direction lower
            try:
                cur_dir = dir_l
                if last_hor_l == 'l':
                    dir_l = next_dir(dir_l, cur_row_l, cur_col_l, visited, ['u', 'r', 'd', 'l'], allowed_range_l)
                elif last_hor_l == 'r':
                    dir_l = next_dir(dir_l, cur_row_l, cur_col_l, visited, ['u', 'l', 'd', 'r'], allowed_range_l)
                else:
                    dir_l = next_dir(dir_l, cur_row_l, cur_col_l, visited, ['u', 'l', 'r', 'd'], allowed_range_l)
                if dir_l == 'u' and (cur_dir == 'l' or cur_dir == 'r'):
                    last_hor_l = cur_dir
            except RuntimeError:
                # reset allowed range
                allowed_range_l = [0, num_rows]

        return mapMask.astype(np.int64)


class FlipRows(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Effect that enables flipping the ordering of pixels for even or odd rows in a panel."

    def __init__(self, flip_odd_rows=False, flip_even_rows=True):
        super().__init__()
        self.flip_odd_rows = flip_odd_rows
        self.flip_even_rows = flip_even_rows
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()

    def numOutputChannels(self):
        return 1

    def numInputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("flip_odd_rows", False),
                ("flip_even_rows", True),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "flip_odd_rows": "Flip ordering of pixels in odd rows.",
                "flip_even_rows": "Flip ordering of pixels in even rows."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['flip_odd_rows'] = self.flip_odd_rows
        definition['parameters']['flip_even_rows'] = self.flip_even_rows
        return definition

    async def update(self, dt):
        await super().update(dt)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        buffer = self._inputBuffer[0]

        cols = int(self._num_pixels / self._num_rows)
        for row in range(self._num_rows - 1):
            if row % 2 == 0:
                if self.flip_even_rows:
                    buffer[:, row * cols:(row + 1) * cols] = self._inputBuffer[0][:, row * cols:(row + 1) * cols][:, ::-1]
                else:
                    buffer[:, row * cols:(row + 1) * cols] = self._inputBuffer[0][:, row * cols:(row + 1) * cols]
            else:
                if self.flip_odd_rows:
                    buffer[:, row * cols:(row + 1) * cols] = self._inputBuffer[0][:, row * cols:(row + 1) * cols][:, ::-1]
                else:
                    buffer[:, row * cols:(row + 1) * cols] = self._inputBuffer[0][:, row * cols:(row + 1) * cols]

        self._outputBuffer[0] = buffer
