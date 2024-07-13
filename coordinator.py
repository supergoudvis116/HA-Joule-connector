"""Joule Thermostat platform configuration."""

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import  CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_TIMEOUT, DOMAIN, UPDATE_INTERVAL

from .joule_api import JouleConnector, JCCError, Thermostat

_LOGGER = logging.getLogger(__name__)


class JouleDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to fetch data."""

    username = ""
    password = ""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Class to manage fetching Joule data.

        Args:
        ----
            hass: The HomeAssistant instance.
            entry: The ConfigEntry containing the user input.

        """
    
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Thermostat]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.

        Returns
        -------
            An object containing the serial number as a key, and
            the resource as a value.

        Raises
        ------
            ConfigEntryAuthFailed: An invalid config was ued.
            UpdateFailed: An error occurred when updating the data.

        """


        try:
            async with async_timeout.timeout(API_TIMEOUT):
                creds = {"username": self.username, 
                        'password': self.password, 
                        'grant_type': 'password', 
                        'scope': 'openid email profile', 
                        'audience': 'https://user-api.joule-cloud.com/',
                        'client_id': 'lS6O7Nf6WV7mxxXe0hBSbCxqyFdhgvqd'
                        }

                self.api = JouleConnector()
                await self.api.login(creds)


                thermostats = await self.api.get_thermostats()

                return {resource.serial_number: resource for resource in thermostats}


        except JCCError as error:
            raise UpdateFailed(error) from error
