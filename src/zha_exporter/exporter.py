"""Metric collection."""

from typing import cast, override

import tomllib
import click
from aiohttp.web import Application
from prometheus_aioexporter import Arguments, PrometheusExporterScript, MetricConfig
from prometheus_client import Gauge, Enum
from prometheus_client.metrics import MetricWrapperBase
from .types import ExporterConfig

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
        self._exporter_config: ExporterConfig | None = None

    @override
    def command_line_parameters(self) -> list[click.Parameter]:
        """Return additional command line options."""
        return [
            click.Option(
                ["--config-file", "-c"],
                required=True,
                help="Path to TOML configuration file",
                type=click.Path(exists=True, dir_okay=False),
            )
        ]

    @override
    def configure(self, args: Arguments) -> None:
        """Configure the application."""
        labels = ("ieee", "area_id", "device_type")
        self.create_metrics(
            [
                MetricConfig(
                    "zha_link_quality", "Link Quality Indication", "gauge", labels
                ),
                MetricConfig(
                    "zha_rssi_dbm", "Received Signal Strength", "gauge", labels
                ),
                MetricConfig(
                    "zha_device_status",
                    "Device State",
                    "gauge",
                    labels=labels,
                ),
                MetricConfig(
                    "zha_neighbor_count",
                    "Number of current neighbors",
                    "gauge",
                    labels=labels,
                ),
                MetricConfig(
                    "zha_route_count",
                    "Number of current routes",
                    "gauge",
                    labels=labels,
                ),
            ]
        )
        config_file = args.config_file
        self.read_config(config_file)

    def read_config(self, path: str) -> None:
        """Read config."""
        with open(path, "rb") as f:
            config_dict = tomllib.load(f)

        assert "zha-exporter" in config_dict

        self._exporter_config = ExporterConfig.model_validate(
            config_dict["zha-exporter"]
        )

    @override
    async def on_application_startup(self, application: Application) -> None:
        """Run on application startup."""
        application["exporter"].set_metric_update_handler(self._update_handler)

    async def _update_handler(self, metrics: dict[str, MetricWrapperBase]) -> None:
        """Update metrics."""
        config = self._exporter_config
        assert config is not None, "Error: No configuration loaded!"
        hostname = config.hostname
        assert isinstance(hostname, str)
        port = config.port
        assert isinstance(port, (str, int))
        api_token = config.token
        assert isinstance(api_token, str)
        lqi = cast(Gauge, metrics["zha_link_quality"])
        rssi = cast(Gauge, metrics["zha_rssi_dbm"])
        device_state = cast(Gauge, metrics["zha_device_status"])
        neighbor_count = cast(Gauge, metrics["zha_neighbor_count"])
        route_count = cast(Gauge, metrics["zha_route_count"])

        async with DeviceManager.connect(
            hostname, str(port), api_token
        ) as device_manager:
            devices = await device_manager.get_devices()
            # ("ieee", "user_given_name", "nwk", "area_id", "device_type")
            for device in devices:
                lqi.labels(
                    ieee=device.ieee,
                    area_id=device.area_id,
                    device_type=device.device_type,
                ).set(device.lqi or 0)
                rssi.labels(
                    ieee=device.ieee,
                    area_id=device.area_id,
                    device_type=device.device_type,
                ).set(device.rssi or -100)
                device_state_val = 1 if device.available else 0
                device_state.labels(
                    ieee=device.ieee,
                    area_id=device.area_id,
                    device_type=device.device_type,
                ).set(device_state_val)
                neighbor_count.labels(
                    ieee=device.ieee,
                    area_id=device.area_id,
                    device_type=device.device_type,
                ).set(len(device.neighbors))
                route_count.labels(
                    ieee=device.ieee,
                    area_id=device.area_id,
                    device_type=device.device_type,
                ).set(len(device.routes))


script = ZhaExporter()
