
import logging
import mido
import sys
import threading
from audioled_controller import bluetooth, grpc_midi_pb2, grpc_midi_pb2_grpc
import grpc
import time
import queue


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
grpc_thread = None
msgQueue = queue.SimpleQueue()

def callback(msg: mido.Message):
    global grpc_client
    global msgQueue
    logger.info("Bluetooth received {}".format(msg))
    send_msg = grpc_midi_pb2.Sysex()
    send_msg.data = bytes(msg.bytes())
    
    if grpc_client is None:
        # Add msg to queue and continue
        if send_msg is not None:
            msgQueue.put(send_msg)
    if grpc_client is not None:
        # Try sending message directly
        try:
            grpc_client.SendMidi(send_msg)
        except Exception as e:
            logger.error("Error sending message.. {}".format(e))
            grpc_client = None
            if send_msg is not None:
                msgQueue.put(send_msg)
            

def msgStream():
    msg = grpc_midi_pb2.Empty()
    yield msg

def midiChat(channel):
    global bt
    global grpc_client
    global msgQueue
    for unsend in iter(msgQueue.get, None):
        logger.info("Processing..")
        try:
            logger.info("Start receiving...")
            grpc_client = grpc_midi_pb2_grpc.MidiStub(channel)
            for msg in grpc_client.MidiChat(msgStream()):
                midi_msg = mido.Message.from_bytes(msg.data)
                logger.info("Received {}".format(midi_msg))
                bt.send(midi_msg)
        except Exception as e:
            logger.error(e)
            grpc_client = None
        finally:
            logger.info("Stop receiving...")

    

def createClient():
    global grpc_client
    global grpc_thread
    try:
        channel = grpc.insecure_channel('localhost:5001')
        grpc_thread = threading.Thread(target=midiChat, args=(channel,), daemon=True).start()
    except Exception as e:
        logger.error(e)
        return None
    return grpc_client



if __name__ == '__main__':
    logger.info("Advertising bluetooth")
    bt = bluetooth.MidiBluetoothService(callback=callback, advertiseName='MOLECOLE Control')
    logger.info("Creating virtual MIDI port")
    grpc_client = createClient()
    while True:
        time.sleep(0.1)
    logger.info("Exiting")
