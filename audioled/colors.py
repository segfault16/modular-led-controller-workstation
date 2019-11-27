from __future__ import (absolute_import, division, print_function, unicode_literals)

import colorsys
import math
from collections import OrderedDict

import numpy as np
from PIL import Image

from audioled.effect import Effect

blend_modes = ['lightenOnly', 'darkenOnly', 'addition', 'multiply', 'screen', 'overlay', 'softLight']
blend_mode_default = 'lightenOnly'


def blend(pixel_a, pixel_b, blend_mode):
    if pixel_a is None and pixel_b is None:
        return None
    elif pixel_a is not None and pixel_b is None:
        return pixel_a
    elif pixel_a is None and pixel_b is not None:
        return pixel_b

    if blend_mode == 'lightenOnly':
        return np.maximum(pixel_a, pixel_b)
    elif blend_mode == 'darkenOnly':
        return np.minimum(pixel_a, pixel_b)
    elif blend_mode == 'addition':
        return pixel_a + pixel_b
    elif blend_mode == 'multiply':
        pA = pixel_a / 255.0
        pB = pixel_b / 255.0
        return 255.0 * pA * pB
    elif blend_mode == 'screen':
        pA = pixel_a / 255.0
        pB = pixel_b / 255.0
        return 255.0 * (1 - (1 - pA) * (1 - pB))
    elif blend_mode == 'overlay':
        pA = pixel_a / 255.0
        pB = pixel_b / 255.0
        mask = pA >= 0.5

        blended = np.zeros(np.shape(pA))
        blended[~mask] = (2 * pA * pB)[~mask]
        blended[mask] = (1 - 2 * (1 - pA) * (1 - pB))[mask]
        return 255.0 * blended
    elif blend_mode == 'softLight':
        # pegtop
        pA = pixel_a / 255.0
        pB = pixel_b / 255.0
        blended = (1 - 2 * pB) * pA * pA + 2 * pB * pA
        return 255.0 * blended

    return pixel_a


def hsv_to_rgb(hsv):
    a = np.expand_dims(hsv, axis=1).T.astype(np.uint8)
    pImg = Image.fromarray(a, mode='HSV')
    pImg = pImg.convert('RGB')
    out = np.asarray(pImg, dtype=np.uint8)
    out = out.reshape(-1, out.shape[-1]).T
    return out


def rgb_to_hsv(rgb):
    a = np.expand_dims(rgb, axis=1).T.astype(np.uint8)
    pImg = Image.fromarray(a, mode='RGB')
    pImg = pImg.convert('HSV')
    out = np.asarray(pImg, dtype=np.uint8)
    out = out.reshape(-1, out.shape[-1]).T
    return out


# New Filtergraph Style effects


