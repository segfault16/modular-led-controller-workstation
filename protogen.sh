#!/bin/bash
rm -r ./server/src/_proto || true
mkdir -p ./server/src/_proto
rm -r ./molecole/proto || true
mkdir -p ./molecole/proto

PROTOC=`command -v protoc`
if [[ "$PROTOC" == "" ]]; then
  echo "Required "protoc" to be installed. Please visit https://github.com/protocolbuffers/protobuf/releases (3.5.0 suggested)."
  exit -1
fi

echo "Compiling protobuf"
protoc \
    --plugin=protoc-gen-ts=./server/node_modules/.bin/protoc-gen-ts \
    -I ./proto \
    --js_out=import_style=commonjs,binary:./server/src/_proto \
    --ts_out=service=true:./server/src/_proto \
    ./proto/molecole/proto/perform/perform_service.proto

python -m grpc_tools.protoc -I ./proto \
    --python_out=. \
    --grpc_python_out=. \
    ./proto/molecole/proto/perform/perform_service.proto