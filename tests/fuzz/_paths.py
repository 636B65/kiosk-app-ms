"""Make the repository's packages importable when a fuzzer runs from source."""

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _sub in (
    "libs/kiosk_common",
    "services/auth-service",
    "services/catalog-service",
    "services/customer-service",
    "services/order-service",
    "services/report-service",
):
    _path = os.path.join(_ROOT, _sub)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
