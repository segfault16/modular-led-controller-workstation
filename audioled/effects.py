from __future__ import (absolute_import, division, print_function, unicode_literals)

from collections import OrderedDict

import numpy as np
import scipy as sp
import math

import audioled.colors as colors
from audioled.effect import Effect

SHORT_NORMALIZE = 1.0 / 32768.0


class Shift(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Shift effect for shifting pixels through the strip."

    def __init__(self, speed=100.0):
        self.speed = speed
        self.__initstate__()

    def __initstate__(self):
        # state
        super(Shift, self).__initstate__()
        try:
            self._shift_pixels
        except AttributeError:
            self._shift_pixels = 0

        self._last_t = self._t

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("speed", [100.0, -1000.0, 1000.0, 1.0]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "speed": "Speed of the shifting effect.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['speed'][0] = self.speed
        return definition

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return

        y = self._inputBuffer[0]
        dt_move = self._t - self._last_t
        shift = dt_move * self.speed * 0.1
        self._shift_pixels = math.fmod((self._shift_pixels + shift), np.size(y, axis=1))
        self._last_t = self._t
        self._outputBuffer[0] = sp.ndimage.interpolation.shift(y, [0, self._shift_pixels], mode='wrap', prefilter=True)


class Append(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Append combines multiple channels into one output."

    def __init__(self,
                 num_channels=2,
                 flip0=False,
                 flip1=False,
                 flip2=False,
                 flip3=False,
                 flip4=False,
                 flip5=False,
                 flip6=False,
                 flip7=False):
        self.num_channels = num_channels
        self.flip0 = flip0
        self.flip1 = flip1
        self.flip2 = flip2
        self.flip3 = flip3
        self.flip4 = flip4
        self.flip5 = flip5
        self.flip6 = flip6
        self.flip7 = flip7
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._flipMask = [self.flip0, self.flip1, self.flip2, self.flip3, self.flip4, self.flip5, self.flip6, self.flip7]

    def numInputChannels(self):
        return self.num_channels

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_channels", [2, 1, 8, 1]),
                ("flip0", False),
                ("flip1", False),
                ("flip2", False),
                ("flip3", False),
                ("flip4", False),
                ("flip5", False),
                ("flip6", False),
                ("flip7", False),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "num_channels": "Number of input channels of the effect.",
                "flip0": "Change pixel direction of input channel 0.",
                "flip1": "Change pixel direction of input channel 1.",
                "flip2": "Change pixel direction of input channel 2.",
                "flip3": "Change pixel direction of input channel 3.",
                "flip4": "Change pixel direction of input channel 4.",
                "flip5": "Change pixel direction of input channel 5.",
                "flip6": "Change pixel direction of input channel 6.",
                "flip7": "Change pixel direction of input channel 7.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_channels']  # not editable at runtime
        definition['parameters']['flip0'] = self.flip0
        definition['parameters']['flip1'] = self.flip1
        definition['parameters']['flip2'] = self.flip2
        definition['parameters']['flip3'] = self.flip3
        definition['parameters']['flip4'] = self.flip4
        definition['parameters']['flip5'] = self.flip5
        definition['parameters']['flip6'] = self.flip6
        definition['parameters']['flip7'] = self.flip7
        return definition

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._inputBuffer[0] is None:
            self._outputBuffer[0] = None
            return
        state = np.zeros((3, 0))
        for i in range(0, self.num_channels):
            if self._inputBuffer[i] is not None:
                if self._flipMask is not None and self._flipMask[i] > 0:
                    state = np.concatenate((state, self._inputBuffer[i][:, ::-1]), axis=1)
                else:
                    state = np.concatenate((state, self._inputBuffer[i]), axis=1)
        # Make sure the size of the output state matches num_pixels
        remainingPixels = self._num_pixels - np.size(state, axis=1)
        if remainingPixels > 0:
            remainder = np.zeros((3, remainingPixels))
            remainder[0, :] = state[0, -1]
            remainder[1, :] = state[1, -1]
            remainder[2, :] = state[2, -1]
            state = np.concatenate((state, remainder), axis=1)
        self._outputBuffer[0] = state

    def getNumInputPixels(self, channel):
        # Override get num input pixels
        if self._num_pixels is not None:
            return int(self._num_pixels / self.num_channels)
        else:
            return None


class Combine(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Effect for blending two channels into one using several color blend modes."

    def __init__(self, mode=colors.blend_mode_default):
        self.mode = mode
        self.__initstate__()

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {"parameters": OrderedDict([("mode", colors.blend_modes)])}
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "mode": "Color blend mode for combining input channel 0 and input channel 1.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['mode'] = [self.mode] + [x for x in colors.blend_modes if x != self.mode]
        return definition

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0) and not self._inputBufferValid(1):
            # no input on any channels
            self._outputBuffer[0] = None
        elif self._inputBufferValid(0) and self._inputBufferValid(1):
            # input on both channels
            self._outputBuffer[0] = colors.blend(self._inputBuffer[0], self._inputBuffer[1], self.mode)
        elif self._inputBufferValid(0):
            # only channel 0 valid
            self._outputBuffer[0] = self._inputBuffer[0]
        elif self._inputBufferValid(1):
            # only channel 1 valid
            self._outputBuffer[0] = self._inputBuffer[0]
        else:
            self._outputBuffer[0] = None


class AfterGlow(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Afterglow makes pixels hold their value and fade out smoothly."

    def __init__(self, glow_time=1.0):
        self.glow_time = glow_time
        self.__initstate__()

    def __initstate__(self):
        # state
        self._pixel_state = None
        self._last_t = 0.0
        super(AfterGlow, self).__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("glow_time", [1.0, 0.0, 5.0, 0.001]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "glow_time": "Amount of time for the pixels to glow.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['glow_time'][0] = self.glow_time
        return definition

    async def update(self, dt):
        await super().update(dt)
        dt = self._t - self._last_t
        self._last_t = self._t

        if dt > 0:
            # Dim state
            if self.glow_time > 0 and self._pixel_state is not None:
                self._pixel_state = self._pixel_state * (1.0 - dt / self.glow_time)
            else:
                self._pixel_state = None

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        y = self._inputBuffer[0]
        if y is None:
            self._outputBuffer[0] = None
            return

        if self._pixel_state is not None and np.size(self._pixel_state) == np.size(y):
            # keep previous state if new color is too dark
            diff = np.nan_to_num((y - self._pixel_state).max(axis=0))
            mask = diff < 10

            y[:, mask] = self._pixel_state[:, mask]

        self._pixel_state = y.clip(0.0, 255.0)

        self._outputBuffer[0] = y.clip(0.0, 255.0)


class Mirror(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Mirrors the upper or lower half of the input channel."

    def __init__(self, mirror_lower=True, recursion=0):
        self.mirror_lower = mirror_lower
        self.recursion = recursion
        self.__initstate__()

    def __initstate__(self):
        # state
        self._mirrorLower = None
        self._mirrorUpper = None
        super(Mirror, self).__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                ("mirror_lower", True),
                # default, min, max, stepsize
                ("recursion", [0, 0, 8, 1]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "mirror_lower": "Switch between mirroring the lower or the upper part of input channel 0.",
                "recursion": "Recursion depth of the mirroring effect. If recursion is set to 1, "\
                    "the lower and upper half of the strip are mirrored again at their centers."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['mirror_lower'] = self.mirror_lower
        definition['parameters']['recursion'][0] = self.recursion
        return definition

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return
        num_pixels = np.size(self._inputBuffer[0], 1)
        if self._mirrorLower is None or np.size(self._mirrorLower, 1) != num_pixels:
            self._mirrorLower = self._genMirrorLowerMap(num_pixels, self.recursion)
        if self._mirrorUpper is None or np.size(self._mirrorUpper, 1) != num_pixels:
            self._mirrorUpper = self._genMirrorUpperMap(num_pixels, self.recursion)
        buffer = self._inputBuffer[0]
        # 0 .. h .. n
        #   h    n-h
        if self.mirror_lower:
            self._outputBuffer[0] = buffer[self._mirrorLower[:, :, 0], self._mirrorLower[:, :, 1]]
        else:
            self._outputBuffer[0] = buffer[self._mirrorUpper[:, :, 0], self._mirrorUpper[:, :, 1]]

    def _genMirrorLowerMap(self, n, recursion):
        mapMask = np.array([[[0, i] for i in range(0, n)], [[1, i] for i in range(0, n)], [[2, i] for i in range(0, n)]],
                           dtype=np.int64)
        mapMask = self._genMirrorLower(mapMask, recursion)
        return mapMask

    def _genMirrorLower(self, mask, recurse=0):
        mapMask = mask.copy()
        n = mapMask.shape[1]
        if n % 2 == 1:
            n = n - 1
        h = int(n / 2)
        temp = mapMask[:, 0:h, :]
        temp = temp[:, ::-1, :]
        mapMask[:, h:n, :] = temp[:, 0:h, :]
        if recurse > 0:
            mapMask[:, 0:h, :] = self._genMirrorLower(mapMask[:, 0:h, :], recurse - 1)
            mapMask[:, h:n, :] = self._genMirrorUpper(mapMask[:, h:n, :], recurse - 1)
        return mapMask

    def _genMirrorUpperMap(self, n, recursion):
        mapMask = np.array([[[0, i] for i in range(0, n)], [[1, i] for i in range(0, n)], [[2, i] for i in range(0, n)]],
                           dtype=np.int64)
        mapMask = self._genMirrorUpper(mapMask, recursion)
        return mapMask

    def _genMirrorUpper(self, mask, recurse=0):
        mapMask = mask.copy()
        n = mapMask.shape[1]
        if n % 2 == 1:
            n = n - 1
        h = int(n / 2)
        # take upper part
        temp = mapMask[:, h:n, :]
        # revert
        temp = temp[:, ::-1, :]
        # assign to lower part
        mapMask[:, 0:n - h, :] = temp[:, 0:n - h, :]
        if recurse > 0:
            mapMask[:, 0:h, :] = self._genMirrorUpper(mapMask[:, 0:h, :], recurse - 1)
            mapMask[:, h:n, :] = self._genMirrorLower(mapMask[:, h:n, :], recurse - 1)
        return mapMask


class SpringCombine(Effect):
    """Spring simulation effect that interpolates between three inputs based on displacement of the springs.

    The trigger input actuates on the springs (if value exceeds trigger_threshold).
    Depending on the displacement of each spring, the output value is a linear interpolation between:
    - Input 1 and Input 2 if displacement < 0
    - Input 2 and Input 3 if displacement > 0

    Inputs:
        0 -- Trigger input
        1 -- Pixel input for displacement in negative direction
        2 -- Pixel input for no displacement
        3 -- Pixel input for displacement in positive direction

    Parameters:
        dampening           -- Dampening factory of the springs
        tension             -- Tension of the springs
        spread              -- Interaction between neighboring springs
        scale_low           -- Scales input 1
        scale_mid           -- Scales input 2
        scale_high          -- Scales input 3
        speed               -- Controls speed of spring simulation
        trigger_threshold   -- Above this threshold springs are actuated based on input 0

    """
    @staticmethod
    def getEffectDescription():
        return \
            "Spring simulation effect that interpolates between three inputs based on displacement of the springs. "\
            "The trigger input (channel 0) actuates on the springs (if value exceeds trigger_threshold). "\
            "Depending on the displacement of each spring, the output value is a linear interpolation between:\n"\
            "- channel 1 and channel 2 if displacement < 0\n"\
            "- channel 2 and channel 3 if displacement > 0"

    def __init__(self,
                 dampening=0.99,
                 tension=0.001,
                 spread=0.8,
                 scale_low=0.0,
                 scale_mid=0.5,
                 scale_high=1.0,
                 speed=5.0,
                 trigger_threshold=0.1):
        self.dampening = dampening
        self.tension = tension
        self.spread = spread
        self.scale_low = scale_low
        self.scale_mid = scale_mid
        self.scale_high = scale_high
        self.speed = speed
        self.trigger_threshold = trigger_threshold
        self.__initstate__()

    def __initstate__(self):
        super(SpringCombine, self).__initstate__()
        self._pos = None
        self._vel = None

    def numInputChannels(self):
        return 4  # trigger, low, mid, high

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "dampening": [0.99, 0.9, 1.0, 0.0001],
                "tension": [0.0001, 0.0, 0.1, 0.0001],
                "spread": [0.8, 0.0, 1.0, 0.001],
                "scale_low": [0.0, 0.0, 2.0, 0.001],
                "scale_mid": [0.5, 0.0, 2.0, 0.001],
                "scale_high": [1.0, 0.0, 2.0, 0.001],
                "speed": [5.0, 0.0, 100.0, 0.001],
                "trigger_threshold": [0.1, 0.01, 1.0, 0.01]
            }
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "dampening": "Dampening factor of the springs. Lower value means stiffer spring.",
                "tension": "Tension of the springs.",
                "spread": "Interaction between neighboring springs.",
                "scale_low": "Scaling factor for input channel 1.",
                "scale_mid": "Scaling factor for input channel 2.",
                "scale_high": "Scaling factor for input channel 3.",
                "speed": "Controls the speed of the spring simulation.",
                "trigger_threshold": "Above this threshold springs are actuated based on brightness of input channel 0."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['dampening'][0] = self.dampening
        definition['parameters']['tension'][0] = self.tension
        definition['parameters']['spread'][0] = self.spread
        definition['parameters']['scale_low'][0] = self.scale_low
        definition['parameters']['scale_mid'][0] = self.scale_mid
        definition['parameters']['scale_high'][0] = self.scale_high
        definition['parameters']['speed'][0] = self.speed
        definition['parameters']['trigger_threshold'][0] = self.trigger_threshold
        return definition

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._pos is None or len(self._pos) != self._num_pixels:
            self._pos = np.zeros(self._num_pixels)
        if self._vel is None or len(self._vel) != self._num_pixels:
            self._vel = np.zeros(self._num_pixels)

        lDeltas = np.zeros(self._num_pixels)  # force from left
        rDeltas = np.zeros(self._num_pixels)  # force from right
        for j in range(4):
            # calculate delta to left and right pixel
            lDeltas[1:] = self.spread * (np.roll(self._pos, 1)[1:] - self._pos[1:])
            rDeltas[:-1] = self.spread * (np.roll(self._pos, -1)[:-1] - self._pos[:-1])
            x = -self._pos
            force = lDeltas + rDeltas + x * self.tension
            acc = force / 1.0
            self._vel = self.dampening * self._vel + acc * (self.speed * dt)
            self._pos += self._vel * (self.speed * dt)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return

        if not self._inputBufferValid(0):
            trigger = np.zeros(self._num_pixels) * np.array([[0], [0], [0]])
        else:
            trigger = self._inputBuffer[0]

        if not self._inputBufferValid(1):
            lowCol = self.scale_low * np.ones(self._num_pixels) * np.array([[0], [0], [0]])
        else:
            lowCol = self.scale_low * self._inputBuffer[1]

        if not self._inputBufferValid(2):
            baseCol = self.scale_mid * np.ones(self._num_pixels) * np.array([[127], [127], [127]])
        else:
            baseCol = self.scale_mid * self._inputBuffer[2]

        if not self._inputBufferValid(3):
            highCol = self.scale_high * np.ones(self._num_pixels) * np.array([[255], [255], [255]])
        else:
            highCol = self.scale_high * self._inputBuffer[3]

        # Actuate on spring depending on trigger
        trigger = np.sum(trigger, axis=0) / (3 * 255.0)
        self._pos[trigger > self.trigger_threshold] = trigger[trigger > self.trigger_threshold]

        # Output: Interpolate between low and mid for self._pos < 0, interpolate between mid and high for self._pos > 0
        out = np.zeros(self._num_pixels) * np.array([[0], [0], [0]])
        out[:, self._pos <= 0] = (np.multiply(1 + self._pos, baseCol) + np.multiply(-self._pos, lowCol))[:, self._pos <= 0]
        out[:, self._pos >= 0] = (np.multiply(self._pos, highCol) + np.multiply(1 - self._pos, baseCol))[:, self._pos >= 0]
        self._outputBuffer[0] = out


class Swing(Effect):
    """PendulumEffect with pixel input.
    Inputs:
    - 0: Pixels
    """
    @staticmethod
    def getEffectDescription():
        return \
            "Makes the pixels shift in both directions like a pendulum."

    def __init__(self, displacement=50, swingspeed=1):
        self.displacement = displacement
        self.swingspeed = swingspeed
        self.__initstate__()

    def __initstate__(self):
        # state
        super(Swing, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("displacement", [50, 1, 1000, 1]),
                ("swingspeed", [1, 0, 5, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "displacement": "Defines maximum amount of pixels that the input is shifted.",
                "swingspeed": "Speed of the swing."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['displacement'][0] = self.displacement
        definition['parameters']['swingspeed'][0] = self.swingspeed
        return definition

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            self._outputBuffer[0] = None
            return

        pixels = self._inputBuffer[0]
        config = self.displacement * math.sin(self._t * self.swingspeed)

        self._outputBuffer[0] = sp.ndimage.interpolation.shift(pixels, [0, config], mode='wrap', prefilter=True)