class StaticRGBColor(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "StaticRGBColor outputs a static color."

    def __init__(self, r=255.0, g=255.0, b=255.0):
        self.r = r
        self.g = g
        self.b = b
        self.__initstate__()

    def __initstate__(self):
        # state
        self._color = None
        super(StaticRGBColor, self).__initstate__()

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
                ("r", [255.0, 0.0, 255.0, 1.0]),
                ("g", [255.0, 0.0, 255.0, 1.0]),
                ("b", [255.0, 0.0, 255.0, 1.0]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "r": "Amount of red.",
                "g": "Amount of green.",
                "b": "Amount of blue.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['r'][0] = self.r
        definition['parameters']['g'][0] = self.g
        definition['parameters']['b'][0] = self.b
        return definition

    def setInputBuffer(self, buffer):
        self._inputBuffer = buffer

    def setOutputBuffer(self, buffer):
        self._outputBuffer = buffer

    async def update(self, dt):
        await super(StaticRGBColor, self).update(dt)
        if self._color is None or np.size(self._color, 1) != self._num_pixels:
            self._color = np.ones(self._num_pixels) * np.array([[self.r], [self.g], [self.b]])

    def process(self):
        if self._outputBuffer is not None:
            self._outputBuffer[0] = self._color


class ColorWheel(Effect):
    """ Generates colors
    """
    @staticmethod
    def getEffectDescription():
        return \
            "The ColorWheel moves through the HSV color space and outputs the color."

    def __init__(self, cycle_time=30.0, offset=0.0, luminocity=0.5, saturation=1.0, wiggle_amplitude=0.0, wiggle_time=0.0):
        self.cycle_time = cycle_time
        self.offset = offset
        self.wiggle_amplitude = wiggle_amplitude
        self.wiggle_time = wiggle_time
        self.luminocity = luminocity
        self.saturation = saturation
        self.__initstate__()

    def __initstate__(self):
        # state
        self._color = None
        super(ColorWheel, self).__initstate__()

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
                ("cycle_time", [30.0, 0, 100, 0.1]),
                ("offset", [0.0, 0, 1, 0.01]),
                ("luminocity", [0.5, 0, 1, 0.01]),
                ("saturation", [1.0, 0, 1, 0.01]),
                ("wiggle_time", [0.0, 0, 10, 0.1]),
                ("wiggle_amplitude", [0.0, 0, 1, 0.01]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['cycle_time'][0] = self.cycle_time
        definition['parameters']['offset'][0] = self.offset
        definition['parameters']['luminocity'][0] = self.luminocity
        definition['parameters']['saturation'][0] = self.saturation
        definition['parameters']['wiggle_time'][0] = self.wiggle_time
        definition['parameters']['wiggle_amplitude'][0] = self.wiggle_amplitude
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "cycle_time":
                "Amount of time the Color Wheel needs to cycle through the hue values of the color space.",
                "offset":
                "Offset of the Color Wheel.",
                "luminocity":
                "Luminocity of the color space.",
                "saturation":
                "Color saturation.",
                "wiggle_time":
                "The Color Wheel can wiggle back and forth while moving through the hue values of the color space. This parameter controls the frequency of the wiggle.",
                "wiggle_amplitude":
                "The Color Wheel can wiggle back and forth while moving through the hue values of the color space. This parameter controls the amplitude of the wiggle.",
            }
        }
        return help

    async def update(self, dt):
        await super(ColorWheel, self).update(dt)
        self._color = self.get_color_array(self._t, self._num_pixels)

    def process(self):
        if self._outputBuffer is not None:
            self._outputBuffer[0] = self._color

    def get_color(self, t, pixel):
        h = 0.0
        # move through wheel
        if self.cycle_time > 0:
            h = (t + self.offset % self.cycle_time) / self.cycle_time
        else:
            h = self.offset
        # and wiggle
        if self.wiggle_time > 0:
            h = h + math.sin(2 * math.pi / self.wiggle_time * t) * self.wiggle_amplitude

        r, g, b = colorsys.hls_to_rgb(h, self.luminocity, self.saturation)

        return np.array([[r * 255.0], [g * 255.0], [b * 255.0]])

    def get_color_array(self, t, num_pix):
        return np.ones(num_pix) * self.get_color(t, -1)


class InterpolateRGB(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "RGB interpolation between two color inputs."

    def __init__(self):
        self.__initstate__()

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is not None and self._outputBuffer is not None:
            a = self._inputBuffer[0]
            b = self._inputBuffer[1]
            if a is not None and b is not None:
                fact = np.linspace(0., 1., self._num_pixels)
                self._outputBuffer[0] = a + np.multiply((b - a), fact)
            elif a is not None:
                self._outputBuffer[0] = a
            elif b is not None:
                self._outputBuffer[0] = b


class InterpolateHSV(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "HSV interpolation between two color inputs."

    def __init__(self):
        self.__initstate__()

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is not None and self._outputBuffer is not None:
            a = self._inputBuffer[0]
            b = self._inputBuffer[1]

            if a is not None and b is not None:
                rgb_a = 1. / 255. * a[0:3, 0]
                rgb_b = 1. / 255. * b[0:3, 0]
                h_a, s_a, v_a = colorsys.rgb_to_hsv(rgb_a[0], rgb_a[1], rgb_a[2])
                h_b, s_b, v_b = colorsys.rgb_to_hsv(rgb_b[0], rgb_b[1], rgb_b[2])

                interp_v = np.linspace(v_a, v_b, self._num_pixels)
                interp_s = np.linspace(s_a, s_b, self._num_pixels)
                interp_h = np.linspace(h_a, h_b, self._num_pixels)
                hsv = np.array([interp_h, interp_s, interp_v]).T

                rgb = hsv_to_rgb(hsv)

                self._outputBuffer[0] = rgb.T * 255.0


class RGBToHSV(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Switches encoding from RGB to HSV encoding"

    def __init__(self):
        self.__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        a = self._inputBuffer[0]
        if a is None:
            return
        a = np.expand_dims(a, axis=1).T.astype(np.uint8)
        pImg = Image.fromarray(a, mode='RGB')
        pImg = pImg.convert('HSV')
        out = np.asarray(pImg, dtype=np.uint8)
        out = out.reshape(-1, out.shape[-1]).T
        self._outputBuffer[0] = out


class HSVToRGB(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Switches encoding from HSV to RGB encoding"

    def __init__(self):
        self.__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        a = self._inputBuffer[0]
        if a is None:
            return
        a = np.expand_dims(a, axis=1).T.astype(np.uint8)
        pImg = Image.fromarray(a, mode='HSV')
        pImg = pImg.convert('RGB')
        out = np.asarray(pImg, dtype=np.uint8)
        out = out.reshape(-1, out.shape[-1]).T
        self._outputBuffer[0] = out