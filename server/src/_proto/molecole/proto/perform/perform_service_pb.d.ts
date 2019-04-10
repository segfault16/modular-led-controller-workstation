// package: molecole.proto.perform
// file: molecole/proto/perform/perform_service.proto

import * as jspb from "google-protobuf";

export class Performance extends jspb.Message {
  getActiveslot(): number;
  setActiveslot(value: number): void;

  serializeBinary(): Uint8Array;
  toObject(includeInstance?: boolean): Performance.AsObject;
  static toObject(includeInstance: boolean, msg: Performance): Performance.AsObject;
  static extensions: {[key: number]: jspb.ExtensionFieldInfo<jspb.Message>};
  static extensionsBinary: {[key: number]: jspb.ExtensionFieldBinaryInfo<jspb.Message>};
  static serializeBinaryToWriter(message: Performance, writer: jspb.BinaryWriter): void;
  static deserializeBinary(bytes: Uint8Array): Performance;
  static deserializeBinaryFromReader(message: Performance, reader: jspb.BinaryReader): Performance;
}

export namespace Performance {
  export type AsObject = {
    activeslot: number,
  }
}

export class QueryPerformanceRequest extends jspb.Message {
  getProjectUid(): string;
  setProjectUid(value: string): void;

  serializeBinary(): Uint8Array;
  toObject(includeInstance?: boolean): QueryPerformanceRequest.AsObject;
  static toObject(includeInstance: boolean, msg: QueryPerformanceRequest): QueryPerformanceRequest.AsObject;
  static extensions: {[key: number]: jspb.ExtensionFieldInfo<jspb.Message>};
  static extensionsBinary: {[key: number]: jspb.ExtensionFieldBinaryInfo<jspb.Message>};
  static serializeBinaryToWriter(message: QueryPerformanceRequest, writer: jspb.BinaryWriter): void;
  static deserializeBinary(bytes: Uint8Array): QueryPerformanceRequest;
  static deserializeBinaryFromReader(message: QueryPerformanceRequest, reader: jspb.BinaryReader): QueryPerformanceRequest;
}

export namespace QueryPerformanceRequest {
  export type AsObject = {
    projectUid: string,
  }
}

