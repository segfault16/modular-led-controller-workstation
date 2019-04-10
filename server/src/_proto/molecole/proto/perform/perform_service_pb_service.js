// package: molecole.proto.perform
// file: molecole/proto/perform/perform_service.proto

var molecole_proto_perform_perform_service_pb = require("../../../molecole/proto/perform/perform_service_pb");
var grpc = require("@improbable-eng/grpc-web").grpc;

var PerformanceService = (function () {
  function PerformanceService() {}
  PerformanceService.serviceName = "molecole.proto.perform.PerformanceService";
  return PerformanceService;
}());

PerformanceService.QueryPerformance = {
  methodName: "QueryPerformance",
  service: PerformanceService,
  requestStream: false,
  responseStream: true,
  requestType: molecole_proto_perform_perform_service_pb.QueryPerformanceRequest,
  responseType: molecole_proto_perform_perform_service_pb.Performance
};

exports.PerformanceService = PerformanceService;

function PerformanceServiceClient(serviceHost, options) {
  this.serviceHost = serviceHost;
  this.options = options || {};
}

PerformanceServiceClient.prototype.queryPerformance = function queryPerformance(requestMessage, metadata) {
  var listeners = {
    data: [],
    end: [],
    status: []
  };
  var client = grpc.invoke(PerformanceService.QueryPerformance, {
    request: requestMessage,
    host: this.serviceHost,
    metadata: metadata,
    transport: this.options.transport,
    debug: this.options.debug,
    onMessage: function (responseMessage) {
      listeners.data.forEach(function (handler) {
        handler(responseMessage);
      });
    },
    onEnd: function (status, statusMessage, trailers) {
      listeners.end.forEach(function (handler) {
        handler();
      });
      listeners.status.forEach(function (handler) {
        handler({ code: status, details: statusMessage, metadata: trailers });
      });
      listeners = null;
    }
  });
  return {
    on: function (type, handler) {
      listeners[type].push(handler);
      return this;
    },
    cancel: function () {
      listeners = null;
      client.close();
    }
  };
};

exports.PerformanceServiceClient = PerformanceServiceClient;

