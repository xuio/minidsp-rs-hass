from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

import aiohttp

_LOGGER = logging.getLogger(__name__)


class MiniDSPAPI:
    """Simple async wrapper around the minidsp-rs HTTP & WebSocket API."""

    def __init__(
        self, base_url: str, session: aiohttp.ClientSession, device_index: int = 0
    ):
        # Normalise base url (strip trailing slash)
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._device_index = device_index
        self._ws_task: asyncio.Task | None = None
        self._listeners: list[
            Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
        ] = []
        self._stop_event = asyncio.Event()

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    async def async_get_status(self) -> dict[str, Any]:
        """Return the status summary for the device."""
        url = f"{self._base_url}/devices/{self._device_index}"
        async with self._session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def async_post_config(self, payload: dict[str, Any]) -> None:
        """POST configuration changes to the device."""
        url = f"{self._base_url}/devices/{self._device_index}/config"
        async with self._session.post(url, json=payload) as resp:
            resp.raise_for_status()

    # ----------------------- convenience setters ------------------------

    async def async_set_volume(self, gain: float) -> None:
        await self.async_post_config({"master_status": {"volume": gain}})

    async def async_set_mute(self, mute: bool) -> None:
        await self.async_post_config({"master_status": {"mute": mute}})

    async def async_set_dirac(self, enabled: bool) -> None:
        await self.async_post_config({"master_status": {"dirac": enabled}})

    async def async_set_source(self, source: str) -> None:
        await self.async_post_config({"master_status": {"source": source}})

    async def async_set_preset(self, preset: int) -> None:
        await self.async_post_config({"master_status": {"preset": preset}})

    async def async_set_output_gain(self, output_index: int, gain: float) -> None:
        await self.async_post_config(
            {"outputs": [{"index": output_index, "gain": gain}]}
        )

    # ----------------------- websocket handling -------------------------

    async def async_subscribe_levels(
        self, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> Callable[[], None]:
        """Subscribe to live level updates.

        The callback will receive a dict containing at least `input_levels` and
        `output_levels` whenever a new message is received.
        Returns an unsubscribe callback.
        """
        self._listeners.append(callback)

        if self._ws_task is None:
            self._ws_task = asyncio.create_task(self._ws_listener_task())

        def _unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)
            if not self._listeners:
                self._stop_event.set()

        return _unsubscribe

    async def async_disconnect(self) -> None:
        """Cancel the websocket task (if any)."""
        if self._ws_task and not self._ws_task.done():
            self._stop_event.set()
            await self._ws_task

    # ---------------------------------------------------------------------

    async def _ws_listener_task(self) -> None:
        """Background task that maintains the websocket connection."""
        ws_url = self._build_ws_url()
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                _LOGGER.debug("Connecting to MiniDSP websocket at %s", ws_url)
                async with self._session.ws_connect(ws_url, heartbeat=30) as ws:
                    backoff = 1.0  # Reset backoff after successful connect
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                            except json.JSONDecodeError as err:
                                _LOGGER.warning(
                                    "Failed to decode websocket message: %s", err
                                )
                                continue
                            _LOGGER.debug("Websocket message: %s", data)
                            await self._dispatch_event(data)
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            _LOGGER.debug("Websocket closed")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.debug("Websocket error: %s", ws.exception())
                            break
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Websocket connection failed: %s", err)

            if self._stop_event.is_set():
                break

            # Reconnect with exponential backoff
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 60.0)

        _LOGGER.debug("MiniDSP websocket listener stopped")

    async def _dispatch_event(self, event: dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                await cb(event)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Listener raised: %s", err)

    # ---------------------------------------------------------------------

    def _build_ws_url(self) -> str:
        """Convert the base_url to a websocket URL for streaming levels."""
        # Convert http(s) to ws(s)
        if self._base_url.startswith("https://"):
            scheme = "wss://"
            rest = self._base_url[len("https://") :]
        elif self._base_url.startswith("http://"):
            scheme = "ws://"
            rest = self._base_url[len("http://") :]
        elif self._base_url.startswith("tcp://"):
            # minidsp-rs sometimes advertises tcp scheme; treat as ws
            scheme = "ws://"
            rest = self._base_url[len("tcp://") :]
        else:
            # Assume scheme already correct (ws:// or wss:// or tcp:// etc.)
            scheme = ""
            rest = self._base_url

        return f"{scheme}{rest}/devices/{self._device_index}?levels=true"
