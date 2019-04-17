from __future__ import (absolute_import, division, print_function, unicode_literals)

import math
import random
import threading
from collections import OrderedDict
import os.path

import numpy as np
import scipy as sp
from scipy import signal as signal

from audioled.effect import Effect

from PIL import Image, ImageOps


wave_modes = ['sin', 'sawtooth', 'sawtooth_reversed', 'square']
wave_mode_default = 'sin'
sortby = ['red', 'green', 'blue', 'brightness']
sortbydefault = 'red'


class SwimmingPool(Effect):
    """Generates a wave effect to look like the reflection on the bottom of a swimming pool."""

    @staticmethod
    def getEffectDescription():
        return \
            "Generates a wave effect to look like the reflection on the bottom of a swimming pool."

    def __init__(self, num_waves=30, scale=0.2, wavespread_low=30, wavespread_high=70, max_speed=30):
        self.num_waves = num_waves
        self.scale = scale
        self.wavespread_low = wavespread_low
        self.wavespread_high = wavespread_high
        self.max_speed = max_speed
        self.__initstate__()

    def __initstate__(self):
        # state
        try:
            self._pixel_state
        except AttributeError:
            self._pixel_state = None
        try:
            self._last_t
        except AttributeError:
            self._last_t = 0.0
        try:
            self._Wave
        except AttributeError:
            self._Wave = None
        try:
            self._WaveSpecSpeed
        except AttributeError:
            self._WaveSpecSpeed = None
        try:
            self._rotate_counter
        except AttributeError:
            self._rotate_counter = 0
        super(SwimmingPool, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_waves", [30, 1, 100, 1]),
                ("scale", [0.2, 0.01, 1.0, 0.01]),
                ("wavespread_low", [30, 1, 100, 1]),
                ("wavespread_high", [70, 50, 150, 1]),
                ("max_speed", [30, 1, 200, 1]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "num_waves": "Number of generated overlaying waves.",
                "scale": "Scales the brightness of the waves.",
                "wavespread_low": "Minimal spread of the randomly generated waves.",
                "wavespread_high": "Maximum spread of the randomly generated waves.",
                "max_speed": "Maximum movement speed of the waves."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['num_waves'][0] = self.num_waves
        definition['parameters']['scale'][0] = self.scale
        definition['parameters']['wavespread_low'][0] = self.wavespread_low
        definition['parameters']['wavespread_high'][0] = self.wavespread_high
        definition['parameters']['max_speed'][0] = self.max_speed
        return definition

    def _SinArray(self, _spread, _wavehight):
        # Create array for a single wave
        _CArray = []
        _spread = min(int(self._num_pixels / 2) - 1, _spread)
        for i in range(-_spread, _spread + 1):
            _CArray.append(math.sin((math.pi / _spread) * i) * _wavehight)
        _output = np.zeros(self._num_pixels)
        _output[:len(_CArray)] = _CArray
        # Move somewhere
        _output = np.roll(_output, np.random.randint(0, self._num_pixels), axis=0)
        return _output.clip(0.0, 255.0)

    def _CreateWaves(self, num_waves, wavespread_low=10, wavespread_high=50, max_speed=30):
        _WaveArray = []
        _wavespread = np.random.randint(wavespread_low, wavespread_high, num_waves)
        _WaveArraySpecSpeed = np.random.randint(-max_speed, max_speed, num_waves)
        _WaveArraySpecHeight = np.random.rand(num_waves)
        for i in range(0, num_waves):
            _WaveArray.append(self._SinArray(_wavespread[i], _WaveArraySpecHeight[i]))
        return _WaveArray, _WaveArraySpecSpeed

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    async def update(self, dt):
        await super().update(dt)
        if self._pixel_state is None or np.size(self._pixel_state, 1) != self._num_pixels:
            self._pixel_state = np.zeros(self._num_pixels) * np.array([[0.0], [0.0], [0.0]])
            self._Wave = None
            self._WaveSpecSpeed = None

        if self._Wave is None or self._WaveSpecSpeed is None or len(self._Wave) < self.num_waves:
            
            self._Wave, self._WaveSpecSpeed = self._CreateWaves(self.num_waves, self.wavespread_low,
                                                                self.wavespread_high, self.max_speed)
        # Rotate waves
        self._rotate_counter += 1
        if self._rotate_counter > 30:
            self._Wave = np.roll(self._Wave, 1, axis=0)
            self._WaveSpecSpeed = np.roll(self._WaveSpecSpeed, 1)
            speed = np.random.randint(-self.max_speed, self.max_speed)
            spread = np.random.randint(self.wavespread_low, self.wavespread_high)
            height = np.random.rand()
            wave = self._SinArray(spread, height)
            self._Wave[0] = wave
            self._WaveSpecSpeed[0] = speed
            self._rotate_counter = 0

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0):
            color = np.ones(self._num_pixels) * np.array([[255], [255], [255]])
        else:
            color = self._inputBuffer[0]

        
        all_waves = np.zeros(self._num_pixels)
        for i in range(0, self.num_waves):
            fact = 1.0
            if i == 0:
                fact = (self._rotate_counter / 30)
            if i == self.num_waves - 1:
                fact = (1.0 - self._rotate_counter / 30)
            if i < len(self._Wave) and i < len(self._WaveSpecSpeed):
                step = np.roll(self._Wave[i], int(self._t * self._WaveSpecSpeed[i]), axis=0) * self.scale * fact
                all_waves += step
        
        self._outputBuffer[0] = np.multiply(color, all_waves).clip(0, 255.0)


class DefenceMode(Effect):
    """Generates a colorchanging strobe light effect.
    The mode to defend against all kinds of attackers.
    """

    @staticmethod
    def getEffectDescription():
        return \
            "Generates a color-changing strobe light effect."

    def __init__(self, scale=0.2):
        self.scale = scale
        self.__initstate__()

    def __initstate__(self):
        # state
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
                self._output = np.ones(self._num_pixels) * np.array([[random.randint(
                    0.0, 255.0)], [random.randint(0.0, 255.0)], [random.randint(0.0, 255.0)]])
            else:
                self._output = np.zeros(self._num_pixels) * np.array([[0.0], [0.0], [0.0]])

            self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class MidiKeyboard(Effect):
    """Effect for handling midi inputs."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for handling midi inputs."

    class Note(object):
        def __init__(self, note, velocity, spawn_time):
            self.note = note
            self.velocity = velocity
            self.spawn_time = spawn_time
            self.active = True
            self.value = 0.0
            self.release_time = 0.0

    def __init__(self, midiPort='', attack=0.0, decay=0.0, sustain=1.0, release=0.0):

        self.midiPort = midiPort
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
        self.__initstate__()

    def __initstate__(self):
        super(MidiKeyboard, self).__initstate__()
        try:
            import mido
        except ImportError as e:
            print('Unable to import the mido library')
            print('You can install this library with `pip install mido`')
            raise e
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
    def getMidiPorts():
        try:
            import mido
            return mido.get_input_names()
        except ImportError:
            print('Unable to import the mido library')
            print('You can install this library with `pip install mido`')
            return []
        except Exception:
            print("Error while getting midi inputs")
            return []

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": {
                # default, min, max, stepsize
                "midiPort": MidiKeyboard.getMidiPorts(),
                "attack": [0.0, 0.0, 5.0, 0.01],
                "decay": [0.0, 0.0, 5.0, 0.01],
                "sustain": [1.0, 0.0, 1.0, 0.01],
                "release": [0.0, 0.0, 5.0, 0.01],
            }
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "midiPort": "Midi Port to use.",
                "attack": "Controls attack in pixel envelope.",
                "decay": "Controls decay in pixel envelope.",
                "sustain": "Controls sustain in pixel envelope.",
                "release": "Controls release in pixel envelope.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['midiPort'] = [self.midiPort
                                                ] + [x for x in MidiKeyboard.getMidiPorts() if x != self.midiPort]
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
            col = np.ones(self._num_pixels) * np.array([[255], [255], [255]])
        else:
            col = self._inputBuffer[0]

        # Draw
        pos = np.zeros(self._num_pixels)
        for note in self._on_notes:
            index = int(max(0, min(self._num_pixels - 1, float(note.note) / 127.0 * self._num_pixels)))
            pos[index] = 1 * note.value / 127.0
        self._outputBuffer[0] = np.multiply(pos, col)


class Breathing(Effect):
    """Effect for simulating breathing behavior over brightness."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for simulating breathing behavior over brightness."

    def __init__(self, cycle=5):
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
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("cycle", [5, 0.1, 10, 0.1]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "cycle": "Seconds to repeat a full cycle.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['cycle'][0] = self.cycle
        return definition

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.cycle)
            self._output = np.multiply(color,
                                       np.ones(self._num_pixels) * np.array([[brightness], [brightness], [brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class Heartbeat(Effect):
    """Effect for simulating a beating heart over brightness."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for simulating a beating heart over brightness."

    def __init__(self, speed=1):
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
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("speed", [1, 0.1, 100, 0.1]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "speed": "Speed of the heartbeat.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['speed'][0] = self.speed
        return definition

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self._num_pixels) * np.array([[255.0], [0.0], [0.0]])
        if self._outputBuffer is not None:
            brightness = self.oneStar(self._t, self.speed)
            self._output = np.multiply(color,
                                       np.ones(self._num_pixels) * np.array([[brightness], [brightness], [brightness]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class FallingStars(Effect):
    """Effect for creating random stars that fade over time."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for creating random stars that fade over time."

    def __init__(self, dim_speed=100, thickness=1, spawntime=0.1, max_brightness=1):
        self.dim_speed = dim_speed
        self.thickness = thickness  # getting down with it
        self.spawntime = spawntime
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
                ("dim_speed", [100, 1, 1000, 1]),
                ("thickness", [1, 1, 300, 1]),
                ("spawntime", [1, 0.01, 10, 0.01]),
                ("max_brightness", [1, 0, 1, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "dim_speed": "Time to fade out one star.",
                "thickness": "Thickness of one star in pixels.",
                "spawntime": "Time until a new star is spawned.",
                "max_brightness": "Maximum brightness of the stars."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['dim_speed'][0] = self.dim_speed
        definition['parameters']['thickness'][0] = self.thickness
        definition['parameters']['spawntime'][0] = self.spawntime
        definition['parameters']['max_brightness'][0] = self.max_brightness
        return definition

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def spawnStar(self):
        self._starCounter += 1
        self._t0Array.append(self._t)
        self._spawnArray.append(random.randint(0, self._num_pixels - self.thickness))
        if self._starCounter > 100:
            self._starCounter -= 1
            self._t0Array.pop(0)
            self._spawnArray.pop(0)
        threading.Timer(self.spawntime, self.spawnStar).start()  # executes itself every *spawnTime* seconds

    def allStars(self, t, dim_speed, thickness, t0, spawnSpot):
        controlArray = []
        for i in range(0, self._starCounter):
            oneStarArray = np.zeros(self._num_pixels)
            for j in range(0, thickness):
                if i < len(spawnSpot):
                    index = spawnSpot[i] + j
                    if index < self._num_pixels:
                        oneStarArray[index] = math.exp(-(100 / dim_speed) * (self._t - t0[i]))
            controlArray.append(oneStarArray)
        return controlArray

    def starControl(self, spawnTime):
        if self._spawnflag is True:
            self.spawnStar()
            self._spawnflag = False
        outputArray = self.allStars(self._t, self.dim_speed, self.thickness, self._t0Array, self._spawnArray)
        return np.sum(outputArray, axis=0)

    async def update(self, dt):
        await super().update(dt)

    def process(self):
        color = self._inputBuffer[0]
        if color is None:
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if self._outputBuffer is not None:
            self._output = np.multiply(
                color,
                self.starControl(self.spawntime) * np.array([[self.max_brightness * 1.0], [self.max_brightness * 1.0],
                                                             [self.max_brightness * 1.0]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class Pendulum(Effect):
    """Generates a blob of light to swing back and forth."""

    @staticmethod
    def getEffectDescription():
        return \
            "Generates a blob of light to swing back and forth."

    def __init__(self, spread=0.03, location=0.5, displacement=0.15, heightactivator=True, lightflip=True,
                 swingspeed=1):

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

    def __setstate__(self, state):
        if 'spread' in state and state['spread'] > 1:
            state['spread'] = state['spread'] / 300
        if 'location' in state and state['location'] > 1:
            state['location'] = state['location'] / 300
        if 'displacement' in state and state['displacement'] > 3:
            state['displacement'] = state['displacement'] / 300
        return super().__setstate__(state)

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("location", [0, 0, 1, 0.01]),
                ("displacement", [0.15, 0, 3, 0.01]),
                ("swingspeed", [1, 0, 5, 0.01]),
                ("heightactivator", False),
                ("lightflip", False),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "location": "Starting location and center to swing around.",
                "displacement": "Displacement of the pendulum to either side.",
                "swingspeed": "Speed of the pendulum.",
                "heightactivator": "Changes brightness of the pendulum depending on its location.",
                "lightflip": "Reverses the setting of heightactivator."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['location'][0] = self.location
        definition['parameters']['displacement'][0] = self.displacement
        definition['parameters']['heightactivator'] = self.heightactivator
        definition['parameters']['lightflip'] = self.lightflip
        definition['parameters']['swingspeed'][0] = self.swingspeed
        return definition

    def createBlob(self, spread_rel, location_rel):
        blobArray = np.zeros(self._num_pixels)
        spread = max(int(spread_rel * self._num_pixels), 1)
        location = int(location_rel * self._num_pixels)
        for i in range(-spread, spread + 1):
            if (location + i) >= 0 and (location + i) < self._num_pixels:
                blobArray[location + i] = math.cos((math.pi / spread) * i)
        return blobArray.clip(0.0, 255.0)

    def moveBlob(self, blobArray, displacement_rel, swingspeed):
        displacement = displacement_rel * self._num_pixels
        outputArray = sp.ndimage.interpolation.shift(
            blobArray, displacement * math.sin(self._t * swingspeed), mode='wrap', prefilter=True)
        return outputArray

    def controlBlobs(self):
        output = self.moveBlob(self.createBlob(self.spread, self.location), self.displacement, self.swingspeed)
        return output

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._inputBufferValid(0):
            color = self._inputBuffer[0]
        else:
            # default: all white
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if self.heightactivator is True:
            if self.lightflip is True:
                lightconfig = -1.0
            else:
                lightconfig = 1.0
            configArray = lightconfig * math.cos(2 * self._t) * np.array([[1.0], [1.0], [1.0]])
        else:
            configArray = np.array([[1.0], [1.0], [1.0]])
        self._output = np.multiply(color, self.controlBlobs() * configArray)
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class RandomPendulums(Effect):
    """Randomly generates a number of pendulums."""

    @staticmethod
    def getEffectDescription():
        return \
            "Randomly generates a number of pendulums."

    def __init__(self, num_pendulums=100, dim=0.1):
        self.num_pendulums = num_pendulums
        self.dim = dim
        self.__initstate__()

    def __initstate__(self):
        super(RandomPendulums, self).__initstate__()
        # state
        self._spread = []
        self._location = []
        self._displacement = []
        self._heightactivator = []
        self._lightflip = []
        self._offset = []
        self._swingspeed = []

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_pendulums", [20, 1, 300, 1]),
                ("dim", [1, 0, 1, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "num_pendulums": "Number of random pendulums.",
                "dim": "Overall brightness of the pendulums.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['num_pendulums'][0] = self.num_pendulums
        definition['parameters']['dim'][0] = self.dim
        return definition

    def createBlob(self, spread_rel, location_rel):
        blobArray = np.zeros(self._num_pixels)
        spread = max(int(spread_rel * self._num_pixels), 1)
        location = int(location_rel * self._num_pixels)
        for i in range(-spread, spread + 1):
            if (location + i) >= 0 and (location + i) < self._num_pixels:
                blobArray[location + i] = math.cos((math.pi / spread) * i)
        return blobArray.clip(0.0, 255.0)

    def moveBlob(self, blobArray, displacement_rel, offset_rel, swingspeed):
        config = displacement_rel * self._num_pixels * math.sin((self._t * swingspeed) + offset_rel * self._num_pixels)
        outputArray = sp.ndimage.interpolation.shift(blobArray, config, mode='wrap', prefilter=True)
        return outputArray.clip(0.0, 255.0)

    def controlBlobs(self, spread_rel, location_rel, displacement_rel, offset_rel, swingspeed):
        output = self.moveBlob(self.createBlob(spread_rel, location_rel), displacement_rel, offset_rel, swingspeed)
        return output

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    async def update(self, dt):
        await super().update(dt)
        if len(self._spread) == 0 or len(self._spread) != self.num_pendulums:
            self._spread = []
            self._location = []
            self._displacement = []
            self._heightactivator = []
            self._lightflip = []
            self._offset = []
            self._swingspeed = []
            for i in range(self.num_pendulums):
                rSpread = int(random.randint(2, 10) / 300 * self._num_pixels)
                self._spread.append(rSpread / 300)
                self._location.append(random.randint(0, self._num_pixels - rSpread - 1) / 300)
                self._displacement.append(random.randint(5, 50) / 300)
                self._heightactivator.append(random.choice([True, False]))
                self._lightflip.append(random.choice([True, False]))
                self._offset.append(random.uniform(0, 6.5) / 300)
                self._swingspeed.append(random.uniform(0, 1))

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._inputBufferValid(0):
            color = self._inputBuffer[0]
        else:
            # default: all white
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])

        self._output = np.zeros(self._num_pixels) * np.array([[0.0], [0.0], [0.0]])
        for i in range(self.num_pendulums):
            if self._heightactivator[i] is True:
                if self._lightflip[i] is True:
                    lightconfig = -1.0
                else:
                    lightconfig = 1.0
                configArray = lightconfig * self.dim * math.cos(2 * self._t + self._offset[i]) * np.array([[1.0], [1.0],
                                                                                                           [1.0]])
            else:
                configArray = np.array([[1.0 * self.dim], [1.0 * self.dim], [1.0 * self.dim]])
            self._output += np.multiply(
                color,
                self.controlBlobs(self._spread[i], self._location[i], self._displacement[i], self._offset[i],
                                  self._swingspeed[i]) * configArray)
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class StaticBlob(Effect):
    """Generates a blob of light. Mostly for testing purposes."""

    @staticmethod
    def getEffectDescription():
        return \
            "Generates a blob of light. Mostly for testing purposes."

    def __init__(self, spread=50, location=150):
        self.spread = spread
        self.location = location
        self.__initstate__()

    def __initstate__(self):
        # state
        super(StaticBlob, self).__initstate__()

    def __setstate__(self, state):
        # Backwards compatibility from absolute -> relative sizes
        if 'spread' in state and state['spread'] > 1:
            state['spread'] = state['spread'] / 300 / 2
        if 'location' in state and state['location'] > 1:
            state['location'] = state['location'] / 300
        return super().__setstate__(state)

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("location", [0.5, 0, 1, 0.01]),
                ("spread", [0.3, 0, 1, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {"parameters": {"location": "Location where the blob is created.", "spread": "Spreading of the blob."}}
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['location'][0] = self.location
        definition['parameters']['spread'][0] = self.spread
        return definition

    def createBlob(self, spread_rel, location_rel):
        blobArray = np.zeros(self._num_pixels)

        # convert relative to absolute values
        spread = max(int(spread_rel * self._num_pixels), 1)
        location = int(location_rel * self._num_pixels)
        for i in range(-spread, spread + 1):
            # make sure we are in bounds of array
            if (location + i) >= 0 and (location + i) < self._num_pixels:
                blobArray[location + i] = math.cos((math.pi / spread) * i)
        return blobArray.clip(0.0, 255.0)

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._inputBufferValid(0):
            color = self._inputBuffer[0]
        else:
            # default: all white
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        self._output = np.multiply(color, self.createBlob(self.spread, self.location) * np.array([[1.0], [1.0], [1.0]]))

        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class GenerateWaves(Effect):
    """Effect for displaying different wave forms."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for displaying different wave forms."

    def __init__(
            self,
            wavemode=wave_mode_default,
            period=20,
            scale=1,
    ):

        self.period = period
        self.scale = scale
        self.wavemode = wavemode
        self.__initstate__()

    def __initstate__(self):
        # state
        self._wavearray = None
        self._outputarray = []

        super(GenerateWaves, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("period", [20, 1, 300, 1]),
                ("scale", [1, 0.01, 1, 0.01]),
                ("wavemode", wave_modes),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "period": "Spread of one wave.",
                "scale": "Overall brightness of the effect.",
                "wavemode": "Selection of different wave forms."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['period'][0] = self.period
        definition['parameters']['scale'][0] = self.scale
        definition['parameters']['wavemode'] = [self.wavemode] + [x for x in wave_modes if x != self.wavemode]
        return definition

    def createSin(self, period, scale):
        outputarray = np.zeros(self._num_pixels)
        for i in range(0, self._num_pixels):
            outputarray[i] = 0.5 * scale - math.sin(math.pi / self.period * i) * 0.5 * scale
        return outputarray

    def createSawtooth(self, period, scale):
        outputarray = np.linspace(0, self._num_pixels, self._num_pixels)
        outputarray = 0.5 * scale - signal.sawtooth(outputarray * math.pi / self.period, width=1) * 0.5 * scale
        return outputarray

    def createSawtoothReversed(self, period, scale):
        outputarray = np.linspace(0, self._num_pixels, self._num_pixels)
        outputarray = 0.5 * scale - signal.sawtooth(outputarray * math.pi / self.period, width=0) * 0.5 * scale
        return outputarray

    def createSquare(self, period, scale):
        outputarray = np.linspace(0, self._num_pixels, self._num_pixels)
        outputarray = 0.5 * scale - signal.square(outputarray * math.pi / self.period) * 0.5 * scale
        return outputarray

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        return 1

    async def update(self, dt):
        await super().update(dt)
        if self._wavearray is None or len(self._wavearray) != self._num_pixels:
            if self.wavemode == 'sin':
                self._wavearray = self.createSin(self.period, self.scale)
            elif self.wavemode == 'sawtooth':
                self._wavearray = self.createSawtooth(self.period, self.scale)
            elif self.wavemode == 'sawtooth_reversed':
                self._wavearray = self.createSawtoothReversed(self.period, self.scale)
            elif self.wavemode == 'square':
                self._wavearray = self.createSquare(self.period, self.scale)

    def process(self):
        if self._outputBuffer is not None:
            color = self._inputBuffer[0]
            if color is None:
                color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])

            output = np.multiply(color, self._wavearray * np.array([[1.0], [1.0], [1.0]]))

            self._outputBuffer[0] = output.clip(0.0, 255.0)


class Sorting(Effect):
    """Effect for sorting an input by color or brightness."""

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for sorting an input by color or brightness."

    def __init__(
            self,
            sortby=sortbydefault,
            reversed=False,
            looping=True,
    ):

        self.sortby = sortby
        self.reversed = reversed
        self.looping = looping
        self.__initstate__()

    def __initstate__(self):
        # state
        self._output = None
        self._sorting_done = True
        super(Sorting, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("sortby", sortby),
                ("reversed", False),
                ("looping", True)
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "sortby":
                "Parameter which the effect sorts by.",
                "reversed":
                "Flips the parameter which is sorted by.",
                "looping":
                "If activated, the effect randomly picks another parameter to sort by. "
                "If deactivated, the effects spawns a new pattern after sorting."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['sortby'] = [self.sortby] + [x for x in sortby if x != self.sortby]
        definition['parameters']['reversed'] = self.reversed
        definition['parameters']['looping'] = self.looping
        return definition

    def disorder(self):
        self._output = np.ones(self._num_pixels) * np.array([[1.0], [1.0], [1.0]])
        for i in range(self._num_pixels):
            for j in range(len(self._output)):
                self._output[j][i] = random.randint(0.0, 255.0)
        return self._output

    def bubble(self, inputArray, sortby, reversed, looping):
        if sortby == 'red':
            sortindex = 0
        elif sortby == 'green':
            sortindex = 1
        elif sortby == 'blue':
            sortindex = 2
        elif sortby == 'brightness':
            sortindex = 3
        else:
            raise NotImplementedError("Sorting not implemented.")

        if reversed:
            flip_index = -1
        else:
            flip_index = 1

        for passnum in range(len(inputArray[0]) - 1, 0, -1):
            check = 0
            for i in range(passnum):
                if sortindex == 0 or sortindex == 1 or sortindex == 2:  # sorting by color
                    if inputArray[sortindex][i] > inputArray[sortindex][i + 1 * flip_index]:
                        temp = np.array([[1.0], [1.0], [1.0]])
                        for j in range(len(inputArray)):
                            temp[j] = inputArray[j][i]
                            inputArray[j][i] = inputArray[j][i + 1 * flip_index]
                            inputArray[j][i + 1 * flip_index] = temp[j]
                    else:
                        check += 1
                        if check == passnum:
                            if looping is True:
                                self.sortby = random.choice(['red', 'green', 'blue', 'brightness'])
                                self.reversed = random.choice([True, False])
                            else:
                                self._sorting_done = True

                elif sortindex == 3:  # sorting by brightness
                    tempArray = np.sum(inputArray, axis=0)
                    if tempArray[i] > tempArray[i + 1 * flip_index]:
                        temp = np.array([[1.0], [1.0], [1.0]])
                        for j in range(len(inputArray)):
                            temp[j] = inputArray[j][i]
                            inputArray[j][i] = inputArray[j][i + 1 * flip_index]
                            inputArray[j][i + 1 * flip_index] = temp[j]
                    else:
                        check += 1
                        if check == passnum:
                            if looping is True:
                                self.sortby = random.choice(['red', 'green', 'blue', 'brightness'])
                                self.reversed = random.choice([True, False])
                            else:
                                self._sorting_done = True
            return inputArray

    def numInputChannels(self):
        return 0

    def numOutputChannels(self):
        return 1

    async def update(self, dt):
        await super().update(dt)
        if self._output is None or np.size(self._output, 1) != self._num_pixels:
            self._output = self.disorder()
            self._sorting_done = False

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return

        if self._sorting_done is True:
            self._output = self.disorder()
            self._sorting_done = False

        self._output = self.bubble(self._output, self.sortby, self.reversed, self.looping)
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class GIFPlayer(Effect):

    @staticmethod
    def getEffectDescription():
        return \
            "Effect for displaying GIFs on LED panels."

    def __init__(self, gif_file, fps=30, center_x=0.5, center_y=0.5):
        self.file = gif_file
        self.fps = fps
        self.center_x = center_x
        self.center_y = center_y
        self.__initstate__()

    def __initstate__(self):
        super(GIFPlayer, self).__initstate__()
        self._last_t = 0.0
        self._cur_index = 0
        self._cur_image = None
        self._gif = None
        self._openGif()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("fps", [30, 0, 120, 0.1]),
                ("center_x", [0.5, 0, 1, 0.01]),
                ("center_y", [0.5, 0, 1, 0.01]),
                ("file", ['gif', None])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "fps":
                "The number of frames per second for GIF playback.",
                "center_x":
                "Moves the GIF left or right if the image is being cropped.",
                "center_y":
                "Moves the GIF up or down if the image is being cropped.",
                "file":
                "The GIF to show."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['fps'][0] = self.fps
        definition['parameters']['center_x'][0] = self.center_x
        definition['parameters']['center_y'][0] = self.center_y
        definition['parameters']['file'][1] = self.file
        return definition

    def numInputChannels(self):
        return 0

    def numOutputChannels(self):
        return 1

    def _openGif(self):
        adjustedFile = self.file
        if self.file is None:
            return
        if self._filterGraph is not None and self._filterGraph._project is not None and self._filterGraph._project._contentRoot is not None:
            adjustedFile = os.path.join(self._filterGraph._project._contentRoot, self.file)
        try:
            self._gif = Image.open(adjustedFile)
        except Exception:
            print("Cannot open file {}".format(adjustedFile))

    async def update(self, dt):
        await super().update(dt)
        if self._t - self._last_t > 1.0 / self.fps:
            # go to next image
            try:
                self._gif.seek(self._gif.tell() + 1)
            except Exception:
                self._openGif()
            
            num_cols = int(self._num_pixels / self._num_rows)
            # Resize image
            if self._gif is not None:
                self._cur_image = ImageOps.fit(self._gif.convert('RGB'), (num_cols, self._num_rows), Image.ANTIALIAS, centering=(self.center_x, self.center_y))
            # update time
            self._last_t = self._t

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._cur_image is not None:

            img = np.asarray(self._cur_image, dtype=np.uint8)
            img = img.reshape(-1, img.shape[-1]).T
            self._outputBuffer[0] = img
