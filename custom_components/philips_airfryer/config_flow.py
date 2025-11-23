"""Config flow for Philips Airfryer integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo
import homeassistant.helpers.config_validation as cv

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
    DEFAULT_TIME_REMAINING,
    DEFAULT_TIME_TOTAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .discovery import discover_airfryers, detect_model_config

_LOGGER = logging.getLogger(__name__)

CONF_MODEL = "model"

MODEL_OPTIONS = [
    "HD9880/90",
    "HD9875/90",
    "HD9255",
    "Other (untested)",
]


class PhilipsAirfryerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Philips Airfryer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: list[dict[str, Any]] = []
        self._model_config: dict[str, Any] = {}
        self._ssdp_discovery_info: SsdpServiceInfo | None = None
        self._mac_address: str | None = None
        self._suggested_ip: str | None = None
        self._suggested_model: str | None = None

    async def async_step_ssdp(
        self, discovery_info: SsdpServiceInfo
    ) -> FlowResult:
        """Handle SSDP discovery."""
        _LOGGER.debug("SSDP discovery: %s", discovery_info)

        # Extract IP address from discovery info
        host = discovery_info.ssdp_location or discovery_info.ssdp_headers.get("_host")
        if not host:
            return self.async_abort(reason="no_ip_address")

        # Parse IP from URL if needed
        if "://" in host:
            host = host.split("://")[1].split("/")[0].split(":")[0]

        # Store discovery info
        self._ssdp_discovery_info = discovery_info

        # Try to detect model from SSDP info
        model_name = discovery_info.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, "")
        model_number = discovery_info.upnp.get(ssdp.ATTR_UPNP_MODEL_NUMBER, "")
        friendly_name = discovery_info.upnp.get(ssdp.ATTR_UPNP_FRIENDLY_NAME, "Philips Airfryer")
        device_type = discovery_info.upnp.get(ssdp.ATTR_UPNP_DEVICE_TYPE, "")
        serial_number = discovery_info.upnp.get(ssdp.ATTR_UPNP_SERIAL, "")
        udn = discovery_info.upnp.get(ssdp.ATTR_UPNP_UDN, "")

        # Check if it's a DiProduct (Philips connected appliance/airfryer)
        if "diproduct" not in device_type.lower():
            _LOGGER.debug("Not a DiProduct device, aborting SSDP discovery")
            return self.async_abort(reason="not_airfryer")

        # Extract MAC address from UDN if available
        mac_address = None
        if udn:
            # Try to extract MAC from UDN (format varies by device)
            # Common format: uuid:00000000-0000-1000-8000-XXXXXXXXXXXX where X is MAC
            if "8000-" in udn:
                potential_mac = udn.split("8000-")[-1].replace("-", ":")
                if len(potential_mac) >= 17:  # MAC address length with colons
                    mac_address = potential_mac[:17].upper()
            # Alternative: MAC might be in serial number
            elif serial_number and len(serial_number) >= 12:
                # Try to format as MAC if it looks like one
                cleaned = serial_number.replace(":", "").replace("-", "").upper()
                if len(cleaned) >= 12 and cleaned[:12].isalnum():
                    mac_address = ":".join([cleaned[i:i+2] for i in range(0, 12, 2)])

        self._mac_address = mac_address

        # Detect model configuration
        self._model_config = detect_model_config(model_number)

        # Set unique_id based on MAC address if available, otherwise IP
        unique_id = mac_address if mac_address else host
        _LOGGER.debug("Setting unique_id to %s (MAC: %s, IP: %s)", unique_id, mac_address, host)

        # Check if already configured - update IP if it changed
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: host})

        # Show confirmation form
        self.context["title_placeholders"] = {
            "name": f"{friendly_name} ({host})"
        }

        return await self.async_step_credentials(
            suggested_ip=host,
            suggested_model=self._model_config.get("model", "Unknown")
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - try UPnP discovery."""
        if user_input is not None:
            # User chose to skip discovery or no devices found
            return await self.async_step_manual()

        # Try UPnP discovery
        self._discovered_devices = await self.hass.async_add_executor_job(
            discover_airfryers
        )

        if self._discovered_devices:
            return await self.async_step_discovery()

        # No devices found, go to manual setup
        return await self.async_step_manual()

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device selection from discovered devices."""
        if user_input is not None:
            selected_ip = user_input["device"]

            # Check if user selected manual setup
            if selected_ip == "manual":
                return await self.async_step_manual()

            # Find the selected device
            selected_device = next(
                (d for d in self._discovered_devices if d["ip_address"] == selected_ip),
                None,
            )

            if selected_device:
                # UPnP discovery provides the model, so use it directly
                self._model_config = selected_device["config"]
                self._mac_address = selected_device.get("mac_address")
                return await self.async_step_credentials(
                    suggested_ip=selected_ip,
                    suggested_model=selected_device["suggested_model"],
                )

        # Build device list for selection
        device_options = {
            device["ip_address"]: f"{device.get('friendly_name', 'Unknown')} ({device['ip_address']}) - {device.get('model_number', 'Unknown')}"
            for device in self._discovered_devices
        }
        device_options["manual"] = "Manual setup (enter IP manually)"

        return self.async_show_form(
            step_id="discovery",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(device_options),
                }
            ),
            description_placeholders={
                "count": str(len(self._discovered_devices)),
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual IP and model selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ip_address = user_input[CONF_IP_ADDRESS]
            model = user_input[CONF_MODEL]

            # Set model configuration
            self._model_config = detect_model_config(
                model if model != "Other (untested)" else None
            )

            return await self.async_step_credentials(
                suggested_ip=ip_address, suggested_model=model
            )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_IP_ADDRESS): str,
                    vol.Required(CONF_MODEL, default="Other (untested)"): vol.In(
                        MODEL_OPTIONS
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_credentials(
        self,
        user_input: dict[str, Any] | None = None,
        suggested_ip: str | None = None,
        suggested_model: str | None = None,
    ) -> FlowResult:
        """Handle credentials input."""
        errors: dict[str, str] = {}

        # Store suggested values on first call
        if suggested_ip is not None:
            self._suggested_ip = suggested_ip
        if suggested_model is not None:
            self._suggested_model = suggested_model

        if user_input is not None:
            # Use stored values if available, otherwise try to get from user_input
            ip_address = self._suggested_ip or user_input.get(CONF_IP_ADDRESS)
            client_id = user_input[CONF_CLIENT_ID]
            client_secret = user_input[CONF_CLIENT_SECRET]

            # Test connection
            command_url = self._model_config.get("command_url", DEFAULT_COMMAND_URL)
            api = AirfryerAPI(ip_address, client_id, client_secret, command_url)
            try:
                connection_ok = await self.hass.async_add_executor_job(
                    api.test_connection
                )
                if not connection_ok:
                    errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                # Create entry with unique ID based on MAC address if available, otherwise IP
                unique_id = self._mac_address if self._mac_address else ip_address
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Store basic config in data
                data = {
                    CONF_IP_ADDRESS: ip_address,
                    CONF_CLIENT_ID: client_id,
                    CONF_CLIENT_SECRET: client_secret,
                }

                # Add MAC address if available
                if self._mac_address:
                    data[CONF_MAC_ADDRESS] = self._mac_address

                # Store model-specific config in options
                options = {
                    CONF_COMMAND_URL: self._model_config.get(
                        "command_url", DEFAULT_COMMAND_URL
                    ),
                    CONF_AIRSPEED: self._model_config.get("airspeed", DEFAULT_AIRSPEED),
                    CONF_PROBE: self._model_config.get("probe", DEFAULT_PROBE),
                    CONF_TIME_REMAINING: self._model_config.get(
                        "time_remaining", DEFAULT_TIME_REMAINING
                    ),
                    CONF_TIME_TOTAL: self._model_config.get(
                        "time_total", DEFAULT_TIME_TOTAL
                    ),
                }

                model_name = suggested_model or self._model_config.get(
                    "model", "Unknown"
                )
                title = f"Philips Airfryer {model_name} ({ip_address})"

                return self.async_create_entry(
                    title=title,
                    data=data,
                    options=options,
                )

        # Show credentials form
        description = f"Enter credentials for {self._suggested_model or 'your airfryer'}"
        if self._suggested_ip:
            description += f" at {self._suggested_ip}"

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                }
            ),
            description_placeholders={"description": description},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return PhilipsAirfryerOptionsFlowHandler()


class PhilipsAirfryerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Philips Airfryer."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Use self.config_entry which is automatically available in OptionsFlow
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_COMMAND_URL,
                    default=self.config_entry.options.get(
                        CONF_COMMAND_URL, DEFAULT_COMMAND_URL
                    ),
                ): str,
                vol.Optional(
                    CONF_AIRSPEED,
                    default=self.config_entry.options.get(
                        CONF_AIRSPEED, DEFAULT_AIRSPEED
                    ),
                ): bool,
                vol.Optional(
                    CONF_PROBE,
                    default=self.config_entry.options.get(CONF_PROBE, DEFAULT_PROBE),
                ): bool,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                    ),
                ): cv.positive_int,
                vol.Optional(
                    CONF_REPLACE_TIMESTAMP,
                    default=self.config_entry.options.get(
                        CONF_REPLACE_TIMESTAMP, DEFAULT_REPLACE_TIMESTAMP
                    ),
                ): bool,
                vol.Optional(
                    CONF_TIME_REMAINING,
                    default=self.config_entry.options.get(
                        CONF_TIME_REMAINING, DEFAULT_TIME_REMAINING
                    ),
                ): vol.In(["disp_time", "cur_time"]),
                vol.Optional(
                    CONF_TIME_TOTAL,
                    default=self.config_entry.options.get(
                        CONF_TIME_TOTAL, DEFAULT_TIME_TOTAL
                    ),
                ): vol.In(["total_time", "time"]),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )
