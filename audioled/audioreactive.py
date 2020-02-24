from __future__ import (absolute_import, division, print_function, unicode_literals)

import colorsys
import math
import random
from collections import OrderedDict

import numpy as np
import scipy as sp
from scipy.ndimage.filters import gaussian_filter1d

import audioled.colors as colors
import audioled.dsp as dsp
from audioled.effects import Effect
import audioled.effect as effect

# TODO: Adjustable Frequency for Bass and Melody
# TODO: Single Band version
class Spectrum(Effect):
    """
    Spectrum performs a FFT and visualizes bass and melody frequencies with different colors.

    Inputs:
    - 0: Audio
    - 1: Color for melody (default: white)
    - 2: Color for bass (default: white)

    Outputs:
    - 0: Pixel array

    """
    @staticmethod
    def getEffectDescription():
        return \
            "Spectrum performs a FFT on the audio input (channel 0) and visualizes bass and melody frequencies "\
            "with different colors (channel 1 for bass, channel 2 for melody)."

    def __init__(self, fmax=6000, n_overlaps=4, fft_bins=64, col_blend=colors.blend_mode_default):
        self.fmax = fmax
        self.n_overlaps = n_overlaps
        self.fft_bins = fft_bins
        self.col_blend = col_blend
        self.__initstate__()

    def __initstate__(self):
        # state
        self._norm_dist = None
        self.fft_bins = 64
        self._fft_dist = np.linspace(0, 1, self.fft_bins)
        self._max_filter = np.ones(8)
        self._min_feature_win = np.hamming(8)
        self._fs_ds = 0.0
        self._bass_rms = None
        self._melody_rms = None
        self._lastAudioChunk = None
        self._gen = None
        super(Spectrum, self).__initstate__()

    def numInputChannels(self):
        return 3

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("n_overlaps", [4, 0, 20, 1]),
                ("fft_bins", [64, 32, 128, 1]),
                ("col_blend", colors.blend_modes)
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "n_overlaps": "Number of overlapping samples in time. This smoothes the FFT.",
                "fft_bins": "Number of bins of the FFT. Increase for a more detailed FFT.",
                "col_blend": "Color blend mode for combining bass and melody FFT."
            }
        }
        return help

    def getParameter(self):
        definition = super().getParameter()
        definition['parameters']['col_blend'] = [self.col_blend] + [x for x in colors.blend_modes if x != self.col_blend]
        return definition

    def getModulateableParameters(self):
        return []  # Disable all modulations

    def _audio_gen(self, audio_gen):
        audio, self._fs_ds = dsp.preprocess(audio_gen, self._fs, self.fmax, self.n_overlaps)
        return audio

    def buffer_coroutine(self):
        while True:
            yield self._lastAudioChunk

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._norm_dist is None or len(self._norm_dist) != self._num_pixels:
            self._norm_dist = np.linspace(0, 1, self._num_pixels)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        audio = self._inputBuffer[0].audio
        self._fs = self._inputBuffer[0].sample_rate
        col_melody = self._inputBuffer[1]
        col_bass = self._inputBuffer[2]
        if col_melody is None:
            # default color: all white
            col_melody = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if col_bass is None:
            # default color: all white
            col_bass = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        if audio is not None:
            if self._gen is None:
                g = self.buffer_coroutine()
                next(g)
                self._lastAudioChunk = audio
                self._gen = self._audio_gen(g)
            self._lastAudioChunk = audio
            y = next(self._gen)
            bass = dsp.warped_psd(y, self.fft_bins, self._fs_ds, [32.7, 261.0], 'bark')
            melody = dsp.warped_psd(y, self.fft_bins, self._fs_ds, [261.0, self.fmax], 'bark')
            bass = self.process_line(bass)
            melody = self.process_line(melody)
            pixels = colors.blend(
                1. / 255.0 * np.multiply(col_bass, bass),
                1. / 255. * np.multiply(col_melody, melody),
                self.col_blend,
            )
            self._outputBuffer[0] = pixels.clip(0, 255).astype(int)

    def process_line(self, fft):

        # fft = np.convolve(fft, self._max_filter, 'same')

        # Some kind of normalization?
        # fft_rms[1:] = fft_rms[:-1]
        # fft_rms[0] = np.mean(fft)
        # fft = np.tanh(fft / np.max(fft_rms)) * 255

        # Upsample to number of pixels
        fft = np.interp(self._norm_dist, self._fft_dist, fft)

        #
        fft = np.convolve(fft, self._min_feature_win, 'same')

        return fft * 255


