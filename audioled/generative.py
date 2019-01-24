from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import math
import random
import threading
from collections import OrderedDict

import mido
import numpy as np
from scipy import signal

from audioled.effect import Effect

wave_modes = ['sin', 'sawtooth', 'sawtooth_reversed', 'square']
wave_mode_default = 'sin'


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
        self._Wave, self._WaveSpecSpeed = self._CreateWaves(self.num_waves, self.scale, self.wavespread_low,
                                                            self.wavespread_high, self.max_speed)
        super(SwimmingPool, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("num_waves", [30, 1, 100, 1]),
                ("scale", [0.2, 0.01, 1.0, 0.01]),
                ("wavespread_low", [30, 1, 100, 1]),
                ("wavespread_high", [70, 50, 150, 1]),
                ("max_speed", [30, 1, 200, 1]),
            ])
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
        for i in range(-_spread, _spread + 1):
            _CArray.append(math.sin((math.pi / _spread) * i) * _scale * _wavehight)
            _output = np.copy(self._pixel_state)
            _output[0][:len(_CArray)] += _CArray
            _output[1][:len(_CArray)] += _CArray
            _output[2][:len(_CArray)] += _CArray
        return _output.clip(0.0, 255.0)

    def _CreateWaves(self, num_waves, scale, wavespread_low=10, wavespread_high=50, max_speed=30):
        _WaveArray = []
        _wavespread = np.random.randint(wavespread_low, wavespread_high, num_waves)
        _WaveArraySpecSpeed = np.random.randint(-max_speed, max_speed, num_waves)
        _WaveArraySpecHeight = np.random.rand(num_waves)
        for i in range(0, num_waves):
            _WaveArray.append(self._SinArray(_wavespread[i], scale, _WaveArraySpecHeight[i]))
        return _WaveArray, _WaveArraySpecSpeed

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            self._output = np.multiply(color, 0.5 * np.zeros(self.num_pixels))

            for i in range(0, self.num_waves):
                step = np.multiply(color, np.roll(self._Wave[i], int(self._t * self._WaveSpecSpeed[i]), axis=1))
                self._output += step

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


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
            # color = self._inputBuffer[0]
            A = random.choice([True, False, False])
            if A is True:
                self._output = np.ones(self.num_pixels) * np.array([[random.randint(
                    0.0, 255.0)], [random.randint(0.0, 255.0)], [random.randint(0.0, 255.0)]])
            else:
                self._output = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class MidiKeyboard(Effect):
    class Note(object):
        def __init__(self, note, velocity, spawn_time):
            self.note = note
            self.velocity = velocity
            self.spawn_time = spawn_time
            self.active = True
            self.value = 0.0
            self.release_time = 0.0

    def __init__(self, num_pixels, midiPort='', attack=0.0, decay=0.0, sustain=1.0, release=0.0):
        self.num_pixels = num_pixels
        self.midiPort = midiPort
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
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

    def numInputChannels(self):
        return 1  # color

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "num_pixels": [300, 1, 1000, 1],
                "midiPort": mido.get_input_names(),
                "attack": [0.0, 0.0, 5.0, 0.01],
                "decay": [0.0, 0.0, 5.0, 0.01],
                "sustain": [1.0, 0.0, 1.0, 0.01],
                "release": [0.0, 0.0, 5.0, 0.01],
            }
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['midiPort'] = [self.midiPort
                                                ] + [x for x in mido.get_input_names() if x != self.midiPort]
        definition['parameters']['attack'][0] = self.attack
        definition['parameters']['decay'][0] = self.decay
        definition['parameters']['sustain'][0] = self.sustain
        definition['parameters']['release'][0] = self.release
        return definition

    async def update(self, dt):
        await super().update(dt)
        # Process midi notes
        for msg in self._midi.iter_pending():
            if msg.type == 'note_on':
                self._on_notes.append(MidiKeyboard.Note(msg.note, msg.velocity, self._t))
            if msg.type == 'note_off':
                toRemove = [note for note in self._on_notes if note.note == msg.note]
                for note in toRemove:
                    note.active = False
                    note.release_time = self._t

        # Process note states
        for note in self._on_notes:
            if note.active:

                if self._t - note.spawn_time < self.attack:
                    # attack phase
                    note.value = note.velocity * (self._t - note.spawn_time) / self.attack
                elif self._t - note.spawn_time < self.attack + self.decay:
                    # decay phase
                    # time since attack phase ended: self._t - note.spawn_time - self.attack
                    decay_fact = 1.0 - (self._t - note.spawn_time - self.attack) / self.decay
                    # linear interpolation
                    # decay_fact = 0.0: decay beginning -> 1.0
                    # decay_fact = 1.0: decay ending -> sustain
                    note.value = note.velocity * (self.sustain + (1.0 - self.sustain) * decay_fact)
                else:
                    # sustain phase
                    note.value = note.velocity * self.sustain
            else:
                # release phase
                if self._t - note.release_time < self.release:
                    note.value = note.velocity * (1.0 - (self._t - note.release_time) / self.release) * self.sustain
                else:
                    self._on_notes.remove(note)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            col = np.ones(self.num_pixels) * np.array([[255], [255], [255]])
        else:
            col = self._inputBuffer[0]

        # Draw
        pos = np.zeros(self.num_pixels)
        for note in self._on_notes:
            index = int(max(0, min(self.num_pixels - 1, float(note.note) / 127.0 * self.num_pixels)))
            pos[index] = 1 * note.value / 127.0
        self._outputBuffer[0] = np.multiply(pos, col)


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
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("cycle", [5, 0.1, 10, 0.1]),
            ])
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
            color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.cycle)
            self._output = np.multiply(color,
                                       np.ones(self.num_pixels) * np.array([[brightness], [brightness], [brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


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
        brightness = abs(math.sin(speed * t)**63 * math.sin(speed * t + 1.5) * 8)
        return brightness

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("speed", [1, 0.1, 100, 0.1]),
            ])
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
            color = np.ones(self.num_pixels) * np.array([[255.0], [0.0], [0.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.speed)
            self._output = np.multiply(color,
                                       np.ones(self.num_pixels) * np.array([[brightness], [brightness], [brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class FallingStars(Effect):

    def __init__(self, num_pixels, dim_speed=100, thickness=1, spawnTime=0.1, max_brightness=1):
        self.num_pixels = num_pixels
        self.dim_speed = dim_speed
        self.thickness = thickness  # getting down with it
        self.spawnTime = spawnTime
        self.max_brightness = max_brightness
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
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("dim_speed", [100, 1, 1000, 1]),
                ("thickness", [1, 1, 300, 1]),
                ("spawntime", [1, 0.01, 10, 0.01]),
                ("maxBrightness", [1, 0, 1, 0.01]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['dim_speed'][0] = self.dim_speed
        definition['parameters']['thickness'][0] = self.thickness
        definition['parameters']['spawntime'][0] = self.spawnTime
        definition['parameters']['max_brightness'][0] = self.maxBrightness
        return definition

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def spawnStar(self):
        self._starCounter += 1
        self._t0Array.append(self._t)
        self._spawnArray.append(random.randint(0, self.num_pixels - self.thickness))
        if self._starCounter > 100:
            self._starCounter -= 1
            self._t0Array.pop(0)
            self._spawnArray.pop(0)
        threading.Timer(self.spawnTime, self.spawnStar).start()  # executes itself every *spawnTime* seconds

    def allStars(self, t, dim_speed, thickness, t0, spawnSpot):
        controlArray = []
        for i in range(0, self._starCounter):
            oneStarArray = np.zeros(self.num_pixels)
            for j in range(0, thickness):
                oneStarArray[spawnSpot[i] + j] = math.exp(-(100 / dim_speed) * (self._t - t0[i]))
            controlArray.append(oneStarArray)
        return controlArray

    def starControl(self, spawnTime):
        if self._spawnflag is True:
            self.spawnStar()
            self._spawnflag = False
        outputArray = self.allStars(self._t, self.dim_speed, self.thickness, self._t0Array, self._spawnArray)
        return np.sum(outputArray, axis=0)

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if self._outputBuffer is not None:
            self._output = np.multiply(color, self.starControl(self.spawnTime) * np.array([[self.maxBrightness*1.0],
                                                                                           [self.maxBrightness*1.0],
                                                                                           [self.maxBrightness*1.0]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class Pendulum(Effect):

    def __init__(self,
                 num_pixels,
                 spread=10,
                 location=150,
                 displacement=50,
                 heightactivator=True,
                 lightflip=1,
                 swingspeed=1):
        self.num_pixels = num_pixels
        self.spread = spread
        self.location = location
        self.displacement = displacement
        self.heightactivator = heightactivator
        self.lightflip = lightflip
        self.swingspeed = swingspeed
        self.__initstate__()

    def __initstate__(self):
        # state
        super(Pendulum, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("location", [150, 0, 300, 1]),
                ("displacement", [50, 1, 1000, 1]),
                ("swingspeed", [1, 0, 5, 0.01]),
                ("heightactivator", False),
                ("lightflip", [1, -1, 1, 2]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['location'][0] = self.location
        definition['parameters']['displacement'][0] = self.displacement
        definition['parameters']['heightactivator'] = self.heightactivator
        definition['parameters']['lightflip'][0] = self.lightflip
        definition['parameters']['swingspeed'][0] = self.swingspeed
        return definition

    def createBlob(self, spread, location):
        blobArray = np.zeros(self.num_pixels)
        for i in range(-spread, spread+1):
            blobArray[location + i] = math.sin((math.pi/spread) * i)
        return blobArray.clip(0.0, 255.0)

    def moveBlob(self, blobArray, displacement, swingspeed):
        outputArray = np.roll(blobArray, int(displacement * math.sin(self._t * swingspeed)))
        return outputArray.clip(0.0, 255.0)

    def controlBlobs(self):
        output = self.moveBlob(self.createBlob(self.spread, self.location), self.displacement, self.swingspeed)
        return output

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            if color is None:
                color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])
            if self.heightactivator is True:
                configArray = np.array([[self.lightflip*math.cos(2*self._t)],
                                        [self.lightflip*math.cos(2*self._t)],
                                        [self.lightflip*math.cos(2*self._t)]])
            else:
                configArray = np.array([[1.0], [1.0], [1.0]])
            self._output = np.multiply(color, self.controlBlobs() * configArray)
            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class RPendulum(Effect):

    def __init__(self, num_pixels, num_pendulums=100, dim=0.1):
        self.num_pixels = num_pixels
        self.num_pendulums = num_pendulums
        self.dim = dim
        self._spread = []
        self._location = []
        self._displacement = []
        self._heightactivator = []
        self._lightflip = []
        self._offset = []
        self._swingspeed = []
        self.__initstate__()

    def __initstate__(self):
        # state
        for i in range(self.num_pendulums):
            self._spread.append(random.randint(2, 10))
            self._location.append(random.randint(0, self.num_pixels-self._spread[i]-1))
            self._displacement.append(random.randint(5, 50))
            self._heightactivator.append(random.choice([True, False]))
            self._lightflip.append(random.choice([-1, 1]))
            self._offset.append(random.uniform(0, 6.5))
            self._swingspeed.append(random.uniform(0, 1))
        super(RPendulum, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("num_pendulums", [20, 1, 300, 1]),
                ("dim", [1, 0, 1, 0.01]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['num_pendulums'][0] = self.num_pendulums
        definition['parameters']['dim'][0] = self.dim
        return definition

    def createBlob(self, spread, location):
        blobArray = np.zeros(self.num_pixels)
        for i in range(-spread, spread+1):
            blobArray[location + i] = math.sin((math.pi/spread) * i)
        return blobArray.clip(0.0, 255.0)

    def moveBlob(self, blobArray, displacement, offset, swingspeed):
        outputArray = np.roll(blobArray, int(displacement * math.sin((self._t * swingspeed) + offset)))
        return outputArray.clip(0.0, 255.0)

    def controlBlobs(self, spread, location, displacement, offset, swingspeed):
        output = self.moveBlob(self.createBlob(spread, location), displacement, offset, swingspeed)
        return output

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            if color is None:
                color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])

            self._output = np.zeros(self.num_pixels) * np.array([[0.0], [0.0], [0.0]])
            for i in range(self.num_pendulums):
                if self._heightactivator[i] is True:
                    configArray = np.array([[self._lightflip[i]*self.dim*math.cos(2*self._t+self._offset[i])],
                                            [self._lightflip[i]*self.dim*math.cos(2*self._t+self._offset[i])],
                                            [self._lightflip[i]*self.dim*math.cos(2*self._t+self._offset[i])]])
                else:
                    configArray = np.array([[1.0*self.dim], [1.0*self.dim], [1.0*self.dim]])
                self._output += np.multiply(color, self.controlBlobs(self._spread[i],
                                                                     self._location[i],
                                                                     self._displacement[i],
                                                                     self._offset[i],
                                                                     self._swingspeed[i]) * configArray)
            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class TestBlob(Effect):

    def __init__(self, num_pixels, spread=50, location=150):
        self.num_pixels = num_pixels
        self.spread = spread
        self.location = location
        self.__initstate__()

    def __initstate__(self):
        # state
        super(TestBlob, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("location", [150, 0, 300, 1]),
                ("spread", [50, 1, 300, 1]),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['location'][0] = self.location
        definition['parameters']['spread'][0] = self.spread
        return definition

    def createBlob(self, spread, location):
        blobArray = np.zeros(self.num_pixels)
        for i in range(-spread, spread+1):
            blobArray[location + i] = math.sin((math.pi/spread) * i)
        return blobArray.clip(0.0, 255.0)

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            if color is None:
                color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])

            self._output = np.multiply(color, self.createBlob(self.spread,
                                                              self.location) * np.array([[1.0], [1.0], [1.0]]))

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class GenerateWaves(Effect):
    """Effect for displaying different wave forms."""
    
    def __init__(self, num_pixels, wavemode=wave_mode_default, period=20, scale=1, ):
        self.num_pixels = num_pixels
        self.period = period
        self.scale = scale
        self.wavemode = wavemode
        self._wavearray = np.zeros(self.num_pixels)
        self._outputarray = []
        self.__initstate__()

    def __initstate__(self):
        # state
        if self.wavemode == 'sin':
            self._wavearray = self.createSin(self.period, self.scale)
        elif self.wavemode == 'sawtooth':
            self._wavearray = self.createSawtooth(self.period, self.scale)
        elif self.wavemode == 'sawtooth_reversed':
            self._wavearray = self.createSawtoothReversed(self.period, self.scale)
        elif self.wavemode == 'square':
            self._wavearray = self.createSquare(self.period, self.scale)
        super(GenerateWaves, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pixels", [300, 1, 1000, 1]),
                ("period", [20, 1, 300, 1]),
                ("scale", [1, 0.01, 1, 0.01]),
                ("wavemode", wave_modes),
            ])
        }
        return definition

    def getParameter(self):
        definition = self.getParameterDefinition()
        del definition['parameters']['num_pixels']
        definition['parameters']['period'][0] = self.period
        definition['parameters']['scale'][0] = self.scale
        definition['parameters']['wavemode'] = [self.wavemode] + [x for x in wave_modes if x != self.wavemode]
        return definition

    def createSin(self, period, scale):
        outputarray = np.zeros(self.num_pixels)
        for i in range(0, self.num_pixels):
            outputarray[i] = 0.5 * scale - math.sin(math.pi / self.period * i) * 0.5 * scale
        return outputarray
    
    def createSawtooth(self, period, scale):
        outputarray = np.linspace(0,300,300)
        outputarray = 0.5 * scale - signal.sawtooth(outputarray * math.pi / self.period, width=1) * 0.5 * scale
        return outputarray

    def createSawtoothReversed(self, period, scale):
        outputarray = np.linspace(0,300,300)
        outputarray = 0.5 * scale - signal.sawtooth(outputarray * math.pi / self.period, width=0) * 0.5 * scale
        return outputarray
    
    def createSquare(self, period, scale):
        outputarray = np.linspace(0,300,300)
        outputarray = 0.5 * scale - signal.square(outputarray * math.pi / self.period) * 0.5 * scale
        return outputarray
    
    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            if color is None:
                color = np.ones(self.num_pixels) * np.array([[255.0], [255.0], [255.0]])

            self._output = np.multiply(color, self._wavearray * np.array([[1.0], [1.0], [1.0]]))

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)
