from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
import asyncio
from audioled import panelize
import numpy as np


class Test_Panelize(unittest.TestCase):
    def test_makeSquare4x4_works(self):
        self._makeSquare_works(4 * 4, 1)
        self._makeSquare_works(4 * 4, 2)
        self._makeSquare_works(4 * 4, 4)
        self._makeSquare_works(4 * 4, 8)
        self._makeSquare_works(4 * 4, 16)

    def test_makeSquare8x8_works(self):
        self._makeSquare_works(8 * 8, 1)
        self._makeSquare_works(8 * 8, 2)
        self._makeSquare_works(8 * 8, 4)
        self._makeSquare_works(8 * 8, 8)
        self._makeSquare_works(8 * 8, 16)
        self._makeSquare_works(8 * 8, 32)

    def test_makeSquare44x22_works(self):
        self._makeSquare_works(44 * 22, 1)
        self._makeSquare_works(44 * 22, 22)
        self._makeSquare_works(44 * 22, 44)

    def _makeSquare_works(self, num_pixels, num_rows):
        self.assertEqual(num_pixels % num_rows, 0)
        num_cols = int(num_pixels / num_rows)
        effect = panelize.MakeSquare()
        effect.setNumOutputPixels(num_pixels)
        effect.setNumOutputRows(num_rows)
        self.assertEqual(effect.getNumInputPixels(0), 2 * num_cols)
        input = np.array([[i + 1, 2 * i + 1, 3 * i + 1] for i in range(0, 2 * num_cols)]).T
        for i in range(0, 2 * num_cols):
            self.assertEqual(i + 1, input[0, i])
        effect._inputBuffer = [input]
        effect._outputBuffer = [None]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(effect.update(0))
        self.assertIsNotNone(effect._mapMask)
        effect.process()
        self.assertIsNotNone(effect._outputBuffer)
        self.assertEqual(len(effect._outputBuffer), 1)
        output = effect._outputBuffer[0]
        self.assertEqual(np.size(output, axis=1), num_pixels)
        for i in range(0, num_rows):
            for j in range(0, num_cols):
                index = self._indexFor(i, j, num_rows, num_cols)
                self.assertEqual(input[0, index], output[0, j + i * num_cols])

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
