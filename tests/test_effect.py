from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
import jsonpickle
from audioled import colors

class Test_Effect(unittest.TestCase):
    def test_parameterOffsetWorks(self):
        testEffect = colors.StaticRGBColor(r=100, g=100)
        testEffect.setParameterOffset('r', testEffect.getParameterDefinition(), 1)
        testEffect.setParameterOffset('g', testEffect.getParameterDefinition(), -1)
        self.assertEqual(testEffect.r, 255)
        self.assertEqual(testEffect.g, 0)
    
    def test_getStateReturnsOriginalValue(self):
        testEffect = colors.StaticRGBColor(r=100)
        testEffect.setParameterOffset('r', testEffect.getParameterDefinition(), 1)
        state = testEffect.__getstate__()
        
        self.assertEqual(state['r'], 100)
