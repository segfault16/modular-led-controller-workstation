from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
from unittest import mock
import mido
from audioled_controller import midi_full, sysex_data

class TestMidiFullController(unittest.TestCase):
    def test_get_version(self):
        # Setup
        f = mock.Mock()
        ctrl = midi_full.MidiProjectController(callback=f)
        # Get Version messsage
        testMsg = mido.Message('sysex')
        testMsg.data = [0x00, 0x00]
        # Handle message
        ctrl.handleMidiMsg(testMsg, None)
        retMsg = f.call_args[0][0]
        # Check response message ID
        self.assertEqual(retMsg.data[0], 0x00)
        self.assertEqual(retMsg.data[1], 0x00)
        # Decode data
        dec = sysex_data.decode(retMsg.data[2:])
        version = str(bytes(dec), encoding='utf8')
        # Check is version string
        version.split('.')
        self.assertTrue(len(version.split('.')) == 4)