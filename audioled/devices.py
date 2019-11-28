from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
from collections import OrderedDict
import time
import numpy as np
from audioled.effect import Effect

_GAMMA_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6,
    7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 11, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19, 20, 20, 21,
    21, 22, 23, 23, 24, 24, 25, 26, 26, 27, 28, 28, 29, 30, 30, 31, 32, 32, 33, 34, 35, 35, 36, 37, 38, 38, 39, 40, 41, 42, 42,
    43, 44, 45, 46, 47, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
    73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 97, 98, 99, 100, 102, 103, 104, 105,
    107, 108, 109, 111, 112, 113, 115, 116, 117, 119, 120, 121, 123, 124, 126, 127, 128, 130, 131, 133, 134, 136, 137, 139,
    140, 142, 143, 145, 146, 148, 149, 151, 152, 154, 155, 157, 158, 160, 162, 163, 165, 166, 168, 170, 171, 173, 175, 176,
    178, 180, 181, 183, 185, 186, 188, 190, 192, 193, 195, 197, 199, 200, 202, 204, 206, 207, 209, 211, 213, 215, 217, 218,
    220, 222, 224, 226, 228, 230, 232, 233, 235, 237, 239, 241, 243, 245, 247, 249, 251, 253, 255
]
_GAMMA_TABLE = np.array(_GAMMA_TABLE)


class LEDController:
    """Base class for interfacing with hardware LED strip controllers

    To add support for another hardware device, simply inherit this class
    and implement the show() method.

    Example usage:
        import numpy as np
        N_pixels = 60
        pixels = np.random.random(size=(3, N_pixels))
        device = LEDController()
        device.show(pixels)
    """
    def __init__(self, num_pixels, num_rows=1, brightness=1.0):
        self.num_pixels = num_pixels
        self.num_rows = num_rows
        self.brightness = brightness

    def setBrightness(self, value):
        self.brightness = value

    def getBrightness(self):
        try:
            return min(1.0, self.brightness)
        except AttributeError:
            self.brightness = 1.0
            return min(1.0, self.brightness)

    def getNumPixels(self):
        return self.num_pixels

    def setNumPixels(self, num_pixels):
        self.num_pixels = num_pixels

    def getNumRows(self):
        return self.num_rows

    def setNumRows(self, num_rows):
        self.num_rows = num_rows

    def show(self, pixels):
        """Set LED pixels to the values given in the array

        This function accepts an array of RGB pixel values (pixels)
        and displays them on the LEDs. To add support for another
        hardware device, you should create a class that inherits from
        this class, and then implement this method.

        Parameters
        ----------
        pixels: numpy.ndarray
            2D array containing RGB pixel values for each of the LEDs.
            The shape of the array is (3, n_pixels), where n_pixels is the
            number of LEDs that the device has.

            The array is formatted as shown below. There are three rows
            (axis 0) which represent the red, green, and blue color channels.
            Each column (axis 1) contains the red, green, and blue color values
            for a single pixel:

                np.array([ [r0, ..., rN], [g0, ..., gN], [g0, ..., gN]])

            Each value brightness value is an integer between 0 and 255.

        Returns
        -------
        None
        """
        raise NotImplementedError('Show() was not implemented')

    def test(self, n_pixels):
        pixels = np.zeros((3, n_pixels))
        pixels[0][0] = 255
        pixels[1][1] = 255
        pixels[2][2] = 255
        print('Starting LED strip test.')
        print('Press CTRL+C to stop the test at any time.')
        print('You should see a scrolling red, green, and blue pixel.')
        while True:
            self.show(pixels)
            pixels = np.roll(pixels, 1, axis=1)
            time.sleep(0.2)


