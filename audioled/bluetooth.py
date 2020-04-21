
import sys
import signal
import mido
import pybleno
from pybleno import *
import traceback
import logging
import array
logger = logging.getLogger(__name__)


class BluetoothMidiLELevelCharacteristic(pybleno.Characteristic):
    def __init__(self, _msgReceivedCallback):
        try:
            logger.debug("Init MIDI-BLE characteristic")
            pybleno.Characteristic.__init__(self, {
                'uuid': '7772e5db-3868-4112-a1a9-f2669d106bf3',
                'properties': ['read', 'write', 'writeWithoutResponse', 'notify'],
                # 'secure': ['read', 'write', 'writeWithoutResponse', 'notify'],
                'value': None,
                'descriptors': []
                })
        except ImportError:
            url = 'https://github.com/Adam-Langley/pybleno'
            logger.error('Could not import the pybleno library')
            logger.error('For installation instructions, see {}'.format(url))
            logger.error('If running on RaspberryPi, please install.')
        except OSError:
            logger.error("Seems like pybleno is not working.")
            url = 'https://github.com/Adam-Langley/pybleno'
            logger.error('For installation instructions, see {}'.format(url))
            logger.error('If running on RaspberryPi, please install.')
            
        self._msgReceivedCallback = _msgReceivedCallback
        self._value = pybleno.array.array('B', [0] * 0)
        self._updateValueCallback = None
        self._isSysex = False
        self._writeBuffer = pybleno.array.array('B', [0] * 0)
          
    # def onReadRequest(self, offset, callback):
    #     if sys.platform == 'darwin':
    #     	output = subprocess.check_output("pmset -g batt", shell=True)
    #     	result = {}
    #     	for row in output.split('\n'):
    #     		if 'InternalBatter' in row:
    #     			percent = row.split('\t')[1].split(';')[0];
    #     			percent = int(re.findall('\d+', percent)[0]);
    #     			callback(Characteristic.RESULT_SUCCESS, array.array('B', [percent]))
    #     			break
    #     else:
    #         # return hardcoded value
    #         callback(Characteristic.RESULT_SUCCESS, array.array('B', [98]))

    def onReadRequest(self, offset, callback):
        logger.debug('BluetoothMidiLELevelCharacteristic - %s - onReadRequest: value = %s' % (self['uuid'], [hex(c) for c in self._value]))
        callback(pybleno.Characteristic.RESULT_SUCCESS, self._value[offset:])

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        self._value = data
        
        logger.debug('BluetoothMidiLELevelCharacteristic - %s - onWriteRequest: value = %s (%s)' % (self['uuid'], [hex(c) for c in self._value], offset))
        if self._value is None or len(self._value) <= 2:
            logger.error("Not enough bytes in MIDI-BLE message")
            return
        # First byte: Header byte
        header = self._value[0]
        if not header & 0x80:
            logger.error("Package in MIDI-BLE message doesn't start with status byte set")
            return

        msg = self._value[1:]  # Strip header
        
        msgs = []
        timestampIndex = 0
        lastStatus = None
        # Handle sysex message over multiple packets
        if self._isSysex:
            # Check if the incoming package is continuation of sysex Midi
            # If the second byte has status bit set, something is off
            if len(msg) > 1 and msg[0] & 0x80:
                logger.warning("Error in sysex receive, unexpected package")
                self._isSysex = False
                self._writeBuffer = []
            else:
                # Append the data
                logger.debug("Sysex multiple packages, adding {} to {} bytes".format(len(msg), len(self._writeBuffer)))
                self._writeBuffer = [*self._writeBuffer, *msg]
                msg = self._writeBuffer[1:]
        else:
            # Second byte: Timestamp byte
            timestamp_low = self._value[1]
            if not timestamp_low & 0x80:
                logger.error("Second MIDI-BLE byte not status")
                return

        logger.debug("Parsing {}".format([hex(c) for c in msg]))

        for id, inByte in enumerate(msg):
            # First byte is always timestamp
            if id <= timestampIndex:
                logger.debug("Skipping timestamp idx {}: {}".format(id, hex(inByte)))
                continue
            
            # respect running status
            if lastStatus is None:
                if not inByte & 0x80:
                    # TODO: Midi sysex over multiple packages
                    logger.debug("TODO: Sysex multiple packages")
                    pass
            
            if inByte & 0x80 and id < len(msg) - 1 and msg[id+1] & 0x80:
                # Midi status only byte
                logger.debug("Midi status only messages {}".format(hex(inByte)))
                msgs.append([inByte])
                timestampIndex = id + 1
                continue
            elif inByte & 0x80 and not inByte == 0xF7:
                # Save status
                logger.debug("New status: {}".format(hex(inByte)))
                lastStatus = inByte
                if inByte == 0xF0:
                    logger.debug("Sysex start")
                    self._isSysex = True
            else:
                # Check preceding byte for new timestamp
                if id < len(msg) - 1 and msg[id+1] & 0x80 and not msg[id+1] == 0xF7:
                    logger.debug("Next byte after {} is timestamp".format(hex(inByte)))
                    if id < len(msg) - 2 and msg[id+1] & 0x80 and msg[id+2] == 0xF7:
                        # End of sysex
                        logger.debug("End of sysex")
                        newMsg = msg[timestampIndex:id+1]
                        newMsg.append(0xF7)
                        msgs.append(newMsg)
                        timestampIndex = id+3
                        self._isSysex = False
                    else:
                        logger.debug("End of midi message")
                        # End of message indicated by new timestamp
                        newMsg = msg[timestampIndex:id+1]
                        
                        if not newMsg[0] & 0x80:
                            # Add running status
                            newMsg = [lastStatus] + newMsg
                        msgs.append(newMsg)
                        # skip first byte in next iteration
                        timestampIndex = id+1
                else:
                    # logger.debug("Skipping data byte {}".format(hex(inByte)))
                    continue
        # last message
        if timestampIndex < len(msg):
            msgs.append(msg[timestampIndex:])
        # Parse messages to midi
        midiMsgs = []  # type: [mido.Message]
        for m in msgs:
            logger.debug("Parsing message {}".format([hex(c) for c in m]))
            try:
                midi = mido.Message.from_bytes(m[1:]) # Strip timestamp on parse
                midiMsgs.append(midi)
            except ValueError as e:
                logger.error("Error decoding midi: {}".format(e))

        if self._isSysex and len(self._writeBuffer) == 0:
            # Begin storing buffer
            self._writeBuffer = self._value

        for msg in midiMsgs:
            logger.info("message is: {}".format(msg))
            if msg.type == 'program_change':
                logger.info("is program change: {}".format(msg.program))
            if msg.type == 'sysex':
                logger.info("is sysex: {}".format(msg.data))
            if self._msgReceivedCallback is not None:
                self._msgReceivedCallback(msg)


    def onSubscribe(self, maxValueSize, updateValueCallback):
        logger.debug('EchoCharacteristic - onSubscribe')
        
        self._updateValueCallback = updateValueCallback

    def onUnsubscribe(self):
        logger.debug('EchoCharacteristic - onUnsubscribe');
        
        self._updateValueCallback = None

    def sendMidi(self, msg : mido.Message):
        if self._updateValueCallback is None:
            logger.debug("No subscription?")
            return
        bytes = msg.bytes()
        if msg.type != 'sysex' or True:
            bytes =  [0x80, 0x80] + msg.bytes()

        logger.debug("Writing {}".format([hex(c) for c in bytes]))
        
        self._updateValueCallback(bytes)



