from __future__ import print_function

import random
import logging

import grpc
import molecole.proto.perform.perform_service_pb2 as perform_service

import molecole.proto.perform.perform_service_pb2_grpc as perform_service_grpc

def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = perform_service_grpc.PerformanceServiceStub(channel)
        req = perform_service.QueryPerformanceRequest(project_uid="test")
        features = stub.QueryPerformance(req)

        for feature in features:
            print("Feature")

if __name__ == '__main__':
    logging.basicConfig()
    run()