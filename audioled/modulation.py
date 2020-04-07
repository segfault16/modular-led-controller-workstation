from __future__ import (absolute_import, division, print_function, unicode_literals)

from collections import OrderedDict

import math
import inspect

import logging
logger = logging.getLogger(__name__)


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
                    logger.info("Backwards compatibility: Adding default value {}={}".format(key, argsWithDefaults[key]))
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

        try:
            self._last_t = self._t - dt
        except AttributeError:
            self._last_t = 0

    def getValue(self):
        pass

    def updateParameter(self, stateDict):
        self.__setstate__(stateDict)

    def getParameter(self):
        definition = self.getParameterDefinition()
        logger.info(definition)
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


class ExternalLinearController(ModulationSource):
    def __init__(self, amount=.0):
        self.amount = amount

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters": OrderedDict([
                # default, min, max, stepsize
                ("amount", [1.0, .0, 1.0, .001]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "amount": "Global scale of the controller.",
            }
        }
        return help

    def getValue(self):
        return self.amount


class SineLFO(ModulationSource):
    def __init__(self, freqHz=.0, depth=1.0):
        self.depth = depth
        self.freqHz = freqHz

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("depth", [1.0, .0, 1.0, .001]),
                ("freqHz", [0.01, .0, 60.0, .01]),
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "depth": "Depth of the LFO target.",
                "freqHz": "LFO Freq in Hz.",
            }
        }
        return help

    def update(self, dt):
        """
        Update timing, can be used to precalculate stuff that doesn't depend on input values
        """
        super().update(dt)

    def getValue(self):
        return self.depth * math.sin(self._t * self.freqHz)
