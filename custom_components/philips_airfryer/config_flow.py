"""Config flow for Philips Airfryer integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .airfryer_api import AirfryerAPI
from .const import (
    CONF_AIRSPEED,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_COMMAND_URL,
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

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class PhilipsAirfryerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Philips Airfryer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            ip_address = user_input[CONF_IP_ADDRESS]
            client_id = user_input[CONF_CLIENT_ID]
            client_secret = user_input[CONF_CLIENT_SECRET]

            # Test connection
            api = AirfryerAPI(ip_address, client_id, client_secret)
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
                # Create entry with unique ID based on IP
                await self.async_set_unique_id(ip_address)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Philips Airfryer ({ip_address})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
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
