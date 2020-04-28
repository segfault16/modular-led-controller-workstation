from __future__ import (absolute_import, division, print_function, unicode_literals)

from collections import OrderedDict

import math
import inspect

import logging
logger = logging.getLogger(__name__)

CTRL_MODULATION = 'Modulation'
CTRL_SPEED = 'Speed'
CTRL_INTENSITY = 'Intensity'
CTRL_BRIGHTNESS = 'Brightness'  # Not available on purpose, handled globally
CTRL_PRIMARY_COLOR_R = 'PrimaryColor_r'
CTRL_PRIMARY_COLOR_G = 'PrimaryColor_g'
CTRL_PRIMARY_COLOR_B = 'PrimaryColor_b'
CTRL_SECONDARY_COLOR_R = 'SecondaryColor_r'
CTRL_SECONDARY_COLOR_G = 'SecondaryColor_g'
CTRL_SECONDARY_COLOR_B = 'SecondaryColor_b'
availableController = [CTRL_MODULATION, CTRL_SPEED, CTRL_INTENSITY]
allController = [CTRL_MODULATION, CTRL_SPEED, CTRL_INTENSITY, CTRL_PRIMARY_COLOR_R, CTRL_PRIMARY_COLOR_G, CTRL_PRIMARY_COLOR_B, CTRL_SECONDARY_COLOR_R, CTRL_SECONDARY_COLOR_G, CTRL_SECONDARY_COLOR_B]

class ModulationSource(object):
    """
    Base class for ModulationSource

    ModulationSource have a number of parameters. Basically same as effect baseclass
    """
    def __init__(self):
        self.__initstate__()

    def __initstate__(self):
        try:
            self._t
        except AttributeError:
            self._t = 0
        # make sure all default values are set (basic backwards compatibility) # TODO: Duplicate code in effect?
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

    def isControlledBy(self, controller):
        return False

    def resetControllerModulation(self):
        pass

    def getControllerModulation(self, controller, param = None):
        if self.isControlledBy(controller):
            return self.getValue(param)

    @staticmethod
    def getParameterDefinition():
        return {}

    @staticmethod
    def getParameterHelp():
        return {}

    @staticmethod
    def getEffectDescription():
        return ""


# TODO: Shouldn't show up
class ExternalColourController(ModulationSource):
    def __init__(self, amount=.0):
        self.amount = amount

    def __initstate__(self):
        super().__initstate__()
        try:
            self.r
        except AttributeError:
            self.r = None
        try:
            self.g
        except AttributeError:
            self.g = None
        try:
            self.b
        except AttributeError:
            self.b = None
        try:
            self.controllerAmount
        except AttributeError:
            self.controllerAmount = None

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
        help = {"parameters": {"amount": "Global scale of the controller."}}
        return help

    def update(self, dt):
        """
        Update timing, can be used to precalculate stuff that doesn't depend on input values
        """
        super().update(dt)

    def updateParameter(self, stateDict):
        super().updateParameter(stateDict)
        if 'amount' in stateDict:
            # Reset remote controller value
            self.resetControllerModulation()

    def getValue(self, param=None):
        if not isinstance(self.amount, float) and not isinstance(self.amount, int):
            self.amount = 0.

        if param is None:
            if self.controllerAmount is None:
                return self.amount
            return self.controllerAmount

        if param in self.__dict__:
            return self.__dict__[param]

        return None

    def resetControllerModulation(self):
        self.controllerAmount = None


class ExternalColourAController(ExternalColourController):
    def __init__(self, amount=0.):
        super().__init__(amount)

    def isControlledBy(self, controller):
        return controller == CTRL_PRIMARY_COLOR_R or controller == CTRL_PRIMARY_COLOR_G or controller == CTRL_PRIMARY_COLOR_B


class ExternalColourBController(ExternalColourController):
    def __init__(self, amount=0.):
        super().__init__(amount)

    def isControlledBy(self, controller):
        return controller == CTRL_SECONDARY_COLOR_R or controller == CTRL_SECONDARY_COLOR_G or controller == CTRL_SECONDARY_COLOR_B


class ExternalLinearController(ModulationSource):
    def __init__(self, amount=.0, controller=None):
        self.amount = amount
        self.controller = controller

    def __initstate__(self):
        super().__initstate__()
        try:
            self.controllerAmount
        except AttributeError:
            self.controllerAmount = None

    @staticmethod
    def getParameterDefinition():
        definition = {
            "parameters":
            OrderedDict([
                # default, min, max, stepsize
                ("amount", [1.0, .0, 1.0, .001]),
                ("controller", availableController)
            ])
        }
        return definition

    @staticmethod
    def getParameterHelp():
        help = {
            "parameters": {
                "amount": "Global scale of the controller.",
                "controller": "Which remote controller will control this modulation."
            }
        }
        return help

    def updateParameter(self, stateDict):
        super().updateParameter(stateDict)
        if 'amount' in stateDict:
            # Reset remote controller value
            self.resetControllerModulation()

    def getValue(self, param=None):
        if not isinstance(self.amount, float) and not isinstance(self.amount, int):
            self.amount = 0.

        if param is None:
            try:
                self.controllerAmount
            except AttributeError:
                self.controllerAmount = None
            if self.controllerAmount is None:
                return self.amount
            return self.controllerAmount

        if param in self.__dict__:
            return self.__dict__[param]

        return None

    def isControlledBy(self, controller):
        if self.controller is not None and self.controller == controller:
            return True
        return False

    def resetControllerModulation(self):
        self.controllerAmount = None


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
