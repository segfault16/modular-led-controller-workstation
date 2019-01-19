from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import asyncio
import colorsys
import math
import random
import struct
import time
import mido
import threading

import numpy as np
from scipy.ndimage.filters import gaussian_filter1d
from scipy.signal import lfilter

import audioled.dsp as dsp
import audioled.filtergraph as filtergraph
from audioled.effect import Effect


class SwimmingPool(Effect):

    def __init__(self, num_pixels, num_waves=30, scale=0.2, wavespread_low=30, wavespread_high=70, max_speed=30):
        self.num_pixels = num_pixels
        self.num_waves = num_waves
        self.scale = scale
        self.wavespread_low = wavespread_low
        self.wavespread_high = wavespread_high
        self.max_speed = max_speed
        self.__initstate__()

    def __initstate__(self):
        # state
        self._pixel_state = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])
        self._last_t = 0.0
        self._output = np.copy(self._pixel_state)
        self._Wave, self._WaveSpecSpeed = self._CreateWaves(self.num_waves, self.scale, self.wavespread_low, self.wavespread_high, self.max_speed)
        super(SwimmingPool, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "num_waves": [30, 1, 100, 1],
                "scale": [0.2, 0.01, 1.0, 0.01],
                "wavespread_low": [30, 1, 100, 1],
                "wavespread_high": [70, 50, 150, 1],
                "max_speed": [30, 1, 200, 1],

            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['num_waves'][0] = self.num_waves
        definition['parameters']['scale'][0] = self.scale
        definition['parameters']['wavespread_low'][0] = self.wavespread_low
        definition['parameters']['wavespread_high'][0] = self.wavespread_high
        definition['parameters']['max_speed'][0] = self.max_speed
        return definition

    def _SinArray(self, _spread, _scale, _wavehight):
        _CArray = []
        _offset = random.randint(0,300)
        for i in range(-_spread, _spread+1):
            _CArray.append(math.sin((math.pi/_spread) * i) * _scale * _wavehight)
            _output = np.copy(self._pixel_state)
            _output[0][:len(_CArray)] += _CArray
            _output[1][:len(_CArray)] += _CArray
            _output[2][:len(_CArray)] += _CArray
        return _output.clip(0.0,255.0)

    def _CreateWaves(self, num_waves, scale, wavespread_low=10, wavespread_high=50, max_speed=30):
        _WaveArray = []
        _WaveArraySpec = []
        _wavespread = np.random.randint(wavespread_low,wavespread_high,num_waves)
        _WaveArraySpecSpeed = np.random.randint(-max_speed,max_speed,num_waves)
        _WaveArraySpecHeight = np.random.rand(num_waves)
        for i in range(0, num_waves):
            _WaveArray.append(self._SinArray(_wavespread[i], scale, _WaveArraySpecHeight[i]))
        return _WaveArray, _WaveArraySpecSpeed;

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            self._output =  np.multiply(color, 0.5 * np.zeros(self.num_pixels))

            for i in range(0,self.num_waves):
                step = np.multiply(color, np.roll(self._Wave[i], int(self._t * self._WaveSpecSpeed[i]), axis=1))
                self._output += step

            self._outputBuffer[0] = self._output.clip(0.0,255.0)



class DefenceMode(Effect):

    def __init__(self, num_pixels, scale=0.2):
        self.num_pixels = num_pixels
        self.scale = scale
        self.__initstate__()

    def __initstate__(self):
        # state
        self._pixel_state = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])
        self._last_t = 0.0
        super(DefenceMode, self).__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            #color = self._inputBuffer[0]
            A = random.choice([True,False,False])
            if A == True:
                self._output = np.ones(self.num_pixels) * np.array([[random.randint(0.0,255.0)], [random.randint(0.0,255.0)], [random.randint(0.0,255.0)]])
            else:
                self._output = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])

            self._outputBuffer[0] = self._output.clip(0.0,255.0)


