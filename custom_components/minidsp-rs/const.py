DOMAIN = "minidsp"

# Default update interval for polling device status (fallback when websocket not available)
SCAN_INTERVAL_SECONDS = 15

# Available source options as described in the OpenAPI schema
SOURCES = [
    "Analog",
    "TOSLINK",
    "SPDIF",
    "USB",
    "Bluetooth",
]
