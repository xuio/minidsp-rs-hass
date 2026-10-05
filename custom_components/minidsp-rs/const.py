DOMAIN = "minidsp"

# Default update interval for polling device status
SCAN_INTERVAL_SECONDS = 1

# Available source options as described in the OpenAPI schema
SOURCES = [
    "Analog",
    "TOSLINK",
    "SPDIF",
    "USB",
    "Bluetooth",
]

# Options controlling how often the miniDSP is read. minidspd reads the device over USB
# for every sample, so fewer updates mean less USB traffic to the miniDSP.

# What the websocket asks minidspd to stream (query parameters `poll` and `levels`)
CONF_SERVER_UPDATES = "server_updates"
SERVER_OFF = "off"
SERVER_STATUS = "status"  # `poll`: master status read every 2 s, sent when it changes
SERVER_LEVELS = "levels"  # `levels`: input/output levels read every 250 ms
SERVER_BOTH = "both"
SERVER_UPDATES = [SERVER_OFF, SERVER_STATUS, SERVER_LEVELS, SERVER_BOTH]

# How often Home Assistant itself fetches the status. That GET reads the master status
# and the levels together; minidspd has no request for just one of them.
CONF_POLL_INTERVAL = "poll_interval"
POLL_OFF = "off"
POLL_INTERVALS = [POLL_OFF, "2", "10", "60"]  # seconds

DEFAULT_SERVER_UPDATES = SERVER_BOTH
DEFAULT_POLL_INTERVAL = POLL_OFF