class MidiKeyboard(Effect):
    def __init__(self, num_pixels, dampening=0.99, tension=0.001, spread=0.1, midiPort='', scale_low=1.0, scale_mid=1.0, scale_high=1.0):
        self.num_pixels = num_pixels
        self.dampening = dampening
        self.tension = tension
        self.spread = spread
        self.midiPort = midiPort
        self.scale_low = scale_low
        self.scale_mid = scale_mid
        self.scale_high = scale_high
        self.__initstate__()
    

    def __initstate__(self):
        super(MidiKeyboard, self).__initstate__()
        print(mido.get_input_names())
        try:
            self._midi.close()
        except Exception:
            pass
        try:
            self._midi = mido.open_input(self.midiPort)
        except OSError:
            self._midi = mido.open_input()
            self.midiPort = self._midi.name
            print(self.midiPort)
        self._on_notes = []
        self._pos = np.zeros(self.num_pixels)
        self._vel = np.zeros(self.num_pixels)

    def numInputChannels(self):
        return 3 # low, mid, high
    
    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "dampening": [0.99, 0.5, 1.0, 0.001],
                "tension": [0.001, 0.0, 1.0, 0.001],
                "spread": [0.1, 0.0, 1.0, 0.001],
                "midiPort": mido.get_input_names(),
                "scale_low": [1.0, 0.0, 1.0, 0.001],
                "scale_mid": [1.0, 0.0, 1.0, 0.001],
                "scale_high": [1.0, 0.0, 1.0, 0.001],
            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['dampening'][0] = self.dampening
        definition['parameters']['tension'][0] = self.tension
        definition['parameters']['spread'][0] = self.spread
        definition['parameters']['midiPort'] = [self.midiPort] + [x for x in mido.get_input_names() if x!=self.midiPort]
        definition['parameters']['scale_low'][0] = self.scale_low
        definition['parameters']['scale_mid'][0] = self.scale_mid
        definition['parameters']['scale_high'][0] = self.scale_high
        return definition

    async def update(self, dt):
        await super().update(dt)

        lDeltas = np.zeros(self.num_pixels) # force from left
        rDeltas = np.zeros(self.num_pixels) # force from right
        for j in range(4):
            # calculate delta to left and right pixel
            lDeltas[1:] = self.spread * (np.roll(self._pos,1)[1:] - self._pos[1:])
            rDeltas[:-1] = self.spread * (np.roll(self._pos,-1)[:-1] - self._pos[:-1])
            x = -self._pos
            force = lDeltas + rDeltas + x * self.tension
            acc = force / 1.0
            self._vel = self.dampening * self._vel + acc
            self._pos += self._vel
    
    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            lowCol = self.scale_low * np.ones(self.num_pixels) * np.array([[0], [0], [0]])
        else:
            lowCol = self.scale_low * self._inputBuffer[0]

        if not self._inputBufferValid(1):
            baseCol = self.scale_mid * np.ones(self.num_pixels) * np.array([[127], [127], [127]])
        else:
            baseCol = self.scale_mid * self._inputBuffer[1]

        if not self._inputBufferValid(2):
            highCol = self.scale_high * np.ones(self.num_pixels) * np.array([[255], [255], [255]])
        else:
            highCol = self.scale_high * self._inputBuffer[2]

        for msg in self._midi.iter_pending():
            if msg.type == 'note_on':
                self._on_notes.append(msg)
            if msg.type == 'note_off':
                toRemove = [note for note in self._on_notes if note.note == msg.note]
                for note in toRemove:
                    self._on_notes.remove(note)
        # Draw
        for note in self._on_notes:
            index = int(max(0, min(self.num_pixels - 1, float(note.note) / 127.0 * self.num_pixels)))
            self._pos[index] = -1 * note.velocity / 127.0
        
        # Output: Interpolate between low and mid for self._pos < 0, interpolate between mid and high for self._pos > 0
        out = np.zeros(self.num_pixels) * np.array([[0],[0],[0]])
        out[:, self._pos <= 0] = (np.multiply(1 + self._pos, baseCol) + np.multiply(-self._pos, lowCol))[:, self._pos <= 0]
        out[:, self._pos >= 0] = (np.multiply(self._pos, highCol) + np.multiply(1 - self._pos, baseCol))[:, self._pos >= 0]
        self._outputBuffer[0] = out


