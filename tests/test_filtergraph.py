from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
from audioled import filtergraph, devices


class Test_FilterGraph(unittest.TestCase):
    def test_canAddAndRemoveNodes(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        ef2 = MockEffect()

        fg.addEffectNode(ef1)
        self.assertEqual(len(fg._filterNodes), 1)
        fg.addEffectNode(ef2)
        self.assertEqual(len(fg._filterNodes), 2)
        fg.removeEffectNode(ef1)
        self.assertEqual(len(fg._filterNodes), 1)
        fg.removeEffectNode(ef2)
        self.assertEqual(len(fg._filterNodes), 0)

    def test_canAddRemoveNodeConnections(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        ef2 = MockEffect()

        fg.addEffectNode(ef1)
        fg.addEffectNode(ef2)
        fg.addConnection(ef1, 0, ef2, 0)
        self.assertEqual(len(fg._filterConnections), 1)
        fg.removeConnection(ef1, 0, ef2, 0)
        self.assertEqual(len(fg._filterConnections), 0)

    def test_connectionOrder_ok(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        ef2 = MockEffect()
        ef3 = MockEffect()
        led = devices.LEDOutput()
        led.setNumOutputPixels(100)

        n1 = fg.addEffectNode(ef1)

        n2 = fg.addEffectNode(ef2)

        n3 = fg.addEffectNode(ef3)
        fg.addEffectNode(led)

        fg.addConnection(ef1, 0, ef2, 0)
        fg.addConnection(ef2, 0, ef3, 0)
        fg.addConnection(ef3, 0, led, 0)
        print(fg._processOrder)
        self.assertTrue(fg._processOrder.index(n1) < fg._processOrder.index(n2))
        self.assertTrue(fg._processOrder.index(n1) < fg._processOrder.index(n3))
        self.assertTrue(fg._processOrder.index(n2) < fg._processOrder.index(n3))

    def test_removeNodes_connectionsAreRemove(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        ef2 = MockEffect()
        fg.addEffectNode(ef1)
        fg.addEffectNode(ef2)
        fg.addConnection(ef1, 0, ef2, 0)
        self.assertEqual(len(fg._filterConnections), 1)
        fg.removeEffectNode(ef1)
        self.assertEqual(len(fg._filterConnections), 0)

    def test_circularConnections_raisesError(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        ef2 = MockEffect()
        ef3 = MockEffect()
        led = devices.LEDOutput()
        fg.addEffectNode(ef1)
        fg.addEffectNode(ef2)
        fg.addEffectNode(ef3)
        fg.addEffectNode(led)
        fg.addConnection(ef1, 0, ef2, 0)
        fg.addConnection(ef2, 0, ef3, 0)
        fg.addConnection(ef3, 0, led, 0)
        self.assertRaises(RuntimeError, fg.addConnection, ef3, 0, ef1, 0)

    def test_outputBuffer_works(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        led = devices.LEDOutput()
        led.setNumOutputPixels(100)
        fg.addEffectNode(ef1)
        fg.addEffectNode(led)
        fg.addConnection(ef1, 0, led, 0)
        fg.process()
        self.assertEqual(len(fg._filterNodes[0]._outputBuffer), 5)
        self.assertEqual(fg._filterNodes[0]._outputBuffer[0], 0)

    def test_mockEffect_works(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect()
        led = devices.LEDOutput()
        led.setNumOutputPixels(100)
        n1 = fg.addEffectNode(ef1)
        fg.addEffectNode(led)
        fg.addConnection(ef1, 0, led, 0)
        ef1._inputBuffer[0] = 12345
        # Process effect
        ef1.process()
        self.assertEqual(ef1._outputBuffer[0], 12345)
        # Set static value for processing node
        ef1.outputValue = 54321
        fg.process()
        self.assertEqual(ef1._outputBuffer[0], 54321)
        self.assertEqual(n1._outputBuffer[0], 54321)

    def test_valuePropagation_works(self):
        fg = filtergraph.FilterGraph()
        ef1 = MockEffect('test')
        ef2 = MockEffect()
        led = devices.LEDOutput()
        led.setNumOutputPixels(100)

        n1 = fg.addEffectNode(ef1)
        n2 = fg.addEffectNode(ef2)
        fg.addEffectNode(led)
        fg.addConnection(ef1, 0, ef2, 1)
        fg.addConnection(ef2, 0, led, 0)

        fg.process()

        self.assertEqual(n1._outputBuffer[0], 'test')
        self.assertEqual(n2._outputBuffer[1], 'test')


class MockEffect(object):
    def __init__(self, outputValue=None):
        self._outputBuffer = None
        self._inputBuffer = None
        self._num_pixels = None
        self.outputValue = outputValue

    def numOutputChannels(self):
        return 5

    def numInputChannels(self):
        return 5

    def setOutputBuffer(self, buffer):
        self._outputBuffer = buffer

    def setInputBuffer(self, buffer):
        self._inputBuffer = buffer

    def setNumOutputPixels(self, num_pixels):
        self._num_pixels = num_pixels

    def getNumInputPixels(self, channel):
        return self._num_pixels

    def process(self):
        self._outputBuffer[0] = 0
        self._outputBuffer[1] = 1
        self._outputBuffer[2] = 2
        self._outputBuffer[3] = 3
        self._outputBuffer[4] = 4

        for i in range(0, 5):
            if self._inputBuffer[i] is not None:
                self._outputBuffer[i] = self._inputBuffer[i]
            elif self.outputValue is not None:
                self._outputBuffer[i] = self.outputValue