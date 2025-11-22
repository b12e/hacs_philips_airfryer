"""Binary sensor platform for Philips Airfryer."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

    entities = [
        AirfryerDrawerOpenBinarySensor(coordinator, config_entry),
    ]

    if probe:
        entities.append(AirfryerProbeUnpluggedBinarySensor(coordinator, config_entry))

    async_add_entities(entities)


class AirfryerBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for Philips Airfryer binary sensors."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "Philips Airfryer",
            "manufacturer": "Philips",
            "model": "Connected Airfryer",
        }


class AirfryerDrawerOpenBinarySensor(AirfryerBinarySensorBase):
    """Drawer open binary sensor for Philips Airfryer."""

    _attr_name = "Drawer Open"
    _attr_device_class = BinarySensorDeviceClass.OPENING
    _attr_icon = "mdi:tray"

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_DRAWER_OPEN}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the drawer is open."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.get(SENSOR_DRAWER_OPEN, False)


class AirfryerProbeUnpluggedBinarySensor(AirfryerBinarySensorBase):
    """Probe unplugged binary sensor for Philips Airfryer."""

    _attr_name = "Probe Unplugged"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:connection"

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_PROBE_UNPLUGGED}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the probe is unplugged."""
        if self.coordinator.data is None:
            return True
        return self.coordinator.data.get(SENSOR_PROBE_UNPLUGGED, True)