class VUMeterRMS(Effect):
    """ VU Meter style effect
    Inputs:
    - 0: Audio
    - 1: Color
    """
    @staticmethod
    def getEffectDescription():
        return \
            "VUMeterRMS visualizes the RMS value of the audio input (channel 0) with the color (channel 1)."

    def __init__(self,
                 db_range=60.0,
                 n_overlaps=1,
                 lowcut_hz=0.0,
                 highcut_hz=20000.0):
        self.db_range = db_range
        self.n_overlaps = n_overlaps
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._hold_values = []
        self._bandpass = None
        self._default_color = None

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("db_range", [60.0, 20.0, 100.0, 1.0]),
                ("n_overlaps", [1, 0, 20, 1]),
                ("lowcut_hz", [0.0, 0.0, 8000.0, 1.0]),
                ("highcut_hz", [20000.0, 0.0, 20000.0, 1.0]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "db_range": "Range of the VU Meter in decibels.",
                "n_overlaps": "Number of overlapping samples in time. This smoothes the VU Meter.",
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input."
            }
        }
        return help

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._default_color is None or np.size(self._default_color, 1) != self._num_pixels:
            # default color: VU Meter style
            # green from -inf to -24
            # green to red from -24 to 0
            h_a, s_a, v_a = colorsys.rgb_to_hsv(0, 1, 0)
            h_b, s_b, v_b = colorsys.rgb_to_hsv(1, 0, 0)
            scal_value = max((self.db_range + (-24)) / self.db_range, 0)  # clip to positive if db_range < 24
            index = int(self._num_pixels * scal_value)
            num_pix = self._num_pixels - index
            interp_v = np.linspace(v_a, v_b, num_pix)
            interp_s = np.linspace(s_a, s_b, num_pix)
            interp_h = np.linspace(h_a, h_b, num_pix)
            hsv = np.array([interp_h, interp_s, interp_v]) * 255
            rgb = colors.hsv_to_rgb(hsv).T
            if (index > 0):
                green = np.array([[0, 255.0, 0] for i in range(index)]).T
                self._default_color = np.concatenate((green, rgb.T), axis=1)
            else:
                self._default_color = rgb.T

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        color = self._inputBuffer[1]
        if color is None:
            color = self._default_color

        y = self._inputBuffer[0].audio
        fs = self._inputBuffer[0].sample_rate

        if self.lowcut_hz > 0 and self.highcut_hz < 20000:
            # construct filter if needed
            if self._bandpass is None:
                self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
            # process audio
            y = self._bandpass.filter(np.array(y), fs)

        rms = dsp.rms(y)
        # calculate rms over hold_time
        while len(self._hold_values) > self.n_overlaps:
            self._hold_values.pop()
        self._hold_values.insert(0, rms)
        rms = dsp.rms(self._hold_values)
        db = 20 * math.log10(max(rms, 1e-16))
        scal_value = (self.db_range + db) / self.db_range
        bar = np.zeros(self._num_pixels) * np.array([[0], [0], [0]])
        index = int(self._num_pixels * scal_value)
        index = np.clip(index, 0, self._num_pixels - 1)
        bar[0:3, 0:index] = color[0:3, 0:index]
        self._outputBuffer[0] = bar

