#!/usr/bin/env python3
from __future__ import annotations

import acquire_vsdc_corporate_actions as collector

# The canonical VSDC host presents the working TLS certificate. Do not disable
# certificate verification to make the legacy www hostname pass.
collector.BASE = "https://vsd.vn/vi/lich-giao-dich"

if __name__ == "__main__":
    collector.main()
