from __future__ import (absolute_import, division, print_function, unicode_literals)

import itertools
import math

import numpy as np
from scipy.signal import butter, lfilter_zi, lfilter


def rollwin(signal, n_overlaps):
    """
    Generates a rolling window of samples
    """
    frame = next(signal)
    N = len(frame)
    window = np.zeros(N * max(n_overlaps, 1))
    window[-N:] = frame  # last N points
    for data in signal:
        S = len(data)
        window[:-S] = window[S:]
        window[-S:] = data[:S]
        yield window


def normalize_scale(signal, past_n):
    buff = np.ones(past_n)
    for data in signal:
        buff[1:] = buff[:-1]
        buff[0] = data
        maxval = np.max(buff)
        minval = np.min(buff)
        if maxval != minval:
            yield (data - minval) / (maxval - minval)
        else:
            yield data * 0


def fir(taps, signal):
    """Generator that applies FIR filter taps to the iterable signal"""
    init = np.array(list(itertools.islice(signal, len(taps) - 1)))
    buff = np.tile(np.expand_dims(init[0], axis=-1), len(taps)).T
    # Consume the first N = (len(taps) - 1) values for initialization
    for chunk in init:
        buff = np.roll(buff, 1, axis=0)
        buff[0] = chunk
    # Yield the dot product of the buffer and taps (filtered result)
    for chunk in itertools.islice(signal, len(taps) - 1, None):
        buff = np.roll(buff, 1, axis=0)
        buff[0] = chunk
        yield buff.T.dot(taps)


def normalize_rms(signal, past_n):
    buff = np.zeros(past_n)
    for chunk in signal:
        buff[1:] = buff[:-1]
        buff[0] = np.sqrt(np.mean(np.square(chunk)))
        yield chunk / np.max(buff)


def downsample(signal, fs, fmax):
    """Downsamples signal by integer factor if fs > 2 * fmax

    Downsamples the signal output if downsampling is possible.
    Downsampling is possible when fs > 2*fmax, where 2*fmax is the Nyquist
    frequency for highest frequency of interest.

    Parameters
    ----------
    signal : generator
        Generator that yields a 1D np.array containing data samples
    fs : int
        Sampling rate of the unmodified signal
    fmax : int
        The highest frequency of interest.
        Frequencies higher than fmax may be removed during downsampling

    Returns
    -------
    ds_signal : generator
        Generator that yields chunks (np.array) containing data samples.
        Data samples are downsampled if downsampling is possible, otherwise
        the original signal generator is returned
    ds_fs : int
        The downsampled sampling rate. If downsampling is not possible
        then the original sampling rate is returned.
    """
    if fs < 2 * fmax:
        raise ValueError('Sampling frequency fs must be at least 2 * fmax')
    n = int(fs / (2 * fmax))
    if n == 1:
        # Downsampling is not possible
        return signal, fs
    else:
        # Downsample the signal generator
        ds_signal = (chunk[::n] for chunk in signal)
        ds_fs = int(fs // n)
        return ds_signal, ds_fs


def pad_zeros(signal):
    """Pad chunks with zeros until chunk length is a power of two

    Chunks of data yielded by the signal generator are padded with zeros
    until the length of the chunks are equal to the next largest power of
    two. No zeros are padded if the chunks are already a power of two.

    Every chunk yielded by the signal is assumed to have the same length.

    Parameters
    ----------
    signal : generator
        Generator that yields chunks of type np.array containing data that
        should be padded with zeros

    Returns
    -------
    signal : generator
        Generator that yields chunks of type np.array containing data
        that has been padded with zeros. The chunk length is equal to
        the next largest power of two greater than the original length.
        If the original chunk length was a power of two, then the signal
        generator is returned unchanged.
    """
    peek = next(signal)
    signal = itertools.chain([peek], signal)
    N = len(peek)
    N_zeros = int(2**np.ceil(np.log2(N))) - N
    zeros = np.zeros(N_zeros)
    return (np.r_[chunk, zeros] for chunk in signal)


def preemphasis(signal, coeff=0.97):
    """Applies a pre-emphasis filter to the given input signal"""
    return np.append(signal[0], signal[1:] - coeff * signal[:-1])


def memoize(function):
    """Provides a decorator for memoizing functions"""
    from functools import wraps
    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv

    return wrapper


@memoize
def filter_bank(n_filters, n_fft, fs, fmin_hz, fmax_hz, scale):
    """Returns an overlapping triangular filterbank"""
    if scale == 'mel':
        fmin_mel = 2595. * np.log10(1 + fmin_hz / 700.)
        fmax_mel = 2595. * np.log10(1 + fmax_hz / 700.)
        f_mel = np.linspace(fmin_mel, fmax_mel, n_filters + 2)
        f_hz = 700. * (np.exp(f_mel / 1127.) - 1.)
    elif scale == 'bark':
        fmin_bark = 6.0 * np.arcsinh(fmin_hz / 600.0)
        fmax_bark = 6.0 * np.arcsinh(fmax_hz / 600.0)
        f_bark = np.linspace(fmin_bark, fmax_bark, n_filters + 2)
        f_hz = 600.0 * np.sinh(f_bark / 6.0)
    # Convert from Hz points to FFT bin number
    bins = np.floor((n_fft + 1.) * f_hz / fs)
    # Construct the filter bank
    filters = np.zeros((n_filters, n_fft // 2 + 1))
    for m in range(1, n_filters + 1):
        f_m_minus = int(bins[m - 1])  # left
        f_m = int(bins[m])  # center
        f_m_plus = int(bins[m + 1])  # right
        for k in range(f_m_minus, f_m):
            filters[m - 1, k] = (k - bins[m - 1]) / (bins[m] - bins[m - 1])
        for k in range(f_m, f_m_plus):
            filters[m - 1, k] = (bins[m + 1] - k) / (bins[m + 1] - bins[m])
    return filters, f_hz[1:-1]


def warped_psd(y, bins, fs, frange, scale):
    """Returns the power spectrum mapped to a perceptual scale"""
    N = len(y)
    # Transform to frequency domain
    pow_spectrum = np.abs(np.fft.rfft(y))**2 * (2 / N)
    # Construct triangular filter bank
    output, f = filter_bank(bins, N, fs, frange[0], frange[1], scale)
    # Apply filter bank to power spectrum
    # Remark: Numpy matrix multiplication uses all available CPU cores for a rather small matrix multiplication
    # output_np = np.dot(pow_spectrum, output.T)

    # Own MM:
    pow_spectrum = pow_spectrum.reshape(1, -1)
    output = np.sum(pow_spectrum[:, :, None]*output.T[None, :, :], axis=1)
    output = output.reshape(-1)
    # print(np.allclose(output, output_np))
    return output


def preprocess(audio, fs, fmax, n_overlaps):
    # Downsample if we don't need high frequencies
    audio, fs = downsample(audio, fs=fs, fmax=fmax)
    # Create rolling window of last audio chunks
    audio = rollwin(audio, n_overlaps)
    # Construct hanning window to smooth audio at the edges
    hanning_window = np.hanning(len(next(audio)))
    # Apply hanning window
    audio = (x * hanning_window for x in audio)
    # Don't know what this should do but breaks processing if no audio input present...
    # audio = (x for x in audio if np.sqrt(np.mean(np.square(x))) > 1e-5)
    audio = pad_zeros(audio)
    return audio, fs


def rms(normalized_sample_points):
    N = len(normalized_sample_points)
    sum_squares = sum(s**2 for s in normalized_sample_points)
    # TODO: Why N/2???
    return math.sqrt(sum_squares / (N / 2))


def design_filter(lowcut, highcut, fs, order=3):
    nyq = 0.5 * fs
    lowcut = max(lowcut, 10)
    highcut = min(highcut, 22000)
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a, lfilter_zi(b, a)


class Bandpass():
    def __init__(self, lowcut=0.0, highcut=20000, fs=44100, order=3):
        self._fs = fs
        self._filter_a = None
        self._filter_b = None
        self._filter_zi = None
        self._lowcut = lowcut
        self._highcut = highcut
        self._order = order
        self._initFilter()

    def filter(self, audio, fs):
        if fs != self._fs:
            self._initFilter()
        y, self._filter_zi = lfilter(b=self._filter_b, a=self._filter_a, x=audio, zi=self._filter_zi)
        return y

    def updateParams(self, lowcut, highcut, fs, order):
        if self._lowcut != lowcut or self._highcut != highcut or self._fs != fs or self._order != order:
            self._lowcut = lowcut
            self._highcut = highcut
            self._fs = fs
            self._order = order
            self._initFilter()

    def _initFilter(self):
        if self._lowcut is None:
            self._lowcut = 0.0
        if self._highcut is None:
            self._highcut = 20000.0
        if self._fs is None:
            self._fs = 44100
        if self._order is None:
            self._order = 3
        self._filter_b, self._filter_a, self._filter_zi = design_filter(self._lowcut, self._highcut, self._fs, self._order)