# TODO: Add Bandpass filter
class VUMeterPeak(Effect):
    """ VU Meter style effect
    Inputs:
    - 0: Audio
    - 1: Color
    """
    @staticmethod
    def getEffectDescription():
        return \
            "VUMeterPeak visualizes the Peak value of the audio input (channel 0) with the color (channel 1)."

    def __init__(self, db_range=60.0, n_overlaps=1):
        self.db_range = db_range
        self.n_overlaps = n_overlaps
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._hold_values = []
        self._default_color = None

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("db_range", [60.0, 20.0, 100.0, 1.0]),
                ("n_overlaps", [1, 0, 20, 1])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "db_range": "Range of the VU Meter in decibels.",
                "n_overlaps": "Number of overlapping samples in time. This smoothes the VU Meter."
            }
        }
        return help

    async def update(self, dt):
        await super().update(dt)
        if self._num_pixels is None:
            return
        if self._default_color is None or np.size(self._default_color, 1) != self._num_pixels:
            # default color: VU Meter style
            # green from -inf to -24
            # green to red from -24 to 0
            h_a, s_a, v_a = colorsys.rgb_to_hsv(0, 1, 0)
            h_b, s_b, v_b = colorsys.rgb_to_hsv(1, 0, 0)
            scal_value = max((self.db_range + (-24)) / self.db_range, 0)  # clip to positive if db_range < 24
            index = int(self._num_pixels * scal_value)
            num_pix = self._num_pixels - index
            interp_v = np.linspace(v_a, v_b, num_pix)
            interp_s = np.linspace(s_a, s_b, num_pix)
            interp_h = np.linspace(h_a, h_b, num_pix)
            hsv = np.array([interp_h, interp_s, interp_v]) * 255
            rgb = colors.hsv_to_rgb(hsv).T
            if (index > 0):
                green = np.array([[0, 255.0, 0] for i in range(index)]).T
                self._default_color = np.concatenate((green, rgb.T), axis=1)
            else:
                self._default_color = rgb.T

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        color = self._inputBuffer[1]
        if color is None:
            color = self._default_color

        y = self._inputBuffer[0].audio

        peak = np.max(y)
        # calculate max over hold_time
        while len(self._hold_values) > self.n_overlaps:
            self._hold_values.pop()
        self._hold_values.insert(0, peak)
        peak = np.max(self._hold_values)

        db = (20 * (math.log10(max(peak, 1e-16))))
        scal_value = (self.db_range + db) / self.db_range
        bar = np.zeros(self._num_pixels) * np.array([[0], [0], [0]])
        index = int(self._num_pixels * scal_value)
        index = np.clip(index, 0, self._num_pixels - 1)
        bar[0:3, 0:index] = color[0:3, 0:index]
        self._outputBuffer[0] = bar


