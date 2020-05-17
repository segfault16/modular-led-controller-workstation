from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
import asyncio
from audioled import effects, audio, audioreactive, colors, generative, panelize  # noqa: F401


class Test_Effects(unittest.TestCase):
    def test_allEffectsHaveDescription(self):
        self.maxDiff = None
        childclasses = inheritors(effects.Effect)
        effectsWithoutDescription = []
        for _class in childclasses:
            if (len(_class.getEffectDescription())) == 0:
                effectsWithoutDescription.append(_class)
        self.assertEqual([], effectsWithoutDescription)

    def test_allEffectsAllParametersHaveDescription(self):
        self.maxDiff = None
        childclasses = inheritors(effects.Effect)
        effectsWithMissingParameterDescription = []
        for _class in childclasses:
            if _class.__name__ == 'MidiKeyboard':  # exclude midikeyboard
                continue
            if 'parameters' in _class.getParameterDefinition():
                parameters = _class.getParameterDefinition()['parameters']
                try:
                    parameterDescription = _class.getParameterHelp()['parameters']
                    for key, value in parameters.items():
                        if parameterDescription.get(key) is None:
                            effectsWithMissingParameterDescription.append("{} has no help for parameter {}".format(
                                _class, key))
                except Exception:
                    effectsWithMissingParameterDescription.append("{} has no parameter help at all".format(_class))

        self.assertEqual([], effectsWithMissingParameterDescription)

    def test_allEffectsUpdateAndProcessWithoutConnection(self):
        childclasses = inheritors(effects.Effect)
        for _class in childclasses:
            if _class.__name__ == 'MidiKeyboard':  # exclude midikeyboard
                continue
            instance = None
            try:
                instance = _class()
            except Exception as e:
                print("Error instanciating effect {}".format(_class.__name__))
                raise ValueError("Error instanciating effect {}: {}".format(_class.__name__, e)) from e
            event_loop = asyncio.get_event_loop()
            event_loop.run_until_complete(instance.update(0.01))
            instance.process()
        else:
            print("Skipping {}".format(_class.__name__))


def inheritors(klass):
    subclasses = set()
    work = [klass]
    while work:
        parent = work.pop()
        for child in parent.__subclasses__():
            if child not in subclasses:
                subclasses.add(child)
                work.append(child)
    return subclasses
