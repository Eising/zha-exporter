"""Base dataclasses and types.

I could import most of ZHA and re-use the types here, or simplify down to a set
of simpler dataclasses. I'm using the latter approach for now.
"""

from pydantic import BaseModel, Field
from typing import Any


class EndpointNames(BaseModel):
    """Endpoint names."""

    name: str


class Entity(BaseModel):

    entity_id: str
    name: str


class Neighbor(BaseModel):
    """Neighbor."""

    device_type: str
    rx_on_when_idle: str
    relationship: str
    extended_pan_id: str
    ieee: str
    nwk: str
    permit_joining: str
    depth: str
    lqi: str



class Route(BaseModel):
    """Route."""

    dest_nwk: str
    route_status: str
    memory_constrained: bool
    many_to_one: bool
    route_record_required: bool
    next_hop: str



class DeviceInfo(BaseModel):
    """ZHA device info."""

    ieee: str  # Originally a binary type
    nwk:  str | int  # Originally bytes as hex
    manufacturer: str
    model: str
    name: str
    quirk_applied: bool
    quirk_class: str
    quirk_id: str | None
    manufacturer_code: int | None
    power_source: str
    lqi: int
    rssi: int
    last_seen: str
    available: bool
    device_type: str
    area_id: str | None
    active_coordinator: bool
    device_reg_id: str | None
    user_given_name: str | None
    neighbors: list[Neighbor] = Field(default_factory=list)
    routes: list[Route] = Field(default_factory=list)

    endpoint_names: list[EndpointNames] | None = None
    signature: dict[str, Any] = Field(default_factory=dict)


class ExporterConfig(BaseModel):
    """Model for the config file."""

    hostname: str
    port: int
    token: str
