"""Config flow to configure Joule."""

from io import BytesIO
import json
from typing import Any

import logging
from urllib.parse import urlencode
import requests
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_KEY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .joule_api import (
    JCCConnectionError,
    JCCError,
    JCCTimeoutError,
)

from .joule_api import JouleConnector
from .const import (
    CONF_COMFORT_MODE_DURATION,
    CONF_CUSTOMER_ID,
    CONF_MODEL,
    CONF_USE_COMFORT_MODE,
    CONFIG_FLOW_VERSION,
    DOMAIN,
    INTEGRATION_NAME,
    MODEL_WD5_SERIES,
    MODEL_WG4_SERIES,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODEL): vol.In([MODEL_WD5_SERIES, MODEL_WG4_SERIES]),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        CONF_CUSTOMER_ID: int,
        CONF_API_KEY: str,
    }
)

WG4_STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str
    }
)


class JouleFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle an Joule config flow."""

    VERSION = CONFIG_FLOW_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler.

        Args:
        ----
            config_entry: The ConfigEntry instance.

        Returns:
        -------
            The created config flow.

        """
        return JouleOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Handle a flow initialized by the user.

        Args:
        ----
            user_input: The input received from the user or none.

        Returns:
        -------
            The created config entry or a form to re-enter the user input with errors.

        """
        return await self.async_step_wg4()

    async def async_step_wg4(self, user_input: dict[str, Any] | None = None) -> Any:
        """Step that gathers information for WG4-series thermostats.

        The result is a config entry if successful.

        Args:
        ----
            user_input: The input received from the user or none.

        Returns:
        -------
            The created config entry or a form to re-enter the user input with errors.

        """
        errors: dict[str, str] = {}
        if user_input:

            _LOGGER.debug("Trying to create entry with data: %s", user_input)

            result = await self._async_try_create_entry(
                {
                    CONF_MODEL: MODEL_WG4_SERIES,
                    **user_input,
                },
                errors,
            )
            if result is not None:
                return result
        return self.async_show_form(
            step_id="wg4", data_schema=WG4_STEP_SCHEMA, errors=errors
        )


    async def _async_try_create_entry(
        self, data: dict[str, Any], errors: dict[str, str]
    ) -> FlowResult | None:
        """Validate the config entry data and logs in to the API.

        If successful, calls async_create_entry and returns the FlowResult.
        Otherwise, stores an error in the errors dict and returns None.
        """



        data = DATA_SCHEMA(data)
        try:
            # Disallow duplicate entries...
            self._async_abort_entries_match(
                {
                    k: data[k]
                    for k in data
                    # ... only considering model/host/username as
                    # distinguishing keys.
                    if k in [CONF_USERNAME]
                }
            )
                        
            creds = {"username": data[CONF_USERNAME], 
                     'password':  data[CONF_PASSWORD],
                     'grant_type': 'password', 
                     'scope': 'openid email profile', 
                     'audience': 'https://user-api.joule-cloud.com/',
                     'client_secret': 'Y8LFBEcfE3iZagOPNcrK3DvPsqrrAddXsy1D3jSICu7-LYoWJuohk13yZgWXD5UP',
                     'client_id': 'KUDPOkC48V3AfQH9GoVnDsvzlyAuvKFD'
                     }

            api = JouleConnector()
            await api.login(creds)
        except JCCTimeoutError:
            errors["base"] = "timeout"
        except JCCConnectionError:
            errors["base"] = "connection_failed"
        except JCCError:
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(
                title=f"{INTEGRATION_NAME} ({data[CONF_USERNAME]})", data=data
            )
        return None


class JouleOptionsFlowHandler(OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow.

        Args:
        ----
            config_entry: The ConfigEntry instance.

        """
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user.

        Args:
        ----
            user_input: The input received from the user or none.

        Returns:
        -------
            The created config entry.

        """
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_USE_COMFORT_MODE,
                        default=self.config_entry.options.get(
                            CONF_USE_COMFORT_MODE, False
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_COMFORT_MODE_DURATION,
                        default=self.config_entry.options.get(
                            CONF_COMFORT_MODE_DURATION, COMFORT_DURATION
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                }
            ),
        )