class MovingLight(Effect):
    """
    This effect generates a peak at the beginning of the strip that moves and dissipates

    Inputs:
    - 0: Audio
    - 1: Color
    """
    @staticmethod
    def getEffectDescription():
        return \
            "MovingLight generates a visual peak based on the audio input (channel 0) with the given color (channel 1) "\
            "at the beginning of the strip. This peak moves down the strip until it dissipates."

    def __init__(self,
                 speed=100.0,
                 dim_time=2.5,
                 lowcut_hz=50.0,
                 highcut_hz=300.0,
                 peak_scale=4.0,
                 peak_filter=2.6,
                 highlight=0.6,
                 smoothing=0):
        self.speed = speed
        self.dim_time = dim_time
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.peak_scale = peak_scale
        self.peak_filter = peak_filter
        self.highlight = highlight
        self.smoothing = smoothing
        self.__initstate__()

    def __initstate__(self):
        super(MovingLight, self).__initstate__()
        # state
        self._pixel_state = None
        self._bandpass = None
        self._last_t = 0.0
        self._last_move_t = 0.0
        self._hold_values = []

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("speed", [10.0, 1.0, 200.0, 1.0]),
                ("dim_time", [1.0, 0.01, 10.0, 0.01]),
                ("lowcut_hz", [50.0, 0.0, 8000.0, 1.0]),
                ("highcut_hz", [100.0, 0.0, 8000.0, 1.0]),
                ("peak_filter", [1.0, 0.0, 10.0, .01]),
                ("peak_scale", [1.0, 0.0, 5.0, .01]),
                ("highlight", [0.0, 0.0, 1.0, 0.01]),
                ("smoothing", [0, 0, 1, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "speed": "Speed of the moving peak.",
                "dim_time": "Amount of time for the afterglow of the moving peak.",
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input.",
                "peak_filter":
                "Filters the audio peaks. Increase this value to transform only high audio peaks into visual peaks.",
                "peak_scale": "Scales the visual peak after the filter.",
                "highlight": "Amount of white light added to the audio peak.",
                "smoothing": "Smoothing of the moving peak.",
            }
        }
        return help

    async def update(self, dt):
        await super().update(dt)
        if self._pixel_state is None or np.size(self._pixel_state, 1) != self._num_pixels:
            self._pixel_state = np.zeros(self._num_pixels) * np.array([[0.0], [0.0], [0.0]])

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        audio = self._inputBuffer[0].audio
        fs = self._inputBuffer[0].sample_rate
        color = self._inputBuffer[1]
        if color is None:
            # default color: all white
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])
        # construct filter if needed
        if self._bandpass is None:
            self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
        # apply bandpass to audio
        y = self._bandpass.filter(np.array(audio), fs)
        # move in speed
        dt_move = self._t - self._last_move_t
        # calculate number of pixels to shift
        shift_pixels = int(dt_move * self.speed)
        shift_pixels = np.clip(shift_pixels, 1, self._num_pixels - 1)
        if dt_move * self.speed > 1:
            self._pixel_state[:, shift_pixels:] = self._pixel_state[:, :-shift_pixels]
            self._pixel_state[:, 0:shift_pixels] = self._pixel_state[:, shift_pixels:shift_pixels + 1]
            # convolve to smooth edges
            self._pixel_state[:, 0:2 * shift_pixels] = gaussian_filter1d(self._pixel_state[:, 0:2 * shift_pixels],
                                                                         sigma=0.5,
                                                                         axis=1)
            self._last_move_t = self._t
        # dim with time
        dt = self._t - self._last_t
        self._last_t = self._t
        self._pixel_state *= (1.0 - dt / self.dim_time)
        self._pixel_state = gaussian_filter1d(self._pixel_state, sigma=0.5, axis=1)
        self._pixel_state = gaussian_filter1d(self._pixel_state, sigma=0.5, axis=1)
        # calculate current peak
        peak = np.max(y) * 1.0
        while len(self._hold_values) > 20 * self.smoothing:
            self._hold_values.pop()
        self._hold_values.insert(0, peak)
        peak = np.max(self._hold_values)
        # apply peak filter and scale
        try:
            peak = peak**self.peak_filter
        except Exception:
            peak = peak
        peak = peak * self.peak_scale
        # new pixel at origin with peak
        r, g, b = color[0, 0], color[1, 0], color[2, 0]
        self._pixel_state[0][0:shift_pixels] = r * peak + self.highlight * peak * 255.0
        self._pixel_state[1][0:shift_pixels] = g * peak + self.highlight * peak * 255.0
        self._pixel_state[2][0:shift_pixels] = b * peak + self.highlight * peak * 255.0
        self._pixel_state = np.nan_to_num(self._pixel_state).clip(0.0, 255.0)
        self._outputBuffer[0] = self._pixel_state

# TODO: 2d version
class Bonfire(Effect):
    """ Effect for audio-reactive color splitting of an existing pixel array.
    Compare searchlight and bonfireSearchlight WebUIConfigs.
    Inputs:
    - 0: Audio
    - 1: Pixels
    """
    @staticmethod
    def getEffectDescription():
        return \
            "Bonfire performs an audio-reactive color splitting of input channel 1 based on "\
            "the audio input (channel 0)."

    def __init__(self,
                 spread=100,
                 lowcut_hz=50.0,
                 highcut_hz=200.0,
                 peak_scale=1.0,
                 peak_filter=1.0,
                 smoothing=0):
        self.spread = spread
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.peak_scale = peak_scale
        self.peak_filter = peak_filter
        self.smoothing = smoothing
        self._default_color = None
        self.__initstate__()

    def __initstate__(self):
        self._bandpass = None
        self._hold_values = []
        super(Bonfire, self).__initstate__()

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("spread", [10, 0, 100, 1]),
                ("lowcut_hz", [50.0, 0.0, 8000.0, 1.0]),
                ("highcut_hz", [100.0, 0.0, 8000.0, 1.0]),
                ("peak_filter", [1.0, 0.0, 10.0, .01]),
                ("peak_scale", [1.0, 0.0, 5.0, .01]),
                ("smoothing", [0, 0, 1, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "spread": "Amount of pixels the splitted colors are moved.",
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input.",
                "peak_filter":
                "Filters the audio peaks. Increase this value to transform only high audio peaks into visual peaks.",
                "peak_scale": "Scales the visual peak after the filter.",
                "smoothing": "Smoothing of the moving peak.",
            }
        }
        return help

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        if self._inputBufferValid(1):
            pixelbuffer = self._inputBuffer[1]
        else:
            # default color: all white
            pixelbuffer = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])

        audio = self._inputBuffer[0].audio
        fs = self._inputBuffer[0].sample_rate

        # construct filter if needed
        if self._bandpass is None:
            self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
        # apply bandpass to audio
        y = self._bandpass.filter(np.array(audio), fs)
        peak = np.max(y) * 1.0
        while len(self._hold_values) > 20 * self.smoothing:
            self._hold_values.pop()
        self._hold_values.insert(0, peak)
        peak = np.max(self._hold_values)
        # apply peak filter and scale
        try:
            peak = peak**self.peak_filter
        except Exception:
            peak = peak
        peak = peak * self.peak_scale

        pixelbuffer[0] = sp.ndimage.interpolation.shift(pixelbuffer[0], -self.spread * peak, mode='wrap', prefilter=True)
        pixelbuffer[2] = sp.ndimage.interpolation.shift(pixelbuffer[2], self.spread * peak, mode='wrap', prefilter=True)
        self._outputBuffer[0] = pixelbuffer


