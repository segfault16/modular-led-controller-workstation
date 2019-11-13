from collections import OrderedDict
import inspect


class ModulationSource(object):
    """
    Base class for ModulationSource

    ModulationSource have a number of parameters
    """

    def __init__(self):
        self.__initstate__()

    def __initstate__(self):
        try:
            self._t
        except AttributeError:
            self._t = 0
        # make sure all default values are set (basic backwards compatibility)
        argspec = inspect.getargspec(self.__init__)
        if argspec.defaults is not None:
            argsWithDefaults = dict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
            for key in argsWithDefaults:
                if key not in self.__dict__:
                    print("Backwards compatibility: Adding default value {}={}".format(key, argsWithDefaults[key]))
                    self.__dict__[key] = argsWithDefaults[key]

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

    def update(self, dt):
        """
        Update timing, can be used to precalculate stuff that doesn't depend on input values
        """
        try:
            self._t += dt
        except AttributeError:
            self._t = 0

    def updateParameter(self, stateDict):
        self.__setstate__(stateDict)

    def getParameter(self):
        return {}

    @staticmethod
    def getParameterDefinition():
        return {}
        
    @staticmethod
    def getParameterHelp():
        return {}
    
    @staticmethod
    def getEffectDescription():
        return ""


class ExternalLinearController(ModulationSource):

    def __init__(self, offset=.0):
        self.offset = offset

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("offset", [.0, .0, 1.0, .001]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "offset": "Static offset.",
            }
        }
        return help

    def getParameter(self):
        definition = self.getParameterDefinition()
        definition['parameters']['offset'][0] = self.offset
        return definition
