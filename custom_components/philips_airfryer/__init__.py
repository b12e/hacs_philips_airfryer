"""The Philips Airfryer integration."""
import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .airfryer_api import AirfryerAPI
from .const import (
    CONF_AIRSPEED,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_COMMAND_URL,
    CONF_MAC_ADDRESS,
    CONF_PROBE,
    CONF_REPLACE_TIMESTAMP,
    CONF_TIME_REMAINING,
    CONF_TIME_TOTAL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AIRSPEED,
    DEFAULT_COMMAND_URL,
    DEFAULT_PROBE,
    DEFAULT_REPLACE_TIMESTAMP,
    DEFAULT_SLEEP_TIME,
    DEFAULT_TIME_REMAINING,
    DEFAULT_TIME_TOTAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SERVICE_ADJUST_TEMP,
    SERVICE_ADJUST_TIME,
    SERVICE_PAUSE,
    SERVICE_START_COOKING,
    SERVICE_START_RESUME,
    SERVICE_STOP,
    SERVICE_TOGGLE_AIRSPEED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Philips Airfryer from a config entry."""
    ip_address = entry.data[CONF_IP_ADDRESS]
    client_id = entry.data[CONF_CLIENT_ID]
    client_secret = entry.data[CONF_CLIENT_SECRET]

    # Get options with defaults
    command_url = entry.options.get(CONF_COMMAND_URL, DEFAULT_COMMAND_URL)
    airspeed = entry.options.get(CONF_AIRSPEED, DEFAULT_AIRSPEED)
    probe = entry.options.get(CONF_PROBE, DEFAULT_PROBE)
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    replace_timestamp = entry.options.get(CONF_REPLACE_TIMESTAMP, DEFAULT_REPLACE_TIMESTAMP)
    time_remaining = entry.options.get(CONF_TIME_REMAINING, DEFAULT_TIME_REMAINING)
    time_total = entry.options.get(CONF_TIME_TOTAL, DEFAULT_TIME_TOTAL)

    # Create API client
    api = AirfryerAPI(ip_address, client_id, client_secret, command_url)

    # Create coordinator
    coordinator = AirfryerDataUpdateCoordinator(
        hass,
        api,
        update_interval,
        airspeed,
        probe,
        replace_timestamp,
        time_remaining,
        time_total,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Get MAC address if available
    mac_address = entry.data.get(CONF_MAC_ADDRESS)

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
        "airspeed": airspeed,
        "probe": probe,
        "mac_address": mac_address,
        "command_lock": asyncio.Lock(),
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, entry)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AirfryerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Airfryer data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AirfryerAPI,
        update_interval: int,
        airspeed: bool,
        probe: bool,
        replace_timestamp: bool,
        time_remaining: str,
        time_total: str,
    ) -> None:
        """Initialize."""
        self.api = api
        self.airspeed = airspeed
        self.probe = probe
        self.replace_timestamp = replace_timestamp
        self.time_remaining = time_remaining
        self.time_total = time_total

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via API."""
        try:
            data = await self.hass.async_add_executor_job(self.api.get_status)
            if data is None:
                raise UpdateFailed("Failed to fetch data from airfryer")
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for Philips Airfryer."""

    async def handle_turn_on(call: ServiceCall) -> None:
        """Handle turn on service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            command = {
                "probe_required": False,
                "method": 0,
                "status": "precook",
                "temp_unit": False,
            }
            await hass.async_add_executor_job(api.send_command, command)
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await coordinator.async_request_refresh()

    async def handle_turn_off(call: ServiceCall) -> None:
        """Handle turn off service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            status = coordinator.data.get("status")

            if status == "cooking":
                command = {"status": "pause"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

            if status != "mainmenu":
                command = {"status": "mainmenu"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

            command = {"status": "powersave"}
            await hass.async_add_executor_job(api.send_command, command)
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await coordinator.async_request_refresh()

    async def handle_start_cooking(call: ServiceCall) -> None:
        """Handle start cooking service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]
        has_airspeed = hass.data[DOMAIN][entry.entry_id]["airspeed"]

        temp = call.data.get("temp", 180)
        total_time = call.data.get("total_time", 60)
        start_cooking = call.data.get("start_cooking", True)
        force_update = call.data.get("force_update", True)

        async with lock:
            if force_update:
                await coordinator.async_request_refresh()
                await asyncio.sleep(0.1)

            status = coordinator.data.get("status")

            if status != "cooking":
                if status in ("pause", "finish"):
                    command = {"status": "mainmenu"}
                    await hass.async_add_executor_job(api.send_command, command)
                    await asyncio.sleep(DEFAULT_SLEEP_TIME)

                command = {
                    "probe_required": False,
                    "method": 0,
                    "status": "precook",
                    "temp_unit": False,
                }
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                if has_airspeed:
                    airspeed_val = call.data.get("airspeed", 2)
                    command = {
                        "temp": temp,
                        "method": 0,
                        "probe_required": False,
                        "airspeed": airspeed_val,
                        "total_time": total_time,
                        "temp_unit": False,
                    }
                else:
                    command = {
                        "temp": temp,
                        "method": 0,
                        "probe_required": False,
                        "total_time": total_time,
                        "temp_unit": False,
                    }

                await hass.async_add_executor_job(api.send_command, command)

                if start_cooking:
                    await asyncio.sleep(DEFAULT_SLEEP_TIME)
                    command = {"status": "cooking"}
                    await hass.async_add_executor_job(api.send_command, command)

                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

    async def handle_adjust_time(call: ServiceCall) -> None:
        """Handle adjust time service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]
        time_total_key = coordinator.time_total

        time = call.data["time"]
        method = call.data["method"]
        restart_cooking = call.data.get("restart_cooking", True)
        force_update = call.data.get("force_update", True)

        async with lock:
            if force_update:
                await coordinator.async_request_refresh()
                await asyncio.sleep(0.1)

            status = coordinator.data.get("status")
            current_total_time = coordinator.data.get(time_total_key, 0)

            if status == "cooking":
                command = {"status": "pause"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                if method == "add":
                    new_time = int(current_total_time) + time
                else:
                    new_time = max(60, int(current_total_time) - time)

                command = {"total_time": new_time}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                if restart_cooking:
                    command = {"status": "cooking"}
                    await hass.async_add_executor_job(api.send_command, command)
                    await asyncio.sleep(DEFAULT_SLEEP_TIME)

                await coordinator.async_request_refresh()

            elif status in ("pause", "precook"):
                if method == "add":
                    new_time = int(current_total_time) + time
                else:
                    new_time = max(60, int(current_total_time) - time)

                command = {"total_time": new_time}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

    async def handle_adjust_temp(call: ServiceCall) -> None:
        """Handle adjust temperature service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        temp = call.data["temp"]
        method = call.data["method"]
        restart_cooking = call.data.get("restart_cooking", True)
        force_update = call.data.get("force_update", True)

        async with lock:
            if force_update:
                await coordinator.async_request_refresh()
                await asyncio.sleep(0.1)

            status = coordinator.data.get("status")
            current_temp = coordinator.data.get("temp", 0)

            if status == "cooking":
                command = {"status": "pause"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                if method == "add":
                    new_temp = int(current_temp) + temp
                else:
                    new_temp = int(current_temp) - temp

                command = {"temp": new_temp}
                await hass.async_add_executor_job(api.send_command, command)

                if restart_cooking:
                    await asyncio.sleep(DEFAULT_SLEEP_TIME)
                    command = {"status": "cooking"}
                    await hass.async_add_executor_job(api.send_command, command)

                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

            elif status in ("pause", "precook"):
                if method == "add":
                    new_temp = int(current_temp) + temp
                else:
                    new_temp = int(current_temp) - temp

                command = {"temp": new_temp}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

    async def handle_toggle_airspeed(call: ServiceCall) -> None:
        """Handle toggle airspeed service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            await coordinator.async_request_refresh()
            await asyncio.sleep(0.1)

            status = coordinator.data.get("status")
            current_airspeed = coordinator.data.get("airspeed")

            if status == "cooking":
                command = {"status": "pause"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                new_airspeed = 1 if current_airspeed == 2 else 2
                command = {"airspeed": new_airspeed}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

                command = {"status": "cooking"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

            elif status in ("precook", "pause"):
                new_airspeed = 1 if current_airspeed == 2 else 2
                command = {"airspeed": new_airspeed}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)
                await coordinator.async_request_refresh()

    async def handle_pause(call: ServiceCall) -> None:
        """Handle pause service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            command = {"status": "pause"}
            await hass.async_add_executor_job(api.send_command, command)
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await coordinator.async_request_refresh()

    async def handle_start_resume(call: ServiceCall) -> None:
        """Handle start/resume service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            command = {"status": "cooking"}
            await hass.async_add_executor_job(api.send_command, command)
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await coordinator.async_request_refresh()

    async def handle_stop(call: ServiceCall) -> None:
        """Handle stop service."""
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        api: AirfryerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
        lock = hass.data[DOMAIN][entry.entry_id]["command_lock"]

        async with lock:
            await coordinator.async_request_refresh()
            await asyncio.sleep(0.1)

            status = coordinator.data.get("status")

            if status == "cooking":
                command = {"status": "pause"}
                await hass.async_add_executor_job(api.send_command, command)
                await asyncio.sleep(DEFAULT_SLEEP_TIME)

            command = {"status": "mainmenu"}
            await hass.async_add_executor_job(api.send_command, command)
            await asyncio.sleep(DEFAULT_SLEEP_TIME)
            await coordinator.async_request_refresh()

    # Register services
    hass.services.async_register(DOMAIN, SERVICE_TURN_ON, handle_turn_on)
    hass.services.async_register(DOMAIN, SERVICE_TURN_OFF, handle_turn_off)
    hass.services.async_register(DOMAIN, SERVICE_START_COOKING, handle_start_cooking)
    hass.services.async_register(DOMAIN, SERVICE_ADJUST_TIME, handle_adjust_time)
    hass.services.async_register(DOMAIN, SERVICE_ADJUST_TEMP, handle_adjust_temp)
    hass.services.async_register(DOMAIN, SERVICE_PAUSE, handle_pause)
    hass.services.async_register(DOMAIN, SERVICE_START_RESUME, handle_start_resume)
    hass.services.async_register(DOMAIN, SERVICE_STOP, handle_stop)

    if hass.data[DOMAIN][entry.entry_id]["airspeed"]:
        hass.services.async_register(
            DOMAIN, SERVICE_TOGGLE_AIRSPEED, handle_toggle_airspeed
        )