class FallingStars(Effect):
    """Effect for creating random stars that fade over time."""
    @staticmethod
    def getEffectDescription():
        return \
            "Effect for creating random stars based on audio input that fade over time."

    def __init__(self,
                 lowcut_hz=50.0,
                 highcut_hz=300.0,
                 peak_filter=1.0,
                 peak_scale=1.0,
                 dim_speed=100,
                 thickness=1,
                 probability=0.1,
                 min_brightness=0.1,
                 max_spawns=10):
        self.dim_speed = dim_speed
        self.thickness = thickness
        self.probability = probability
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.peak_filter = peak_filter
        self.peak_scale = peak_scale
        self.min_brightness = min_brightness
        self.max_spawns = max_spawns
        self.__initstate__()

    def __initstate__(self):
        # state
        self._t0Array = []
        self._spawnArray = []
        self._peakArray = []
        self._starCounter = 0
        self._bandpass = None
        super(FallingStars, self).__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("lowcut_hz", [50.0, 0.0, 8000.0, 1.0]),
                ("highcut_hz", [100.0, 0.0, 8000.0, 1.0]),
                ("peak_filter", [1.0, 0.0, 10.0, .01]),
                ("peak_scale", [1.0, 0.0, 10.0, .01]),
                ("dim_speed", [100, 1, 1000, 1]),
                ("thickness", [1, 1, 300, 1]),
                ("probability", [0.1, 0.0, 1.0, 0.01]),
                ("min_brightness", [0.1, 0.0, 1.0, 0.01]),
                ("max_spawns", [10, 1, 10, 1])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input.",
                "peak_filter":
                "Filters the audio peaks. Increase this value to transform only high audio peaks into visual peaks.",
                "peak_scale": "Scales the visual peak after the filter.",
                "dim_speed": "Time to fade out one star.",
                "thickness": "Thickness of one star in pixels.",
                "probability": "Probability of spawning a new star even if there's no audio peak.",
                "max_spawns": "Maximum number of spawning stars per frame.",
                "min_brightness": "Adjust minimum brightness of stars."
            }
        }
        return help

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def spawnStar(self, peak):
        self._starCounter += 1
        self._t0Array.append(self._t)
        self._spawnArray.append(random.randint(0, self._num_pixels - self.thickness))
        self._peakArray.append(peak)
        if self._starCounter > 100:
            self._starCounter -= 1
            self._t0Array.pop(0)
            self._spawnArray.pop(0)
            self._peakArray.pop(0)

    def allStars(self, t, dim_speed, thickness, t0, spawnSpot, peak):
        controlArray = []
        for i in range(0, self._starCounter):
            oneStarArray = np.zeros(self._num_pixels)
            for j in range(0, thickness):
                if i < len(spawnSpot):
                    index = spawnSpot[i] + j
                    if index < self._num_pixels:
                        tmp = math.exp(-(100 / dim_speed) * (self._t - t0[i])) * max(self.min_brightness, peak[i])
                        oneStarArray[index] = tmp
            controlArray.append(oneStarArray)
        return controlArray

    def starControl(self, prob, peak):
        for i in range(int(self.max_spawns)):
            if random.random() <= prob:
                self.spawnStar(peak)
        outputArray = self.allStars(self._t, self.dim_speed, self.thickness, self._t0Array, self._spawnArray, self._peakArray)
        return np.sum(outputArray, axis=0)

    async def update(self, dt):
        await super().update(dt)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            self._outputBuffer[0] = None
            return
        if self._inputBufferValid(1):
            color = self._inputBuffer[1]
        else:
            color = np.ones(self._num_pixels) * np.array([[255.0], [255.0], [255.0]])

        audio = self._inputBuffer[0].audio
        fs = self._inputBuffer[0].sample_rate

        # construct filter if needed
        if self._bandpass is None:
            self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
        # apply bandpass to audio
        y = self._bandpass.filter(np.array(audio), fs)

        # adjust probability according to peak of audio
        peak = np.max(y) * 1.0
        try:
            peak = peak**self.peak_filter
        except Exception:
            peak = peak
        prob = min(self.probability + peak, 1.0)
        if self._outputBuffer is not None:
            self._output = np.multiply(
                color,
                self.starControl(prob, peak)
                * np.array([[self.peak_scale * 1.0], [self.peak_scale * 1.0], [self.peak_scale * 1.0]]))
        self._outputBuffer[0] = self._output.clip(0.0, 255.0)


