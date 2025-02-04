"""Command line."""

import asyncio

import json
from typing import Any

import click

import tomllib

from .client import DeviceManager
from .types import DeviceInfo, ZDMConfig

@click.group()
@click.argument("config", type=click.Path())
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """Interact with ZHA."""
    with open(config, "rb") as f:
        cli_config = tomllib.load(f)
    ctx.ensure_object(dict)

    hass_config = cli_config.get("homeassistant")
    if hass_config is None:
        raise RuntimeError("Error: Missing homeassistant section in config.")

    zdm_config = ZDMConfig.model_validate(hass_config)

    ctx.obj["config"] = zdm_config

@cli.command("get-devices")
@click.pass_context
def get_devices(ctx: click.Context) -> None:
    """Get devices."""
    config: ZDMConfig = ctx.obj["config"]

    devices = asyncio.run(command_get_devices(config.hostname, str(config.port), config.token))
    for device in devices:
        click.echo(device.as_cisco())

# @cli.command("dump-devices")
# @click.pass_context
# def dump_devices(ctx: click.Context) -> None:
#     """Dump devices."""
#     hostname = ctx.obj["hostname"]
#     port = ctx.obj["port"]
#     api_key = ctx.obj["api_key"]
#     devices = asyncio.run(command_dump_devices(hostname, port, api_key))
#     click.echo(json.dumps(devices, indent=2))




async def command_get_devices(hostname: str, port: str, api_key: str) -> list[DeviceInfo]:
    """Get devices."""
    async with DeviceManager.connect(hostname, port, api_key) as device_manager:
        devices = await device_manager.get_devices()

    return devices

async def command_dump_devices(hostname: str, port: str, api_key: str) -> list[dict[str, Any]]:
    """Get devices."""
    async with DeviceManager.connect(hostname, port, api_key) as device_manager:
        devices = await device_manager.dump_devices()

    return devices