class ESP8266(LEDController):
    def __init__(self, num_pixels, num_rows=1, ip='192.168.0.150', port=7777):
        super().__init__(num_pixels, num_rows)
        """Initialize object for communicating with as ESP8266

        Parameters
        ----------
        ip: str, optional
            The IP address of the ESP8266 on the network. This must exactly
            match the IP address of your ESP8266 device.
        port: int, optional
            The port number to use when sending data to the ESP8266. This
            must exactly match the port number in the ESP8266's firmware.
        """
        import socket
        self._ip = ip
        self._port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def show(self, pixels):
        """Sends UDP packets to ESP8266 to update LED strip values

        The ESP8266 will receive and decode the packets to determine what values
        to display on the LED strip. The communication protocol supports LED strips
        with a maximum of 256 LEDs.

        The packet encoding scheme is:
            |i|r|g|b|
        where
            i (0 to 255): Index of LED to change (zero-based)
            r (0 to 255): Red value of LED
            g (0 to 255): Green value of LED
            b (0 to 255): Blue value of LED
        """
        message = (pixels * self.getBrightness()).T.clip(0, 255).astype(np.uint8).ravel().tostring()
        self._sock.sendto(message, (self._ip, self._port))


class FadeCandy(LEDController):
    def __init__(self, num_pixels, num_rows=1, server='localhost:7890'):
        super().__init__(num_pixels, num_rows)
        """Initializes object for communicating with a FadeCandy device

        Parameters
        ----------
        server: str, optional
            FadeCandy server used to communicate with the FadeCandy device.
        """
        import audioled.opc
        self.client = audioled.opc.Client(server)
        if self.client.can_connect():
            print('Successfully connected to FadeCandy server.')
        else:
            print('Could not connect to FadeCandy server.')
            print('Ensure that fcserver is running and try again.')

    def show(self, pixels):
        self.client.put_pixels((pixels * self.getBrightness()).T.clip(0, 255).astype(int).tolist())


class BlinkStick(LEDController):
    def __init__(self, num_pixels, num_rows=1):
        super().__init__(num_pixels, num_rows)
        """Initializes a BlinkStick controller"""
        try:
            from blinkstick import blinkstick
        except ImportError as e:
            print('Unable to import the blinkstick library')
            print('You can install this library with `pip install blinkstick`')
            raise e
        self.stick = blinkstick.find_first()

    def show(self, pixels):
        """Writes new LED values to the Blinkstick.

        This function updates the LED strip with new values.
        """
        # Truncate values and cast to integer
        n_pixels = pixels.shape[1]
        pixels = (pixels * self.getBrightness()).clip(0, 255).astype(int)
        pixels = _GAMMA_TABLE[pixels]
        # Read the rgb values
        r = pixels[0][:].astype(int)
        g = pixels[1][:].astype(int)
        b = pixels[2][:].astype(int)

        # Create array in which we will store the led states
        newstrip = [None] * (n_pixels * 3)

        for i in range(n_pixels):
            # Blinkstick uses GRB format
            newstrip[i * 3] = g[i]
            newstrip[i * 3 + 1] = r[i]
            newstrip[i * 3 + 2] = b[i]
        # Send the data to the blinkstick
        self.stick.set_led_data(0, newstrip)