class Oscilloscope(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Displays audio as a wave signal over time."

    def __init__(self, lowcut_hz=1.0, highcut_hz=22000.0, window_fq_hz=50, gain=1.0, speed_fps=30.0):
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.window_fq_hz = window_fq_hz
        self.gain = gain
        self.speed_fps = speed_fps
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._bandpass = None
        self._audioBuffer = None
        self._last_process_dt = 0.0

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("lowcut_hz", [1.0, 1.0, 8000.0, 1.0]),
                ("highcut_hz", [22000.0, 0.0, 22000.0, 1.0]),
                ("window_fq_hz", [50, 10, 320, 1.0]),
                ("gain", [1.0, 0.5, 1.8, 0.001]),
                ("speed_fps", [30.0, 5.0, 60.0, 5.0])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input.",
                "window_fq_hz": "Window size (frequency) to display",
                "gain": "Gain for audio input (makeup db)",
                "speed_fps": "Framerate of oscilloscope effect"
            }
        }
        return help

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    def getNumInputPixels(self, channel):
        if self._num_pixels is not None:
            cols = int(self._num_pixels / self._num_rows)
            return cols
        return None

    async def update(self, dt):
        await super().update(dt)

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            return

        # Process every now and then (speed_fps)
        dt = self._t - self._last_process_dt
        # Prevent division by zero
        if dt == 0.0:
            return
        cur_fps = 1.0 / dt
        if cur_fps > self.speed_fps:
            # Return to exit
            # print("Met t= {}".format(self._t))
            return

        # print("Process")

        # Init color input
        cols = int(self._num_pixels / self._num_rows)
        if self._inputBufferValid(1):
            color = self._inputBuffer[1]
        else:
            color = np.ones(cols) * np.array([[255], [255], [255]])

        # Init audio
        audio = self._inputBuffer[0].audio * self.gain
        fs = self._inputBuffer[0].sample_rate

        # construct filter if needed
        if self._bandpass is None:
            self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
        # apply bandpass to audio
        y = self._bandpass.filter(np.array(audio), fs)

        # adjust number of samples to respect window_fq_hz.
        # if we have 440 samples @ 44000 Hz -> 440/44000 = 0.01 s of data -> 100 Hz
        # if we have 880 samples @ 44000 Hz -> 880/44000 = 0.02 s of data -> 50 Hz
        # if we want to display 100 Hz in the entire window:
        # 1 / 100 Hz * 44000 -> 440 samples

        adjusted_window = int(1.0 / self.window_fq_hz * fs / 2.0)
        # update audio buffer
        if self._audioBuffer is None:
            self._audioBuffer = y
        elif self._audioBuffer is not None and (len(self._audioBuffer) + len(y)) > adjusted_window * 10:
            # audio buffer contains more samples than we need
            self._audioBuffer = self._audioBuffer[len(y):]
            self._audioBuffer = np.append(self._audioBuffer, y)
        else:
            self._audioBuffer = np.append(self._audioBuffer, y)

        y = self._audioBuffer
        adjusted_window = int(min(len(y), adjusted_window))

        # Find zero crossings to stabilize output
        zero_crossings = np.where(np.diff(np.sign(y)))[0]
        start_idx = 0
        if len(zero_crossings) > 1:
            if y[zero_crossings[0]] < 0 and y[zero_crossings[0] + 1] > 0:
                start_idx = zero_crossings[0]
            else:
                start_idx = zero_crossings[1]

        y = y[start_idx:start_idx + adjusted_window]

        output = np.zeros((3, self._num_rows, cols))
        # First downsample to half the cols
        decimation_ratio = np.round(len(y) / (cols + 1))
        downsampled_audio = sp.signal.decimate(y, int(decimation_ratio), ftype='fir', zero_phase=True)
        # Then resample to the number of cols -> prevents jumping between positive and negative values
        for i in range(0, cols):
            if i >= len(downsampled_audio):
                continue
            # determine index in audio array
            valIdx = i
            # get value
            val = downsampled_audio[valIdx]
            # convert to row idx
            rowIdx = max(0, min(int(self._num_rows / 2 + val * self._num_rows / 2), self._num_rows - 1))
            # set value for this col
            output[:, rowIdx, i] = color[:, i]
        self._outputBuffer[0] = output.reshape((3, -1))
        # Update timer
        self._last_process_dt = self._t


class Blink(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Makes pixels blink with audio"

    def __init__(self, db_range=60.0, smoothing=0, amount=1.0):
        self.db_range = db_range
        self.smoothing = smoothing
        self.amount = amount
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._hold_values = []
        self._default_color = None

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("db_range", [60.0, 20.0, 100.0, 1.0]),
                ("smoothing", [0, 0, 1, 0.01]),
                ("amount", [1, 0, 1, 0.01])
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "db_range": "dB range of Blink to work in.",
                "smoothing": "Smoothing of the blinking.",
                "amount": "Amount of blinking."
            }
        }
        return help

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            return
        y = self._inputBuffer[0].audio
        rms = dsp.rms(y)
        # calculate rms over hold_time
        while len(self._hold_values) > 20 * self.smoothing:
            self._hold_values.pop()
        self._hold_values.insert(0, rms)
        rms = dsp.rms(self._hold_values)
        db = 20 * math.log10(max(rms, 1e-16))
        scal_value = (self.db_range + db) / self.db_range
        self._outputBuffer[0] = self._inputBuffer[1] * (1 - self.amount) + self._inputBuffer[1] * scal_value * self.amount


