import inspect


class PixelBuffer(object):
    def __init__(self):
        super().__init__()


class AudioBuffer(object):
    def __init__(self, sample_rate):
        super().__init__()
        self.audio = None
        self.sample_rate = sample_rate


class Effect(object):
    """
    Base class for effects

    Effects have a number of input channels and a number of output channels.
    Before each processing the effect is updated.

    Input values can be accessed by self._inputBuffer[channelNumber], output values
    are to be written into self_outputBuffer[channelNumber].
    """

    def __init__(self):
        self.__initstate__()

    def __initstate__(self):
        try:
            self._filterGraph
        except AttributeError:
            self._filterGraph = None
        try:
            self._t
        except AttributeError:
            self._t = 0
        try:
            self._last_t
        except AttributeError:
            self._last_t = 0
        try:
            self._num_pixels
        except AttributeError:
            self._num_pixels = None
        try:
            self._num_rows
        except AttributeError:
            self._num_rows = 1
        try:
            self._inputBuffer
        except AttributeError:
            self._inputBuffer = None
        try:
            self._outputBuffer
        except AttributeError:
            self._outputBuffer = None
        # make sure all default values are set (basic backwards compatibility)
        argspec = inspect.getargspec(self.__init__)
        if argspec.defaults is not None:
            argsWithDefaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
            for key in argsWithDefaults:
                if key not in self.__dict__:
                    print("Backwards compatibility: Adding default value {}={}".format(key, argsWithDefaults[key]))
                    self.__dict__[key] = argsWithDefaults[key]

    def numOutputChannels(self):
        """
        Returns the number of output channels for this effect
        """
        raise NotImplementedError('numOutputChannels() was not implemented')

    def numInputChannels(self):
        """
        Returns the number of input channels for this effect.
        """
        raise NotImplementedError('numInputChannels() was not implemented')

    def setOutputBuffer(self, buffer):
        """
        Set output buffer where processed data is to be written
        """
        self._outputBuffer = buffer

    def setInputBuffer(self, buffer):
        """
        Set input buffer for incoming data
        """
        self._inputBuffer = buffer

    def process(self):
        """
        The main processing function:
        - Read input data from self._inputBuffer
        - Process data
        - Write output data to self._outputBuffer
        """
        raise NotImplementedError('process() was not implemented')

    async def update(self, dt):
        """
        Update timing, can be used to precalculate stuff that doesn't depend on input values
        """
        if self._t:
            self._last_t = self._t
        self._t += dt
        

    def __cleanState__(self, stateDict):
        """
        Cleans given state dictionary from state objects beginning with __
        """
        for k in list(stateDict.keys()):
            # Remove internal variables
            if k.startswith('_'):
                stateDict.pop(k)
            # Remove parameter offsets
            if k.startswith('@'):
                stateDict.pop(k)
            # Reset to original values
            if k.startswith('~'):
                stateDict[k[1:]] = stateDict[k]
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

    def updateParameter(self, stateDict):
        self.__setstate__(stateDict)
    
    def setParameterOffset(self, paramId, paramDefinition, offset):
        state = self.__dict__.copy()
        # Get min and max range of parameter from parameterDefinition
        paramDef = paramDefinition['parameters'][paramId]
        if len(paramDef) != 4:
            return
        minP = paramDef[1]
        maxP = paramDef[2]

        # Store original value if not already stored
        origVal = state.get('~'+paramId, None)
        if origVal is None:
            origVal = state.get(paramId, None)
            if origVal is not None:
                state['~'+paramId] = origVal
        
        adjustedValue = origVal + (maxP - minP) * offset
        # ensure we stay inside max and min
        adjustedValue = min(maxP, adjustedValue)
        adjustedValue = max(minP, adjustedValue)
        state[paramId] = adjustedValue

        # store offset for getParameterOffset
        state['@'+paramId] = offset
        self.__setstate__(state)
        
        
    def getParameterOffset(self, paramId):
        return self.__dict__.get('@'+paramId, None)

    def resetParameterOffsets(self):
        for k in list(self.__dict__.keys()):
            if k.startswith('@'):
                self.__dict__.pop(k)
        

    def getParameter(self):
        definition = self.getParameterDefinition()
        print(definition)
        return definition

    @staticmethod
    def getParameterDefinition():
        return {}
        
    @staticmethod
    def getParameterHelp():
        return {}
    
    @staticmethod
    def getEffectDescription():
        return ""

    def _inputBufferValid(self, index, buffer_type=PixelBuffer.__name__):
        if self._inputBuffer is None:
            return False
        if len(self._inputBuffer) <= index:
            return False
        if self._inputBuffer[index] is None:
            return False
        if buffer_type is AudioBuffer.__name__:
            if not isinstance(self._inputBuffer[index], AudioBuffer):
                raise RuntimeError("Input {}: Audio input expected.".format(index))

        return True

    def setNumOutputPixels(self, num_pixels):
        self._num_pixels = num_pixels
        if num_pixels is not None:
            self._num_pixels = int(num_pixels)

    def getNumOutputPixels(self):
        return self._num_pixels

    def getNumInputPixels(self, channel):
        # Default: Same pixels as output
        return self._num_pixels

    def setNumOutputRows(self, num_rows):
        self._num_rows = num_rows
        if num_rows is not None:
            self._num_rows = int(num_rows)
    
    def getNumOutputRows(self):
        return self._num_rows

    def getNumInputRows(self, channel):
        # Default: Same number of columns as output
        return self._num_rows
