// package: molecole.proto.perform
// file: molecole/proto/perform/perform_service.proto

import * as molecole_proto_perform_perform_service_pb from "../../../molecole/proto/perform/perform_service_pb";
import {grpc} from "@improbable-eng/grpc-web";

type PerformanceServiceQueryPerformance = {
  readonly methodName: string;
  readonly service: typeof PerformanceService;
  readonly requestStream: false;
  readonly responseStream: true;
  readonly requestType: typeof molecole_proto_perform_perform_service_pb.QueryPerformanceRequest;
  readonly responseType: typeof molecole_proto_perform_perform_service_pb.Performance;
};

export class PerformanceService {
  static readonly serviceName: string;
  static readonly QueryPerformance: PerformanceServiceQueryPerformance;
}

export type ServiceError = { message: string, code: number; metadata: grpc.Metadata }
export type Status = { details: string, code: number; metadata: grpc.Metadata }

interface UnaryResponse {
  cancel(): void;
}
interface ResponseStream<T> {
  cancel(): void;
  on(type: 'data', handler: (message: T) => void): ResponseStream<T>;
  on(type: 'end', handler: () => void): ResponseStream<T>;
  on(type: 'status', handler: (status: Status) => void): ResponseStream<T>;
}
interface RequestStream<T> {
  write(message: T): RequestStream<T>;
  end(): void;
  cancel(): void;
  on(type: 'end', handler: () => void): RequestStream<T>;
  on(type: 'status', handler: (status: Status) => void): RequestStream<T>;
}
interface BidirectionalStream<ReqT, ResT> {
  write(message: ReqT): BidirectionalStream<ReqT, ResT>;
  end(): void;
  cancel(): void;
  on(type: 'data', handler: (message: ResT) => void): BidirectionalStream<ReqT, ResT>;
  on(type: 'end', handler: () => void): BidirectionalStream<ReqT, ResT>;
  on(type: 'status', handler: (status: Status) => void): BidirectionalStream<ReqT, ResT>;
}

export class PerformanceServiceClient {
  readonly serviceHost: string;

  constructor(serviceHost: string, options?: grpc.RpcOptions);
  queryPerformance(requestMessage: molecole_proto_perform_perform_service_pb.QueryPerformanceRequest, metadata?: grpc.Metadata): ResponseStream<molecole_proto_perform_perform_service_pb.Performance>;
}

