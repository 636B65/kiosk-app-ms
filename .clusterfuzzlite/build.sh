#!/bin/bash -eu
# Builds the Atheris fuzz targets in tests/fuzz/ (ClusterFuzzLite / OSS-Fuzz).
# The fuzzed modules only need fastapi + pydantic, installed hash-locked.
pip3 install --require-hashes -r "$SRC/kiosk-app-ms/tests/fuzz/requirements.txt"

export PYTHONPATH="$SRC/kiosk-app-ms/libs/kiosk_common:$SRC/kiosk-app-ms/services/catalog-service:$SRC/kiosk-app-ms/services/order-service:$SRC/kiosk-app-ms/services/report-service"
for fuzzer in "$SRC"/kiosk-app-ms/tests/fuzz/fuzz_*.py; do
    compile_python_fuzzer "$fuzzer" --paths "$PYTHONPATH"
done
