"""Functions on devices."""
from .types import DeviceInfo
import networkx


def device_info_details(device: DeviceInfo) -> dict[str, str]:
    """Create a small info dict for a device."""
    return {
        "user_given_name": device.user_given_name or "",
        "area_id": device.area_id or "None",
        "nwk": str(device.nwk),
        "manufacturer": device.manufacturer,
        "model": device.model,
        "lqi": str(device.lqi),
        "rssi": str(device.rssi),
        "device_type": device.device_type,
    }


class ZigbeeNetwork:
    """Zigbee Network class."""

    def __init__(self, devices: list[DeviceInfo]) -> None:
        """Initialize class."""
        self.nodes: list[tuple[str, str]] = []
        self.edges: list[tuple[str, str, dict[str, int | str]]] = []
        self.devices: list[DeviceInfo] = devices
        self.graph: networkx.Graph[str] = networkx.Graph()
        self.build_graph()

    def build_graph(self) -> None:
        """Analyze devices.."""
        for device in self.devices:
            self.graph.add_node(device.ieee, **device_info_details(device))
            for neighbor in device.neighbors:
                self.graph.add_edge(device.ieee, neighbor.ieee, **neighbor.model_dump())
