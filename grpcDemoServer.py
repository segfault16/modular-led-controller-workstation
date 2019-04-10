from concurrent import futures
import time
import math
import logging

import grpc
import molecole.proto.perform.perform_service_pb2 as perform_service

import molecole.proto.perform.perform_service_pb2_grpc as perform_service_grpc

_ONE_DAY_IN_SECONDS = 60 * 60 * 24
logging.basicConfig()
_LOGGER = logging.getLogger(__name__)

class PerformanceServicer(perform_service_grpc.PerformanceServiceServicer):
    def QueryPerformance(self, request, context):
        print("Listing Performances")
        while True:
            time.sleep(1)
            perf = perform_service.Performance(activeSlot=1)
            print("Another performance")
            yield perf

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    perform_service_grpc.add_PerformanceServiceServicer_to_server(PerformanceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started")
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()