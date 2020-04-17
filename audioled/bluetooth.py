
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

        logger.debug('BluetoothMidiLELevelCharacteristic - %s - onWriteRequest: value = %s' % (self['uuid'], [hex(c) for c in self._value]))
        # Strip first two bytes?
        # TODO: BLE adds bytes?
        header = self._value[0]
        timestamp_low = self._value[1]
        
        try:
            msgs = []
            msg = self._value[2:] # Strip header and lower timestamp
            logger.info("Parsing {}".format([hex(c) for c in msg]))
            midi = mido.parse(msg)
            if midi is not None:
                msgs += [midi]
            else:
                # Probably sysex?
                if msg[0] == 0xF0:
                    endSysex = msg.index(0xF7)
                    msg = msg[:endSysex+1]
                    # Remove timestamps?
                    msg = [item for index, item in enumerate(msg) if (index + 1) % 4 != 0]
                    logger.info("Parsing sysex to {}: {}".format(endSysex, [hex(c) for c in msg]))
                    midi = mido.Message.from_bytes(msg)
                    msgs += [midi]

            for msg in msgs:
                logger.info("message is: ")
                if msg.type == 'program_change':
                    logger.info("is program change: {}".format(msg.program))
                if msg.type == 'sysex':
                    logger.info("is sysex: {}".format(msg.data))
                if self._msgReceivedCallback is not None:
                    self._msgReceivedCallback(msg)
        except ValueError as e:
            logger.error("Error decoding midi: {}".format(e))

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
        if msg.type is not 'sysex' or True:
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