class RaspberryPi(LEDController):
    def __init__(self, num_pixels, num_rows=1, pin=18, invert_logic=False, freq=800000, dma=10):
        super().__init__(num_pixels, num_rows)
        """Creates a Raspberry Pi output device

        Parameters
        ----------
        pixels: int
            Number of LED strip pixels
        pin: int, optional
            GPIO pin used to drive the LED strip (must be a PWM pin).
            Pin 18 can be used on the Raspberry Pi 2.
        invert_logic: bool, optional
            Whether or not to invert the driving logic.
            Set this to True if you are using an inverting logic level
            converter, otherwise set to False.
        freq: int, optional
            LED strip protocol frequency (Hz). For ws2812 this is 800000.
        dma: int, optional
            DMA (direct memory access) channel used to drive PWM signals.
            If you aren't sure, try 5.
        """
        print('construct')
        self.pin = pin
        self.freq_hz = freq
        self.dma = dma
        self.invert = invert_logic
        self.brightness = 255
        self.__initstate__()

    def __initstate__(self):
        try:
            import rpi_ws281x
            print('init')
            self._strip = rpi_ws281x.PixelStrip(num=self.num_pixels,
                                                pin=self.pin,
                                                freq_hz=self.freq_hz,
                                                dma=self.dma,
                                                invert=self.invert,
                                                brightness=self.brightness)
            self._strip.begin()
        except ImportError:
            url = 'learn.adafruit.com/neopixels-on-raspberry-pi/software'
            print('Could not import the neopixel library')
            print('For installation instructions, see {}'.format(url))
            print('If running on RaspberryPi, please install.')
            print('------------------------------------------')
            print('Otherwise rely on dependency injection')
            print('Disconnecting Device.')

    def __cleanState__(self, stateDict):
        """
        Cleans given state dictionary from state objects beginning with __
        """
        for k in list(stateDict.keys()):
            if k.startswith('_'):
                stateDict.pop(k)
        return stateDict

    def __getstate__(self):
        """
        Default implementation of __getstate__ that deletes buffer, call __cleanState__ when overloading
        """
        state = self.__dict__.copy()
        self.__cleanState__(state)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__initstate__()

    def show(self, pixels):
        """Writes new LED values to the Raspberry Pi's LED strip

        Raspberry Pi uses the rpi_ws281x to control the LED strip directly.
        This function updates the LED strip with new values.
        """

        # Truncate values and cast to integer
        n_pixels = pixels.shape[1]
        pixels = (pixels * self.getBrightness()).clip(0, 255).astype(int)
        # Optional gamma correction
        pixels = _GAMMA_TABLE[pixels]
        # Encode 24-bit LED values in 32 bit integers
        r = np.left_shift(pixels[0][:].astype(int), 16)
        g = np.left_shift(pixels[1][:].astype(int), 8)
        b = pixels[2][:].astype(int)
        rgb = np.bitwise_or(np.bitwise_or(g, r), b)
        # Update the pixels

        for i in range(n_pixels):
            self._strip.setPixelColor(i, int(rgb[i]))
        self._strip.show()


class DotStar(LEDController):
    def __init__(self, num_pixels, num_rows=1, brightness=31):
        super().__init__(num_pixels, num_rows)
        """Creates an APA102-based output device

        Parameters
        ----------
        pixels: int
            Number of LED strip pixels
        brightness: int, optional
            Global brightness
        """
        try:
            import apa102
        except ImportError as e:
            url = 'https://github.com/tinue/APA102_Pi'
            print('Could not import the apa102 library')
            print('For installation instructions, see {}'.format(url))
            raise e
        self._strip = apa102.APA102(numLEDs=num_pixels, globalBrightness=brightness)  # Initialize the strip
        led_data = np.array(self._strip.leds, dtype=np.uint8)
        # memoryview preserving the first 8 bits of LED frames (w/ global brightness)
        self._strip.leds = led_data.data
        # 2D view of led_data
        self.led_data = led_data.reshape((num_pixels, 4))  # or (-1, 4)

    def show(self, pixels):
        bgr = [2, 1, 0]
        self.led_data[0:, 1:4] = (pixels * self.getBrightness())[bgr].T.clip(0, 255)
        self._strip.show()