class Shift(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Makes pixels shift with audio"

    def __init__(
            self,
            db_range=60.0,
            smoothing=0,
            speed=100.0,
            lowcut_hz=1.0,
            highcut_hz=22000.0,
            peak_filter=2.6,
            peak_scale=4.0,
    ):
        self.db_range = db_range
        self.smoothing = smoothing
        self.speed = speed
        self.lowcut_hz = lowcut_hz
        self.highcut_hz = highcut_hz
        self.peak_filter = peak_filter
        self.peak_scale = peak_scale
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()
        self._bandpass = None
        self._hold_values = []
        self._shift_pixels = 0
        self._last_t = self._t

    def numInputChannels(self):
        return 2

    def numOutputChannels(self):
        return 1

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("db_range", [60.0, 20.0, 100.0, 1.0]),
                ("smoothing", [0, 0, 1, 0.01]),
                ("speed", [100.0, -1000.0, 1000.0, 1.0]),
                ("lowcut_hz", [1.0, 1.0, 8000.0, 1.0]),
                ("highcut_hz", [22000.0, 0.0, 22000.0, 1.0]),
                ("peak_filter", [1.0, 0.0, 10.0, .01]),
                ("peak_scale", [1.0, 0.0, 5.0, .01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "db_range": "dB range of Shift to work in.",
                "smoothing": "Smoothing of the shift.",
                "speed": "Speed of the shifting effect.",
                "lowcut_hz": "Lowcut frequency of the audio input.",
                "highcut_hz": "Highcut frequency of the audio input.",
                "peak_filter":
                "Filters the audio peaks. Increase this value to transform only high audio peaks into visual peaks.",
                "peak_scale": "Scales the visual peak after the filter.",
            }
        }
        return help

    def process(self):
        if self._inputBuffer is None or self._outputBuffer is None:
            return
        if not self._inputBufferValid(0, buffer_type=effect.AudioBuffer.__name__):
            return
        if not self._inputBufferValid(1):
            self._outputBuffer[0] = None
            return

        # Init audio
        audio = self._inputBuffer[0].audio
        fs = self._inputBuffer[0].sample_rate

        # construct filter if needed
        if self._bandpass is None:
            self._bandpass = dsp.Bandpass(self.lowcut_hz, self.highcut_hz, fs, 3)
        # apply bandpass to audio
        y = self._bandpass.filter(np.array(audio), fs)

        x = self._inputBuffer[1]
        rms = dsp.rms(y)
        # calculate rms over hold_time
        while len(self._hold_values) > 20 * self.smoothing:
            self._hold_values.pop()
        self._hold_values.insert(0, rms)
        rms = dsp.rms(self._hold_values)
        db = 20 * math.log10(max(rms, 1e-16))
        db = max(db, -self.db_range)

        scal_value = (self.db_range + db) / self.db_range
        try:
            scal_value = scal_value**self.peak_filter
        except Exception:
            scal_value = scal_value
        scal_value = scal_value * self.peak_scale

        dt_move = self._t - self._last_t
        shift = dt_move * self.speed * 0.1 * scal_value
        self._shift_pixels = math.fmod((self._shift_pixels + shift), np.size(x, axis=1))
        self._last_t = self._t
        self._outputBuffer[0] = sp.ndimage.interpolation.shift(x, [0, self._shift_pixels], mode='wrap', prefilter=True)
