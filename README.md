# Homeassistant MiniDSP

needs minidsp rs instance with http server

to configure, enter the address of minidspd's HTTP server with the `ws://` prefix and the port
(5380 unless you changed `bind_address` in minidspd's config), for example `ws://192.168.1.50:5380`

## Options

Settings → Devices & services → MiniDSP → Configure:

| Option | Choices | Default |
|---|---|---|
| minidspd updates | Off · Status (every 2 s) · Levels (every 250 ms) · Status + levels | Status + levels |
| Home Assistant polling | Off · Every 2 s · Every 10 s · Every 60 s | Off |

- **minidspd updates** is what the websocket asks minidspd to stream: *Status* reads volume,
  source, mute and preset every 2 s and sends them when they change; *Levels* reads the input
  and output levels every 250 ms.
- **Home Assistant polling** fetches the status from Home Assistant instead. minidspd has no
  request for just one of them, so every fetch reads the status and the levels. Use one of
  the two settings for each kind of update; turning both on just reads the device twice.
- Changes made with the IR remote or from Home Assistant show up even with both settings off.
  They only matter for changes made by other apps, and for the level sensors, which aren't
  created when nothing updates the levels.

Every read is a USB transaction between minidspd and the miniDSP. If you don't need the level
sensors or other apps' changes, turning both off keeps the USB link quiet.

minidspd doesn't answer websocket pings, so on a quiet connection the integration reconnects
about every 45 s, and each reconnect brings a fresh status and levels reading.
