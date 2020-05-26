
import logging
import mido
import sys
import mido.backends.rtmidi  # Pyupdate required
from audioled_controller import bluetooth, grpc_midi_pb2, grpc_midi_pb2_grpc
import grpc


logger = logging.getLogger(__name__)
orig_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = orig_factory(*args, **kwargs)
    record.sname = record.name[-10:] if len(record.name) > 10 else record.name
    if record.threadName and len(record.threadName) > 10:
        record.sthreadName = record.threadName[:10]
    elif not record.threadName:
        record.sthreadName = ""
    else:
        record.sthreadName = record.threadName
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(stream=sys.stdout,
                    level=logging.INFO,
                    format='[%(relativeCreated)6d %(sthreadName)10s  ] %(sname)10s:%(levelname)s %(message)s')

midi_out = None

def callback(msg: mido.Message):
    global midi_out
    logger.info("Bluetooth received {}".format(msg))
    if msg.type == 'control_change' and msg.control == 121:
        # Reset all controllers, close backchannel
        logger.info("Received reset all controllers via bluetooth, closing backchannel")
        midi_out = None
    if midi_out is None:
        try:
            logger.info("Connecting to existing port")
            midi_out = mido.open_output('MOLECOLE Control In')
        except Exception as e:
            logger.error(e)
    if midi_out is not None:
        logger.info("Relay {}".format(msg))
        midi_out.send(msg)

def midiChat(stub: grpc_midi_pb2_grpc.MidiStub):
    stub.MidiChat([mido.Message('note_on').bytes])

if __name__ == '__main__':
    logger.info("Advertising bluetooth")
    bt = bluetooth.MidiBluetoothService(callback=callback, advertiseName='MOLECOLE Control')
    logger.info("Creating virtual MIDI port")
    with grpc.insecure_channel('localhost:5001') as channel:
        stub = grpc_midi_pb2_grpc.MidiStub(channel)
        midiChat(stub)
    logger.info("Exiting")
    # midi_in = mido.open_input('MOLECOLE Control Out', virtual=True)
    # for msg in midi_in:
    #     logger.info("Received {}".format(msg))
    #     if msg.type == 'control_change' and msg.control == 121:
    #         # Reset all controllers, close backchannel
    #         logger.info("Received reset all controllers, closing backchannel")
    #         midi_out = None
    #     if bt is not None:
    #         bt.send(msg)
