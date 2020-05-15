from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import
import unittest
import time
from audioled_controller import sysex_data, midi_timestamp

class TestMidiSysex(unittest.TestCase):
    def test_midi_timestamp(self):
        curTime = int(round(time.time() * 1000))
        print("curtime: {}".format(curTime))
        midiTime = midi_timestamp.toMidiTime(curTime)
        print("midiTime: {}".format(midiTime))
        sysTime = midi_timestamp.toSysTime(midiTime)
        print("systime: {}".format(sysTime))
        midiTimeAgain = midi_timestamp.toMidiTime(sysTime)
        print("midiTimeAgain: {}".format(midiTimeAgain))
        self.assertListEqual(midiTime, midiTimeAgain)

    def test_enc_0x00(self):
        to_enc = [0x00]
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x00, 0x00])

    def test_dec_0x00(self):
        to_dec = [0x00, 0x00]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0x00])

    def test_enc_0x80(self):
        to_enc = [0x80]
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x00, 0x40])

    def test_dec_0x80(self):
        to_dec = [0x00, 0x40]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0x80])

    def test_enc_list1(self):
        to_enc = [0x00, 0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6]
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x00, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x3F])
    
    def test_dec_list1(self):
        to_dec = [0x00, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x3F]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0x00, 0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6])
    
    def test_enc_list1rev(self):
        to_enc = [0xF6, 0xE5, 0xD4, 0xC3, 0xB2, 0xA1, 0x00]
        # 0 1 1 1 1 1 1 0
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x76, 0x65, 0x54, 0x43, 0x32, 0x21, 0x00, 0x7E])

    def test_dec_list1rev(self):
        to_dec = [0x76, 0x65, 0x54, 0x43, 0x32, 0x21, 0x00, 0x7E]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0xF6, 0xE5, 0xD4, 0xC3, 0xB2, 0xA1, 0x00])
    
    def test_enc_list1_long(self):
        to_enc = [0xF6, 0xE5, 0xD4, 0xC3, 0xB2, 0xA1, 0x00, 0x00, 0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6]
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x76, 0x65, 0x54, 0x43, 0x32, 0x21, 0x00, 0x7E, 0x00, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x3F])

    def test_dec_list1_long(self):
        to_dec = [0x76, 0x65, 0x54, 0x43, 0x32, 0x21, 0x00, 0x7E, 0x00, 0x21, 0x32, 0x43, 0x54, 0x65, 0x76, 0x3F]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0xF6, 0xE5, 0xD4, 0xC3, 0xB2, 0xA1, 0x00, 0x00, 0xA1, 0xB2, 0xC3, 0xD4, 0xE5, 0xF6])
    
    def test_enc_list2(self):
        to_enc = [0x00, 0xA1]
        enc = sysex_data.encode(to_enc)
        self.assertListEqual(enc, [0x00, 0x21, 0x20])

    def test_dec_list2(self):
        to_dec = [0x00, 0x21, 0x20]
        dec = sysex_data.decode(to_dec)
        self.assertListEqual(dec, [0x00, 0xA1])

