"""Binary sensor platform for Philips Airfryer."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_DRAWER_OPEN, SENSOR_PROBE_UNPLUGGED

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Philips Airfryer binary sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    probe = hass.data[DOMAIN][config_entry.entry_id]["probe"]
    mac_address = hass.data[DOMAIN][config_entry.entry_id].get("mac_address")

    entities = [
        AirfryerDrawerOpenBinarySensor(coordinator, config_entry, mac_address),
    ]

    if probe:
        entities.append(AirfryerProbeUnpluggedBinarySensor(coordinator, config_entry, mac_address))

    async_add_entities(entities)


class AirfryerBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Philips Airfryer binary sensors."""

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the binary sensor."""
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
            _LOGGER.debug("Adding MAC address connection: %s", self._mac_address)
            device_info["connections"] = {(dr.CONNECTION_NETWORK_MAC, self._mac_address)}
        else:
            _LOGGER.debug("No MAC address available for device connection")

        return device_info


class AirfryerDrawerOpenBinarySensor(AirfryerBinarySensorBase):
    """Drawer open binary sensor for Philips Airfryer."""

    _attr_name = "Drawer Open"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:tray"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_DRAWER_OPEN}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the drawer is open."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get(SENSOR_DRAWER_OPEN, False)


class AirfryerProbeUnpluggedBinarySensor(AirfryerBinarySensorBase):
    """Probe unplugged binary sensor for Philips Airfryer."""

    _attr_name = "Probe"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:connection"

    def __init__(self, coordinator, config_entry: ConfigEntry, mac_address: str | None = None) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry, mac_address)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_PROBE_UNPLUGGED}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the probe is plugged in."""
        if self.coordinator.data is None:
            return False  # When no data, assume unplugged (off)
        # Invert the unplugged state: if probe_unplugged is True, return False (not plugged in)
        return not self.coordinator.data.get(SENSOR_PROBE_UNPLUGGED, True)