class Breathing(Effect):

    def __init__(self, num_pixels, cycle=5):
        self.num_pixels = num_pixels
        self.cycle = cycle
        self.__initstate__()

    def __initstate__(self):
        # state
        super(Breathing, self).__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def oneStar(self, t, cycle):
        brightness = 0.5 * math.sin((2 * math.pi) / cycle * t) + 0.5
        return brightness

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "cycle": [5, 0.1, 10, 0.1],
            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['cycle'][0] = self.cycle
        return definition

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self.num_pixels) * np.array([[255.0],[255.0],[255.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.cycle)
            self._output = np.multiply(color, np.ones(self.num_pixels) * np.array([[brightness],[brightness],[brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0,255.0)



class Heartbeat(Effect):

    def __init__(self, num_pixels, speed=1):
        self.num_pixels = num_pixels
        self.speed = speed
        self.__initstate__()

    def __initstate__(self):
        # state
        super(Heartbeat, self).__initstate__()

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def oneStar(self, t, speed):
        brightness = abs(math.sin(speed * t)**63 * math.sin(speed * t + 1.5)*8)
        return brightness

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "speed": [1, 0.1, 100, 0.1],
            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['speed'][0] = self.speed
        return definition

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self.num_pixels) * np.array([[255.0],[0.0],[0.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.speed)
            self._output = np.multiply(color, np.ones(self.num_pixels) * np.array([[brightness],[brightness],[brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0,255.0)



class FallingStars(Effect):

    def __init__(self, num_pixels, dim_speed=100, thickness=1, spawnTime=0.1, maxBrightness=1):
        self.num_pixels = num_pixels
        self.dim_speed = dim_speed
        self.thickness = thickness #getting down with it
        self.spawnTime = spawnTime
        self.maxBrightness = maxBrightness
        self.__initstate__()

    def __initstate__(self):
        # state
        self._t0Array = []
        self._spawnArray = []
        self._starCounter = 0
        self._spawnflag = True
        super(FallingStars, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "dim_speed": [100, 1, 1000, 1],
                "thickness": [1, 1, 300, 1],
                "spawntime": [1, 0.01, 10, 0.01],
                "maxBrightness": [1, 0, 1, 0.01],
            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['dim_speed'][0] = self.dim_speed
        definition['parameters']['thickness'][0] = self.thickness
        definition['parameters']['spawntime'][0] = self.spawnTime
        definition['parameters']['maxBrightness'][0] = self.maxBrightness
        return definition

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def spawnStar(self):
        self._starCounter += 1
        self._t0Array.append(self._t)
        self._spawnArray.append(random.randint(0,self.num_pixels-self.thickness))
        if self._starCounter > 100:
            self._starCounter -= 1
            self._t0Array.pop(0)
            self._spawnArray.pop(0)
        threading.Timer(self.spawnTime, self.spawnStar).start()     #executes itself every *spawnTime* seconds


    def allStars(self, t, dim_speed, thickness, t0, spawnSpot):
        controlArray = []
        for i in range(0,self._starCounter):
            oneStarArray = np.zeros(self.num_pixels)
            for j in range(0,thickness):
                oneStarArray[spawnSpot[i]+j] = math.exp(- (100/dim_speed) * (self._t - t0[i]))
            controlArray.append(oneStarArray)
        return controlArray


    def starControl(self, spawnTime):
        if self._spawnflag == True:
            self.spawnStar()
            self._spawnflag = False
        outputArray = self.allStars(self._t, self.dim_speed, self.thickness, self._t0Array, self._spawnArray)
        return np.sum(outputArray, axis=0)


    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self.num_pixels) * np.array([[255.0],[255.0],[255.0]])
        if self._outputBuffer is not None:
            self._output = np.multiply(color, self.starControl(self.spawnTime) * np.array([[self.maxBrightness*1.0],[self.maxBrightness*1.0],[self.maxBrightness*1.0]]))
        self._outputBuffer[0] = self._output.clip(0.0,255.0)
