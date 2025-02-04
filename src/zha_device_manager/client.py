"""API client."""

import logging
import asyncio
import json

import websockets
from websockets.asyncio.client import connect, ClientConnection

from collections.abc import AsyncGenerator
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Final, Iterator

from .types import DeviceInfo

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
LOG.addHandler(logging.StreamHandler())

#websock_log = logging.getLogger("websockets")
#websock_log.setLevel(logging.DEBUG)
#websock_log.addHandler(logging.StreamHandler())


class DeviceManager:
    """ZHA Device manager."""

    def __init__(self, api_key: str, connection: ClientConnection) -> None:
        """Initialize device manager."""
        self.api_key: Final = api_key
        self.connection: Final = connection
        self.used_ids: set[int] = set()
        self._current_id: int = 0

    def _resp_auth_required(self) -> str:
        """Respond to auth required message."""
        return json.dumps({"type": "auth", "access_token": self.api_key})

    @contextmanager
    def get_id(self) -> Iterator[int]:
        """Get ID."""
        id: int | None = None
        if not self.used_ids:
            id = 1
        else:
            for i in range(len(self.used_ids)):
                if (i + 1) not in self.used_ids:
                    id = i + 1
                    break
                for i in range(1, 65000):
                    if i not in self.used_ids:
                        id = i
                        break

        if not id:
            raise RuntimeError("Unable to resolve a client ID.")
        self.used_ids.add(id)

        try:
            yield id
        finally:
            self.used_ids.remove(id)

    async def send_message(
        self, request_type: str, response_type: str, use_id: bool = True, **kwargs: Any
    ) -> str:
        """Handle message sending."""
        with self.get_id() as request_id:
            body = {"type": request_type, **kwargs}
            if use_id:
                body["id"] = request_id
            payload = json.dumps(body)
            LOG.debug("Sending message: %s", payload)

            await self.connection.send(payload)
            response = await self.connection.recv()

        message = str(response)
        LOG.debug("Got response: %r", response)
        message_type = self._get_type(message)

        if message_type == response_type:
            return message

        raise RuntimeError("Unexpected response.")

    def _get_type(self, message: str) -> str:
        """Get the message type."""
        response = json.loads(message)
        return response["type"]

    def handle_response(self, message: str, expected_type: str) -> str | None:
        """Handle the response to a message, return JSON string."""
        response = json.loads(message)
        api_type: str | None = response.get("type")
        if api_type is None:
            raise ValueError("No API type received.")

        if api_type == "auth_required":
            return self._resp_auth_required()

        if api_type == "auth_ok":
            return None

        if api_type == "auth_invalid":
            raise RuntimeError("Authentication invalid.")

        if expected_type and api_type == expected_type:
            return message

    async def login(self) -> None:
        """Login to api."""
        response = await self.send_message(
            "auth", "auth_ok", use_id=False, access_token=self.api_key
        )
        LOG.info("Logged in. Response: %s", response)

    async def get_devices(self) -> list[DeviceInfo]:
        """Get Devices."""
        message_type = "zha/devices"
        device_response = await self.send_message(message_type, "result")
        result = json.loads(device_response)
        status: bool = result.get("result", False)
        if not status:
            raise RuntimeError("Unable to get devices")
        devices = result.get("result", [])
        device_info: list[DeviceInfo] = []
        for device in devices:
            device_info.append(DeviceInfo.model_validate(device))

        return device_info

    async def dump_devices(self) -> list[dict[str, Any]]:
        """Dump Devices, trying to keep the output readable."""
        message_type = "zha/devices"
        device_response = await self.send_message(message_type, "result")
        result = json.loads(device_response)
        status: bool = result.get("result", False)
        if not status:
            raise RuntimeError("Unable to get devices")
        devices = result.get("result", [])
        return devices

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, hostname: str, port: str, api_key: str
    ) -> "AsyncGenerator[DeviceManager, None]":
        """Connect and yield the device manager."""
        url = f"ws://{hostname}:{port}/api/websocket"
        async with connect(url) as websocket:
            device_manager = cls(api_key, websocket)
            initial_message = await websocket.recv()
            message_type = device_manager._get_type(str(initial_message))
            if message_type != "auth_required":
                raise RuntimeError(f"Unexpected message received: {initial_message}")
            await device_manager.login()
            yield device_manager
