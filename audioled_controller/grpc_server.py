import audioled_controller.grpc_midi_pb2
import audioled_controller.grpc_midi_pb2_grpc
import grpc
import mido
import logging
import queue
from concurrent import futures
logger = logging.getLogger(__name__)

class MidiServicer(audioled_controller.grpc_midi_pb2_grpc.MidiServicer):
    def __init__(self, callback=None):
        self._queue = queue.SimpleQueue()
        self._midiCallback = callback

    def MidiChat(self, request_iterator, context):
        for new_msg in request_iterator:
            logger.info("Started Midi Backchannel {}".format(new_msg))
            for prev_msg in iter(self._queue.get, None):
                yield prev_msg

    def SendMidi(self, request, context):
        logger.info("Received {}".format(request))
        midi_msg = mido.Message.from_bytes(request.data)
        if self._midiCallback is not None:
            self._midiCallback(midi_msg)
        return audioled_controller.grpc_midi_pb2.Empty()

    def send(self, msg: mido.Message):
        logger.info("Appending {}".format(msg))
        grpc_msg = audioled_controller.grpc_midi_pb2.Sysex()
        grpc_msg.data = bytes(msg.bytes())
        self._queue.put(grpc_msg)

def create_server(callback=None):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service = MidiServicer(callback)
    audioled_controller.grpc_midi_pb2_grpc.add_MidiServicer_to_server(
        service, server)
    
    return server, service