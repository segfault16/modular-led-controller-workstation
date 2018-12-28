from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import asyncio
import colorsys
import math
import random
import struct
import time
import mido

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

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class MidiKeyboard(Effect):
    def __init__(self, num_pixels, dampening=0.99, tension=0.001, spread=0.1, midiPort=''):
        self.num_pixels = num_pixels
        self.dampening = dampening
        self.tension = tension
        self.spread = spread
        self.midiPort = midiPort
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
        return 2
    
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
                "midiPort": mido.get_input_names()
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
        return definition

    async def update(self, dt):
        await super().update(dt)

        lDeltas = np.zeros(self.num_pixels) # force from left
        rDeltas = np.zeros(self.num_pixels) # force from right
        for j in range(4):
            for i in range(self.num_pixels):
                if i > 0:
                    lDeltas[i] = self.spread * (self._pos[i-1] - self._pos[i])
                    
                if i < self.num_pixels - 1:
                    rDeltas[i] = self.spread * (self._pos[i+1] - self._pos[i])
            x = -self._pos
            force = lDeltas + rDeltas + x * self.tension
            acc = force / 1.0
            self._vel = self.dampening * self._vel + acc
            self._pos += self._vel
    
    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            baseCol = np.ones(self.num_pixels) * np.array([[255],[255],[255]])
        else:
            baseCol = self._inputBuffer[0]
        if not self._inputBufferValid(1):
            colGrad = None
        else:
            colGrad = self._inputBuffer[1]
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
        if colGrad is None:
            self._outputBuffer[0] = np.multiply((0.5 + self._pos), baseCol)
        else:
            # Create lookup
            index = np.clip((0.5 + 0.5 * self._pos) * self.num_pixels, 0, self.num_pixels - 1).astype(int)
            self._outputBuffer[0] = np.multiply((0.5 + self._pos), colGrad[:, index])
        
        

# class PrimitiveKeyboard(Effect):
#     #needs import keyboard and terminal run as sudo
#     #press 'w' to trigger defence mode


#     def __init__(self, num_pixels, explodeAtPixel=100, _trigger=False, broadness=50, scale=0.2):
#         self.num_pixels = num_pixels
#         self.explodeAtPixel = explodeAtPixel
#         self._trigger = _trigger
#         self.broadness = broadness
#         self.scale = scale
#         self.__initstate__()

#     def __initstate__(self):
#         # state
#         self._pixel_state = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])
#         self._last_t = 0.0
#         super(PrimitiveKeyboard, self).__initstate__()

#     def numInputChannels(self):
#         return 1

#     def numOutputChannels(self):
#         return 1

#     def process(self):
#         if self._outputBuffer is not None:
#             if keyboard.is_pressed('w') == True:
#                 #print('You Pressed A Key!')
#                 self._output = np.ones(self.num_pixels) * np.array([[random.randint(0.0,255.0)], [random.randint(0.0,255.0)], [random.randint(0.0,255.0)]])
#             else:
#                 self._output = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])
#             self._outputBuffer[0] = self._output.clip(0.0,255.0)
