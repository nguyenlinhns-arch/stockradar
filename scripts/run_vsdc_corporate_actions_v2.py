#!/usr/bin/env python3
from __future__ import annotations

import acquire_vsdc_corporate_actions as collector

# VSDC's current official host is vsdc.vn. Keep normal TLS verification enabled;
# do not work around hostname errors by disabling certificate verification.
# The collector now mirrors the browser AJAX contract: same session + meta __VPToken header.
collector.BASE = "https://vsdc.vn/vi/lich-giao-dich"

if __name__ == "__main__":
    collector.main()