class LEDOutput(Effect):
    @staticmethod
    def getEffectDescription():
        return \
            "Sends pixel information to a LED Output Device.."

    def __init__(self, brightness=1.0):
        self.brightness = brightness
        self.__initstate__()

    def __initstate__(self):
        super().__initstate__()

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("brightness", [1.0, 0.0, 1.0, 0.01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {"parameters": {"brightness": "Adjust brightness of all pixels."}}
        return help

    def numInputChannels(self):
        return 1

    def numOutputChannels(self):
        # Don't want anything to show in the UI
        return 0

    def process(self):
        if self._inputBuffer is not None and self._outputBuffer is not None:
            # Make output buffer same size as input buffer
            if len(self._outputBuffer) <= self.numInputChannels():
                for i in range(self.numInputChannels() - len(self._outputBuffer)):
                    self._outputBuffer.append(None)
            if self._inputBuffer[0] is not None:
                self._outputBuffer[0] = self.brightness * self._inputBuffer[0]
            else:
                self._outputBuffer[0] = None


class PanelWrapper(LEDController):
    """Device Wrapper for LED Panels

    This class can be used as a wrapper for arbitrary devices and maps
    2d pixel information to the correct pixels on a LED panel.
    A LED panel is assumed to be a combination of short LED strips forming
    rows and columns.

    The format for the mapping JSON:
    {
        "num_rows" : 11, // Number of rows of the panel
        "num_cols" : 44, // Number of columns of the panel
        "substrips": [
            {
                "start_index": 0, // Starting index of the substrip
                "row": 0, // Starting row of the substrip
                "col": 43, // Starting column of the substrip
                "dir": "L", // Direction of the substrip (L, R, U, D)
                "num_pixels": 44 // Number of pixels of the substrip
            },
            {
                "start_index": 44,
                "row": 1,
                "col": 0,
                "dir": "R",
                "num_pixels": 44
            },
            ...
        ]
    }
    """
    def __init__(self, device, mappingJson):
        self.device = device
        self.num_pixels = device.num_pixels
        self.num_rows = device.num_rows
        self.pixel_mapping = None
        if mappingJson is not None:
            self.pixel_mapping = self._createPixelMapping(mappingJson)

    def getBrightness(self):
        return self.device.getBrightness()

    def setBrightness(self, value):
        self.device.setBrightness(value)

    def getNumPixels(self):
        return self.device.getNumPixels()

    def setNumPixels(self, num_pixels):
        self.device.setNumPixels(num_pixels)

    def getNumRows(self):
        return self.device.getNumRows()

    def setNumRows(self, num_rows):
        self.device.setNumRows(num_rows)

    def show(self, pixels):
        mapped_pixels = pixels
        if self.pixel_mapping is not None:
            mapped_pixels = pixels[self.pixel_mapping[:, :, 0], self.pixel_mapping[:, :, 1]]
        self.device.show(mapped_pixels)

    def _createPixelMapping(self, mappingJson):
        def toIdx(row, col, num_cols):
            return row * num_cols + col

        num_rows = mappingJson['num_rows']
        num_cols = mappingJson['num_cols']
        mapping = np.zeros((3, num_rows * num_cols, 2), dtype=np.int64)

        for substrip in mappingJson['substrips']:
            start_index = substrip['start_index']
            row = substrip['row']
            col = substrip['col']
            dir = substrip['dir']
            num_pixels = substrip['num_pixels']
            cur_row = row
            cur_col = col
            for i in range(num_pixels):
                index = start_index + i
                mapping[0, index, :] = [0, toIdx(cur_row, cur_col, num_cols)]
                mapping[1, index, :] = [1, toIdx(cur_row, cur_col, num_cols)]
                mapping[2, index, :] = [2, toIdx(cur_row, cur_col, num_cols)]
                if dir == 'L':
                    cur_col = cur_col - 1
                elif dir == 'R':
                    cur_col = cur_col + 1
                elif dir == 'U':
                    cur_row = cur_row - 1
                else:
                    cur_row = cur_row + 1
        return mapping


# # Execute this file to run a LED strand test
# # If everything is working, you should see a red, green, and blue pixel scroll
# # across the LED strip continously
# if __name__ == '__main__':
#     import time
#     # Turn all pixels off
#     pixels = np.zeros((3, config.N_PIXELS))
#     update(pixels)
#     pixels[0, 0] = 255  # Set 1st pixel red
#     pixels[1, 1] = 255  # Set 2nd pixel green
#     pixels[2, 2] = 255  # Set 3rd pixel blue
#     print('Starting LED strand test')
#     while True:
#         pixels = np.roll(pixels, 1, axis=1)
#         update(pixels)
#         time.sleep(1)
