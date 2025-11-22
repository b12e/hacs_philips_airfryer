"""Sensor platform for Philips Airfryer."""
from datetime import datetime
import logging
from typing import Any

import dateutil.parser

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_REPLACE_TIMESTAMP,
    DOMAIN,
    SENSOR_DIALOG,
    SENSOR_DISP_TIME,
    SENSOR_PROGRESS,
    SENSOR_STATUS,
    SENSOR_TEMP,
    SENSOR_TIMESTAMP,
    SENSOR_TOTAL_TIME,
    SENSOR_AIRSPEED,
    SENSOR_TEMP_PROBE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Philips Airfryer sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    airspeed = hass.data[DOMAIN][config_entry.entry_id]["airspeed"]
    probe = hass.data[DOMAIN][config_entry.entry_id]["probe"]
    mac_address = hass.data[DOMAIN][config_entry.entry_id].get("mac_address")

    entities = [
        AirfryerStatusSensor(coordinator, config_entry, mac_address),
        AirfryerTemperatureSensor(coordinator, config_entry, mac_address),
        AirfryerTimestampSensor(coordinator, config_entry, mac_address),
        AirfryerTotalTimeSensor(coordinator, config_entry, mac_address),
        AirfryerDisplayTimeSensor(coordinator, config_entry, mac_address),
        AirfryerProgressSensor(coordinator, config_entry, mac_address),
        AirfryerDialogSensor(coordinator, config_entry, mac_address),
    ]

    if airspeed:
        entities.append(AirfryerAirspeedSensor(coordinator, config_entry, mac_address))

    if probe:
        entities.append(AirfryerTempProbeSensor(coordinator, config_entry, mac_address))

    async_add_entities(entities)


class AirfryerSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Philips Airfryer sensors."""

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._mac_address = mac_address
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "Philips Airfryer",
            "manufacturer": "Philips",
            "model": "Connected Airfryer",
        }

        # Add MAC address as a connection if available
        if self._mac_address:
            device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac_address)}

        return device_info


class AirfryerStatusSensor(AirfryerSensorBase):
    """Status sensor for Philips Airfryer."""

    _attr_name = "Status"
    _attr_icon = "mdi:state-machine"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_STATUS}"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self.coordinator.data is None:
            return "offline"
        return self.coordinator.data.get(SENSOR_STATUS, "unknown")


class AirfryerTemperatureSensor(AirfryerSensorBase):
    """Temperature sensor for Philips Airfryer."""

    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_TEMP}"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.get(SENSOR_TEMP, 0)


class AirfryerTimestampSensor(AirfryerSensorBase):
    """Timestamp sensor for Philips Airfryer."""

    _attr_name = "Timestamp"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_TIMESTAMP}"

    @property
    def native_value(self) -> datetime | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None

        time_remaining_key = self.coordinator.time_remaining
        time_remaining = self.coordinator.data.get(time_remaining_key, 0)
        status = self.coordinator.data.get(SENSOR_STATUS)

        if time_remaining == 0 or status in ("standby", "powersave"):
            return None

        replace_timestamp = self.coordinator.replace_timestamp
        if replace_timestamp:
            return datetime.now()
        else:
            timestamp_str = self.coordinator.data.get(SENSOR_TIMESTAMP)
            if timestamp_str:
                try:
                    return dateutil.parser.parse(timestamp_str, ignoretz=True)
                except (ValueError, TypeError):
                    return None
        return None


class AirfryerTotalTimeSensor(AirfryerSensorBase):
    """Total time sensor for Philips Airfryer."""

    _attr_name = "Total Time"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_TOTAL_TIME}"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None

        time_total_key = self.coordinator.time_total
        time_remaining_key = self.coordinator.time_remaining
        time_remaining = self.coordinator.data.get(time_remaining_key, 0)
        status = self.coordinator.data.get(SENSOR_STATUS)

        if time_remaining == 0 or status in ("standby", "powersave"):
            return None

        return self.coordinator.data.get(time_total_key)


class AirfryerDisplayTimeSensor(AirfryerSensorBase):
    """Display time (remaining) sensor for Philips Airfryer."""

    _attr_name = "Time Remaining"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_DISP_TIME}"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return None

        time_remaining_key = self.coordinator.time_remaining
        time_remaining = self.coordinator.data.get(time_remaining_key, 0)
        status = self.coordinator.data.get(SENSOR_STATUS)

        if time_remaining == 0 or status in ("standby", "powersave"):
            return None

        return time_remaining


class AirfryerProgressSensor(AirfryerSensorBase):
    """Progress sensor for Philips Airfryer."""

    _attr_name = "Progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:progress-clock"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_PROGRESS}"

    @property
    def native_value(self) -> float | None:
        """Return the state."""
        if self.coordinator.data is None:
            return 0

        time_total_key = self.coordinator.time_total
        time_remaining_key = self.coordinator.time_remaining

        time_remaining = self.coordinator.data.get(time_remaining_key, 0)
        time_total = self.coordinator.data.get(time_total_key, 0)
        status = self.coordinator.data.get(SENSOR_STATUS)

        if time_remaining == 0 or status in ("standby", "powersave") or time_total == 0:
            return 0

        progress = (time_total - time_remaining) / time_total * 100
        return round(progress, 1)


class AirfryerDialogSensor(AirfryerSensorBase):
    """Dialog sensor for Philips Airfryer."""

    _attr_name = "Dialog"
    _attr_icon = "mdi:message-alert"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_DIALOG}"

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self.coordinator.data is None:
            return "none"
        return self.coordinator.data.get(SENSOR_DIALOG, "none")


class AirfryerAirspeedSensor(AirfryerSensorBase):
    """Airspeed sensor for Philips Airfryer."""

    _attr_name = "Airspeed"
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_AIRSPEED}"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.get(SENSOR_AIRSPEED, 0)


class AirfryerTempProbeSensor(AirfryerSensorBase):
    """Temperature probe sensor for Philips Airfryer."""

    _attr_name = "Temperature Probe"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-probe"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_TEMP_PROBE}"

    @property
    def native_value(self) -> int | None:
        """Return the state."""
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.get(SENSOR_TEMP_PROBE, 0)
