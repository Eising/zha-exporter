"""Metric collection."""

from typing import cast, override

from collections.abc import AsyncGenerator

import click
from aiohttp.web import Application
from prometheus_aioexporter import Arguments, PrometheusExporterScript, MetricConfig
from prometheus_client import (Gauge, Enum)
from prometheus_client.metrics import MetricWrapperBase

from .client import DeviceManager

# Somehow I want to easily convert my Pydantic class into a series of metrics.
# But let's try the naive approach first
# Device metrics
"""
labels: ieee, nwk, power_source
lqi: gauge
rssi: gauge
state: enum(available, unavailable)
device_type: enum(Router, Coordinator, Enddevice)
neighbors: gauge

"""

class ZhaExporter(PrometheusExporterScript):
    """Export Zigbee for Home Assistant device stats."""

    name: str = "zha-exporter"
    default_port: int = 18123
    envvar_prefix: str = "ZHA"

    @override
    def __init__(self) -> None:
        """Initialize class."""
        super().__init__()
        self._hass_hostname: str | None = None
        self._hass_port: str | None = None
        self._hass_token: str | None = None

    @override
    def command_line_parameters(self) -> list[click.Parameter]:
        """Return additional command line options."""
        return [
            click.Option(["--hass-hostname"], help="Hostname for Home-Assistant, e.g. homeassistant.local", default="homeassistant.local"),
            click.Option(["--hass-port"], help="Port for Home-Assistant, e.g., 8123", default="8123"),
            click.Option(["--hass-token"], help="Home-Assistant token for API access.", required=True)
        ]

    @override
    def configure(self, args: Arguments) -> None:
        """Configure the application."""
        labels = ("ieee", "user_given_name")
        self.create_metrics(
            [
                MetricConfig("zha_lqi_info", "Link Quality Indication", "gauge", labels),
                MetricConfig("zha_rssi_db", "Received Signal Strength", "gauge", labels),
                MetricConfig("zha_device_state_info", "Device State", "enum", labels=labels, config={"states": ["available", "unavailable"]}),
                MetricConfig("zha_neighbor_count", "Number of current neighbors", "gauge", labels=labels),
                MetricConfig("zha_route_count", "Number of current routes", "gauge", labels=labels),

            ]
        )
        self._hass_hostname = args.hass_hostname
        self._hass_port = args.hass_port
        self._hass_token = args.hass_token

    @override
    async def on_application_startup(self, application: Application) -> None:
        """Run on application startup."""
        application["exporter"].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics: dict[str, MetricWrapperBase]) -> None:
        """Update metrics."""
        hostname = self._hass_hostname
        assert isinstance(hostname, str)
        port = self._hass_port
        assert isinstance(port, str)
        api_token = self._hass_token
        assert isinstance(api_token, str)
        lqi = cast(Gauge, metrics["zha_lqi_info"])
        rssi = cast(Gauge, metrics["zha_rssi_db"])
        device_state = cast(Enum, metrics["zha_device_state_info"])
        neighbor_count = cast(Gauge, metrics["zha_neighbor_count"])
        route_count = cast(Gauge, metrics["zha_route_count"])

        async with DeviceManager.connect(hostname, port, api_token) as device_manager:
            devices = await device_manager.get_devices()
            for device in devices:
                lqi.labels(ieee=device.ieee, user_given_name=device.user_given_name).set(device.lqi)
                rssi.labels(ieee=device.ieee, user_given_name=device.user_given_name).set(device.rssi)
                device_state_val = "available" if device.available else "unavailable"
                device_state.labels(ieee=device.ieee, user_given_name=device.user_given_name).state(device_state_val)
                neighbor_count.labels(ieee=device.ieee, user_given_name=device.user_given_name).set(len(device.neighbors))
                route_count.labels(ieee=device.ieee, user_given_name=device.user_given_name).set(len(device.routes))

script = ZhaExporter()
