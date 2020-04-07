
import sys
import signal
import mido
import pybleno
import logging
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
            logger.info(('Could not import the pybleno library')
            logger.info(('For installation instructions, see {}'.format(url))
            logger.info(('If running on RaspberryPi, please install.')
        except OSError:
            logger.info(("Seems like pybleno is not working.")
            url = 'https://github.com/Adam-Langley/pybleno'
            logger.info(('For installation instructions, see {}'.format(url))
            logger.info(('If running on RaspberryPi, please install.')
            
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
        logger.info(('EchoCharacteristic - %s - onReadRequest: value = %s' % (self['uuid'], [hex(c) for c in self._value]))
        callback(pybleno.Characteristic.RESULT_SUCCESS, self._value[offset:])

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        self._value = data

        logger.info(('EchoCharacteristic - %s - onWriteRequest: value = %s' % (self['uuid'], [hex(c) for c in self._value]))
        msgs = mido.parse_all(self._value)
        for msg in msgs:
            if msg.type == 'program_change':
                logger.info(("is program change: {}".format(msg.program))
            if self._msgReceivedCallback is not None:
                self._msgReceivedCallback(msg)

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
        logger.info(("Received msg: {}".format(msg))
        if self._callback is not None:
            self._callback(msg)
        

    def _onStateChange(self, state):
        logger.info(('on -> stateChange: ' + state);

        if (state == 'poweredOn'):
            self.bleno.startAdvertising('MOLECOLE Control', [self.primaryService.uuid]);
        else:
            self.bleno.stopAdvertising();
    

    def _onAdvertisingStart(self, error):
        logger.info(('on -> advertisingStart: ' + ('error ' + error if error else 'success'));

        if not error:
            def on_setServiceError(error):
                logger.info(('setServices: %s'  % ('error ' + error if error else 'success'))
                
            self.bleno.setServices([
                self.primaryService
            ], on_setServiceError)