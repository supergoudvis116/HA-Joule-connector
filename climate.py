"""Climate sensors for Joule."""

import asyncio
import logging
from collections.abc import Mapping
from typing import Any, ClassVar

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .exceptions import JCCError

from .const import (
    CONF_COMFORT_MODE_DURATION,
    CONF_USE_COMFORT_MODE,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import JouleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)



async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Load all Joule Thermostat devices.

    Args:
    ----
        hass: The HomeAssistant instance.
        entry: The ConfigEntry containing the user input.
        async_add_entities: The callback to provide the created entities to.

    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for idx in coordinator.data:
        entities.append(  # noqa: PERF401
            JouleThermostat(
                coordinator=coordinator, idx=idx, options=entry.options
            )
        )
    async_add_entities(entities)


class JouleThermostat(
    CoordinatorEntity[JouleDataUpdateCoordinator], ClimateEntity
):
    """JouleThermostat climate."""

    _attr_hvac_modes: ClassVar[list[HVACMode]] = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = (
        ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TARGET_TEMPERATURE
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "ojthermostat"

    idx: str
    options: Mapping[str, Any]

    def __init__(
        self,
        coordinator: JouleDataUpdateCoordinator,
        idx: str,
        options: Mapping[str, Any],
    ) -> None:
        """Initialise the entity.

        Args:
        ----
            coordinator: The data coordinator updating the models.
            idx: The identifier for this entity.
            options: The options provided by the user.

        """
        super().__init__(coordinator)
        self.idx = idx
        self.options = options
        self._attr_unique_id = self.idx

    @property
    def device_info(self) -> DeviceInfo:
        """Set up the device information for this thermostat.

        Returns
        -------
            The device identifiers to make sure the entity is attached
            to the correct device.

        """
        return DeviceInfo(
            identifiers={(DOMAIN, self.idx)},
            manufacturer=MANUFACTURER,
            name=self.coordinator.data[self.idx].name,
            sw_version=self.coordinator.data[self.idx].software_version,
            model=self.coordinator.data[self.idx].model,
        )


    @property
    def current_temperature(self) -> float:
        """Return current temperature.

        Returns
        -------
            The current temperature in a float format..

        """
        return self.coordinator.data[self.idx].get_current_temperature() / 100

    @property
    def target_temperature(self) -> float:
        """Return target temperature.

        Returns
        -------
            The target temperature in a float format.

        """
        return self.coordinator.data[self.idx].get_target_temperature() / 100


    @property
    def preset_modes(self) -> list[str] | None:
        """Return a list of available preset modes.

        Returns
        -------
            A list of supported preset modes in string format.

        """
        return [
        ]

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode, e.g., schedule, manual.

        Returns
        -------
            The preset mode in a string format.

        """
        return ""  # type: ignore[return-value]

    @property
    def hvac_action(self) -> HVACAction | None:
        """Indicates whether the thermostat is currently heating.

        Returns
        -------
            The HVACAction.

        """
        thermostat = self.coordinator.data[self.idx]
        if thermostat.heating:
            return HVACAction.HEATING
        if thermostat.online:
            return HVACAction.IDLE
        return HVACAction.OFF

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode.

        Args:
        ----
            preset_mode: The preset mode to set the thermostat to.

        """
        try:
            await self.coordinator.api.set_regulation_mode(
                self.coordinator.data[self.idx],
                HA_TO_VENDOR_STATE.get(preset_mode),
            )
            await self._async_delayed_request_refresh()
        except JCCError:
            _LOGGER.exception(
                'Failed setting preset mode "%s" (%s)',
                self.coordinator.data[self.idx].name,
                preset_mode,
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new temperature.

        Args:
        ----
            **kwargs: All arguments passed to the method.

        """
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        regulation_mode = 0
        if self.options.get(CONF_USE_COMFORT_MODE) is True:
            regulation_mode = REGULATION_COMFORT

        await self.coordinator.api.set_regulation_mode(
            resource=self.coordinator.data[self.unique_id],
            regulation_mode=regulation_mode,
            temperature=int(temperature * 100),
            duration=self.options.get(CONF_COMFORT_MODE_DURATION),
        )
        await self._async_delayed_request_refresh()

    async def _async_delayed_request_refresh(self) -> None:
        """Get delayed data from the coordinator.

        Refreshing immediately after an API call can return stale data,
        probably due to DB propagation on the API backend.

        The *ideal* fix would be to switch away from polling; the API
        does support some sort of HTTP-long-poll notification mechanism.

        As a temporary band-aid, sleep for 2 seconds and then request a
        refresh. Manual testing indicates this seems to work well enough;
        1 second was verified to be too short.
        """
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(
        self,
        hvac_mode: str,  # pylint: disable=unused-argument  # noqa: ARG002
    ) -> bool:
        """Set new hvac mode.

        Always ignore; we only support HEATING mode.

        Args:
        ----
            hvac_mode: Currently not used.

        """
        return True
