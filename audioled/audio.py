from __future__ import (absolute_import, division, print_function, unicode_literals)

import time
from collections import OrderedDict

import numpy as np
import pyaudio

from audioled.effects import Effect
from audioled.effect import AudioBuffer


def print_audio_devices():
    """Print information about the system's audio devices"""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(info['name'])
        print('\tDevice index:', info['index'])
        print('\tSample rate:', info['defaultSampleRate'])
        print('\tMax input channels:', info['maxInputChannels'])
        print('\tMax output channels:', info['maxOutputChannels'])
    p.terminate()


def numInputChannels(device_index=None):
    p = pyaudio.PyAudio()
    device = device_index
    defaults = p.get_default_host_api_info()
    if device_index is None:
        device = defaults['defaultInputDevice']
    info = p.get_device_info_by_index(device)
    p.terminate()
    return info['maxInputChannels']


class GlobalAudio():
    device_index = None
    buffer = None
    chunk_rate = None
    sample_rate = None

    def __init__(self, device_index=None, chunk_rate=60, num_channels=1):
        GlobalAudio.device_index = device_index
        GlobalAudio.chunk_rate = chunk_rate
        self.num_channels = num_channels
        try:
            self.global_stream, GlobalAudio.sample_rate = self.stream_audio(device_index, chunk_rate, num_channels)
        except:
            print("!!! Fatal error in audio device !!!")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        chunk = np.fromstring(in_data, np.float32).astype(np.float)
        GlobalAudio.buffer = chunk
        return (None, pyaudio.paContinue)

    def _open_input_stream(self, chunk_length, device_index=None, channels=1, retry=0):
        """Opens a PyAudio audio input stream

        Parameters
        ----------
        device_index: int, optional
            Device index for the PyAudio audio input stream.
            If device index is not specified then the default audio device
            will be opened.
        """
        p = pyaudio.PyAudio()
        defaults = p.get_default_host_api_info()

        print("Using audio device {}".format(device_index))
        device_info = p.get_device_info_by_index(device_index)

        if device_info['maxInputChannels'] == 0:
            err = 'Your audio input device cannot be opened. '
            err += 'Change default audio device or try a different device index. '
            err += 'Device info:\n{}\n{}'.format(defaults, device_info)
            raise OSError(err)

        try:
            frameRate = int(device_info['defaultSampleRate'])
            stream = p.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=frameRate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=chunk_length,
                stream_callback=self._audio_callback)
            stream.start_stream()
            print("Started stream on device {}, fs: {}, chunk_length: {}".format(device_index, frameRate, chunk_length))
            GlobalAudio.buffer = np.zeros(chunk_length)
        except OSError as e:
            if retry == 5:
                err = 'Error occurred while attempting to open audio device. '
                err += 'Check your operating system\'s audio device configuration. '
                err += 'Audio device information: \n'
                err += str(device_info)
                print(err)
                raise e
            time.sleep(retry)
            return self._open_input_stream(chunk_length, device_index=device_index, channels=channels, retry=retry + 1)
        return stream, int(device_info['defaultSampleRate'])

    def stream_audio(self, device_index=None, chunk_rate=60, channels=1):
        if device_index == -1:
            print("Audio device disabled by device_index -1.")
            return None, None
        if device_index is None:
            print("No device_index for audio given. Using default.")
            p = pyaudio.PyAudio()
            defaults = p.get_default_host_api_info()
            p.terminate()
            device_index = defaults['defaultInputDevice']
            if device_index == -1:
                err = 'No default audio device configured. '
                err += 'Change default audio device or supply a specific device index. '
                raise OSError(err)
        # Get samplerate for device
        p = pyaudio.PyAudio()
        device_info = p.get_device_info_by_index(device_index)
        samplerate = int(device_info['defaultSampleRate'])

        chunk_length = int(samplerate // chunk_rate)
        return self._open_input_stream(chunk_length, device_index=device_index, channels=channels)


class AudioInput(Effect):

    @staticmethod
    def getEffectDescription():
        return \
            "Audio input captures audio from your device and " \
            "makes each channel available as an output. "

    def __init__(self,
                 num_channels=2,
                 autogain_max=10.0,
                 autogain=False,
                 autogain_time=10.0):
        self.num_channels = num_channels
        self.autogain_max = autogain_max
        self.autogain = autogain
        self.autogain_time = autogain_time
        self.__initstate__()

    def __initstate__(self):
        super(AudioInput, self).__initstate__()
        self._buffer = []
        self._outBuffer = []
        self._autogain_perc = None
        self._cur_gain = 1.0
        print("Virtual audio input created. {} {}".format(GlobalAudio.device_index, GlobalAudio.chunk_rate))
        
    def numOutputChannels(self):
        return self.num_channels

    def numInputChannels(self):
        return 0

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("num_channels", [2, 1, 100, 1]),
                ("autogain", False),
                ("autogain_max", [1.0, 0.0, 50.0, 0.01]),
                ("autogain_time", [30.0, 1.0, 100.0, 0.1]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "num_channels":
                "Number of input channels of the audio device.",
                "autogain":
                "Automatically adjust the gain of the input channels.\nThe input signal will be scaled up to 'autogain_max', gain will be reduced if the audio signal would clip.",
                "autogain_max":
                "Maximum gain makeup.",
                "autogain_time":
                "Control the lag of the gain adjustment. Higher values will result in slower gain makeup."
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['autogain_max'][0] = self.autogain_max
        definition['parameters']['autogain_time'][0] = self.autogain_time
        definition['parameters']['autogain'] = self.autogain
        return definition

    def getSampleRate(self):
        return GlobalAudio.sample_rate

    async def update(self, dt):
        await super(AudioInput, self).update(dt)
        if self._autogain_perc is None and GlobalAudio.chunk_rate is not None:
            # increase cur_gain by percentage
            # we want to get to self.autogain_max in approx. self.autogain_time seconds
            min_value = 1. / self.autogain_max  # the minimum input value we want to bring to 1.0
            N = GlobalAudio.chunk_rate * self.autogain_time  # N = chunks_per_second * autogain_time
            # min_value * (perc)^N = 1.0?
            # perc = root(1.0 / min_value, N) = (1./min_value)**(1/N)
            self._autogain_perc = (1.0 / min_value)**float(1 / N)
        self._buffer = GlobalAudio.buffer
        if len(self._outBuffer) != self.num_channels:
            self._outBuffer = []
            for i in range(0, self.num_channels):
                self._outBuffer.append(AudioBuffer(GlobalAudio.sample_rate))

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if self._buffer is None:
            raise RuntimeError("No audio signal. Audio device might be not present or disabled.")
        if len(self._buffer) <= 0:
            return
        if self.autogain:
            # determine max value -> in range 0,1
            maxVal = np.max(self._buffer)
            if maxVal * self._cur_gain > 1:
                # reset cur_gain to prevent clipping
                self._cur_gain = 1. / maxVal
            elif self._cur_gain < self.autogain_max:
                self._cur_gain = min(self.autogain_max, self._cur_gain * self._autogain_perc)
            # print("cur_gain: {}, gained value: {}".format(self._cur_gain, self._cur_gain * maxVal))
        for i in range(0, self.num_channels):
            # layout for multiple channel is interleaved:
            # 00 01 .. 0n 10 11 .. 1n
            self._outBuffer[i].audio = self._cur_gain * self._buffer[i::self.num_channels]
            self._outputBuffer[i] = self._outBuffer[i]
            # print("{}: {}".format(i, self._outputBuffer[i]))
