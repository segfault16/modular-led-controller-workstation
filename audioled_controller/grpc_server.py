import audioled_controller.grpc_midi_pb2, audioled_controller.grpc_midi_pb2_grpc
import grpc
import mido
from concurrent import futures


class MidiServicer(audioled_controller.grpc_midi_pb2_grpc.MidiServicer):
    def __init__(self):
        self._prev_msgs = []
        self._midiCallback = None

    def MidiChat(self, request_iterator, context):
        for new_msg in request_iterator:
            new_msg = new_msg  # type: grpc_midi_pb2.Sysex
            midi_msg = mido.Message.from_bytes(new_msg.data)
            if self._midiCallback is not None:
                self._midiCallback(midi_msg)
        for prev_msg in self._prev_msgs:
            yield prev_msg

def create_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    audioled_controller.grpc_midi_pb2_grpc.add_MidiServicer_to_server(
        MidiServicer(), server)
    return server