
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

bt = None
grpc_client = None

def callback(msg: mido.Message):
    logger.info("Bluetooth received {}".format(msg))
    if grpc_client is not None:
        send_msg = grpc_midi_pb2.Sysex()
        send_msg.data = bytes(msg.bytes())
        grpc_client.SendMidi(send_msg)

def msgStream():
    msg = grpc_midi_pb2.Empty()
    yield msg

def midiChat(stub: grpc_midi_pb2_grpc.MidiStub):
    global bt
    for msg in stub.MidiChat(msgStream()):
        midi_msg = mido.Message.from_bytes(msg.data)
        logger.info("Received {}".format(midi_msg))
        bt.send(midi_msg)
    pass


if __name__ == '__main__':
    logger.info("Advertising bluetooth")
    bt = bluetooth.MidiBluetoothService(callback=callback, advertiseName='MOLECOLE Control')
    logger.info("Creating virtual MIDI port")
    with grpc.insecure_channel('localhost:5001') as channel:
        grpc_client = grpc_midi_pb2_grpc.MidiStub(channel)
        midiChat(grpc_client)
    logger.info("Exiting")
