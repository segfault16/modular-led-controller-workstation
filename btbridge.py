
import logging
import mido
import sys
import threading
from audioled_controller import bluetooth, grpc_midi_pb2, grpc_midi_pb2_grpc
import grpc
import time
import queue
import argparse
import os


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
                    level=os.environ.get("LOGLEVEL", "INFO"),
                    format='[%(relativeCreated)6d %(sthreadName)10s  ] %(sname)10s:%(levelname)s %(message)s')

bt = None
grpc_client = None
grpc_thread = None
msgQueue = queue.SimpleQueue()

def callback(msg: mido.Message):
    global grpc_client
    global msgQueue
    
    send_msg = grpc_midi_pb2.Sysex()
    send_msg.data = bytes(msg.bytes())
    
    if grpc_client is None:
        # Add msg to queue and continue
        if send_msg is not None:
            msgQueue.put(send_msg)
    if grpc_client is not None:
        # Try sending message directly
        try:
            logger.info("BT RECEIVE -> GRPC SEND")
            logger.debug("BT RECEIVE -> GRPC SEND {}".format(msg))
            grpc_client.SendMidi(send_msg)
        except Exception as e:
            logger.error("Error sending message.. {}".format(e))
            grpc_client = None
            if send_msg is not None:
                msgQueue.put(send_msg)

def sendMsgAfter(send_msg: grpc_midi_pb2.Sysex, delay: float):
    time.sleep(delay)
    global grpc_client

    if grpc_client is not None:
        # Try sending message directly
        try:
            logger.info("BT RECEIVE -> GRPC SEND DIRECT")
            logger.debug("BT RECEIVE -> GRPC SEND DIRECT {}".format(send_msg))
            grpc_client.SendMidi(send_msg)
        except Exception as e:
            logger.error("Error sending message.. {}".format(e))
    else:
        logger.error("FATAL. Could not send message {}".format(send_msg))

def msgStream():
    msg = grpc_midi_pb2.Empty()
    yield msg


thread_lock = threading.Lock()

def startThreading(channel):
    global thread_lock
    global grpc_client
    try:
        thread_lock.acquire()
        if grpc_client is None:
            logger.info("Start receiving GRPC...")
            grpc_client = grpc_midi_pb2_grpc.MidiStub(channel)
            thread_lock.release()
            for msg in grpc_client.MidiChat(msgStream()):
                midi_msg = mido.Message.from_bytes(msg.data)
                logger.info("GRPC RECEIVE -> BT SEND")
                logger.debug("GRPC RECEIVE -> BT SEND {}".format(midi_msg))
                bt.send(midi_msg)
        else:
            thread_lock.release()
    except Exception as e:
        logger.error("Error starting thread {}".format(e))
        grpc_client = None
        

def midiChat(channel):
    global bt
    global grpc_client
    global msgQueue
    for unsend in iter(msgQueue.get, None):
        logger.debug("Start chat with GRPC server starting with {}".format(unsend))
        threading.Thread(target=sendMsgAfter, args=([unsend, 0.1])).start()
        threading.Thread(target=startThreading, args=([channel])).start()
        

def createClient():
    global grpc_client
    global grpc_thread
    try:
        channel = grpc.insecure_channel('localhost:5001')
        grpc_thread = threading.Thread(target=midiChat, args=(channel,), daemon=True).start()
    except Exception as e:
        logger.error("Error creating client: {}".format(e))
        return None
    return grpc_client


if __name__ == '__main__':
    advertiseName = 'MOLECOLE BTBridge Control'

    parser = argparse.ArgumentParser(description='BTBrige - a Bridge from Bluetooth LE MIDI to GRPC')
    parser.add_argument(
        '--name',
        '-N',
        dest='name',
        default=advertiseName,
        help='Name of MIDI-BLE Port to be advertised',
    )
    args = parser.parse_args()
    if args.name:
        advertiseName = args.name
    logger.info("Advertising MIDI-BLE as '{}'".format(advertiseName))
    bt = bluetooth.MidiBluetoothService(callback=callback, advertiseName=advertiseName)
    logger.info("Creating GRPC Client")
    grpc_client = createClient()
    while True:
        time.sleep(0.1)
    logger.info("Exiting")