class BluetoothMidiLEService(pybleno.BlenoPrimaryService):
    def __init__(self, _msgReceivedCallback):
        self._characteristic = BluetoothMidiLELevelCharacteristic(_msgReceivedCallback)
        pybleno.BlenoPrimaryService.__init__(self, {
          'uuid': '03b80e5a-ede8-4b33-a751-6ce34ec4c700',
          'characteristics': [
              self._characteristic
          ],
        })

class MidiBluetoothService(object):
    def __init__(self, callback = None):
        self._callback = callback
        self.bleno = pybleno.Bleno()
        self.primaryService = BluetoothMidiLEService(self._onMessageReceived);
        self.primaryServiceName = 'MOLECOLE Control'


        self.bleno.on('advertisingStart', self._onAdvertisingStart)
        self.bleno.on('stateChange', self._onStateChange)
        logging.info("Advertising Bluetooth Service")
        self.bleno.start()
        # self.bleno.startAdvertising("MOLECOLE Control")

        # logger.info( ('Hit <ENTER> to disconnect')

        # if (sys.version_info > (3, 0)):
        #     input()
        # else:
        #     raw_input()

        # bleno.stopAdvertising()
        # bleno.disconnect()

        # logger.info( ('terminated.')
        # sys.exit(1)

    def _onMessageReceived(self, msg : mido.Message):
        logger.debug("Received msg: {}".format(msg))
        if self._callback is not None:
            try:
                self._callback(msg)
            except Exception as e:
                logger.error("Error in bluetooth callback: {}".format(e))
                traceback.print_tb(e.__traceback__)

        

    def _onStateChange(self, state):
        logger.debug('on -> stateChange: ' + state);

        if (state == 'poweredOn'):
            self.bleno.startAdvertising(self.primaryServiceName, [self.primaryService.uuid]);
        else:
            self.bleno.stopAdvertising();
    

    def _onAdvertisingStart(self, error):
        logger.debug('on -> advertisingStart: ' + ('error ' + error if error else 'success'));

        if not error:
            def on_setServiceError(error):
                logger.debug('setServices: %s'  % ('error ' + error if error else 'success'))
                
            self.bleno.setServices([
                self.primaryService
            ], on_setServiceError)
            logger.info("Started Bluetooth advertising")

    def getName(self):
        if self.primaryService is None:
            return None
        return self.primaryServiceName

    def sendMidi(self, msg : mido.Message):
        if self.primaryService is None:
            return
        self.primaryService._characteristic.sendMidi(msg)