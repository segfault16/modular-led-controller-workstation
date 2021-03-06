# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from . import grpc_midi_pb2 as grpc__midi__pb2


class MidiStub(object):
    """Missing associated documentation comment in .proto file"""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.MidiChat = channel.stream_stream(
                '/Midi/MidiChat',
                request_serializer=grpc__midi__pb2.Empty.SerializeToString,
                response_deserializer=grpc__midi__pb2.Sysex.FromString,
                )
        self.SendMidi = channel.unary_unary(
                '/Midi/SendMidi',
                request_serializer=grpc__midi__pb2.Sysex.SerializeToString,
                response_deserializer=grpc__midi__pb2.Empty.FromString,
                )


class MidiServicer(object):
    """Missing associated documentation comment in .proto file"""

    def MidiChat(self, request_iterator, context):
        """Missing associated documentation comment in .proto file"""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SendMidi(self, request, context):
        """Missing associated documentation comment in .proto file"""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MidiServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'MidiChat': grpc.stream_stream_rpc_method_handler(
                    servicer.MidiChat,
                    request_deserializer=grpc__midi__pb2.Empty.FromString,
                    response_serializer=grpc__midi__pb2.Sysex.SerializeToString,
            ),
            'SendMidi': grpc.unary_unary_rpc_method_handler(
                    servicer.SendMidi,
                    request_deserializer=grpc__midi__pb2.Sysex.FromString,
                    response_serializer=grpc__midi__pb2.Empty.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Midi', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Midi(object):
    """Missing associated documentation comment in .proto file"""

    @staticmethod
    def MidiChat(request_iterator,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.stream_stream(request_iterator, target, '/Midi/MidiChat',
            grpc__midi__pb2.Empty.SerializeToString,
            grpc__midi__pb2.Sysex.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SendMidi(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Midi/SendMidi',
            grpc__midi__pb2.Sysex.SerializeToString,
            grpc__midi__pb2.Empty.FromString,
            options, channel_credentials,
            call_credentials, compression, wait_for_ready, timeout, metadata)
