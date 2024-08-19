"""Miscellaneous sensors for Joule thermostats."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
import homeassistant.const

from .joule_api import Thermostat

from .const import DOMAIN
from .models import JouleEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import JouleDataUpdateCoordinator

# A sensor's value is passed through a function of this type to format it.
ValueFormatter = Callable[[Any], Any]

# By default, a sensor's value is fetched from the Thermostat using getattr
# with the sensor description's key. This can be overridden using this type.
ValueGetterOverride = Callable[[Thermostat], Any]


@dataclass
class JouleSensorInfo:
    """Describes a sensor for the Joule thermostat.

    In addition to a SensorEntityDescription for Home Assistant, it may
    include Callables to fetch the raw value (overriding the default behavior
    of using the entity description's key) and to format the raw value.
    """

    entity_description: SensorEntityDescription
    formatter: ValueFormatter | None = None
    # Defaults to getattr on the key if None
    value_getter: ValueGetterOverride | None = None


def _get_value(
    thermostat: Thermostat,
    desc: SensorEntityDescription,
    value_getter: ValueGetterOverride | None,
) -> Any:
    """Fetch a value from the thermostat by using the getter override.

    If it exists, use it, otherwise it fetches the value using getattr
    with the description's key.
    """
    if value_getter:
        return value_getter(thermostat)
    return getattr(thermostat, desc.key)


def _temp_formatter(temp: Any) -> float:
    """Format the temperature."""
    return temp / 100


SENSOR_TYPES: list[JouleSensorInfo] = [
    JouleSensorInfo(
        SensorEntityDescription(
            name="Temperature Room",
            icon="mdi:home-thermometer",
            native_unit_of_measurement=homeassistant.const.UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            key="temperature",
        ),
        formatter=_temp_formatter,
    ),
    JouleSensorInfo(
        SensorEntityDescription(
            name="Humidity Room",
            icon="mdi:water-percent",
            native_unit_of_measurement=homeassistant.const.PERCENTAGE,
            device_class=SensorDeviceClass.HUMIDITY,
            state_class=SensorStateClass.MEASUREMENT,
            key="humidity",
        ),
    )
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Load all Joule Thermostat sensors.

    Args:
    ----
        hass: The HomeAssistant instance.
        entry: The ConfigEntry containing the user input.
        async_add_entities: The callback to provide the created entities to.

    """
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for idx in coordinator.data.keys():  # noqa: SIM118
        for info in SENSOR_TYPES:
            # Different models of thermostat support different sensors;
            # skip creating entities if the value is None.
            val = _get_value(
                coordinator.data[idx], info.entity_description, info.value_getter
            )
            if val is not None:
                entities.append(
                    JouleSensor(
                        coordinator,
                        idx,
                        info.entity_description,
                        info.formatter,
                        info.value_getter,
                    )
                )

    async_add_entities(entities)


class JouleSensor(JouleEntity, SensorEntity):
    """Defines an Joule Sensor."""

    entity_description: SensorEntityDescription
    formatter: ValueFormatter | None
    value_getter: ValueGetterOverride | None

    def __init__(  # pylint: disable=too-many-arguments  # noqa: PLR0913
        self,
        coordinator: JouleDataUpdateCoordinator,
        idx: str,
        entity_description: SensorEntityDescription,
        formatter: ValueFormatter | None,
        value_getter: ValueGetterOverride | None,
    ) -> None:
        """Initialise the entity.

        Args:
        ----
            coordinator: The data coordinator updating the models.
            idx: The identifier for this entity.
            key: The key to get the sensor info from BINARY_SENSOR_TYPES.

        """
        super().__init__(coordinator, idx)

        self.entity_description = entity_description
        self.formatter = formatter
        self.value_getter = value_getter

        self._attr_unique_id = f"{idx}_{self.entity_description.key}"
        self._attr_name = f"{coordinator.data[idx].name} {self.entity_description.name}"

    @property
    def available(self) -> bool:
        """Get the availability status.

        Returns
        -------
            True if the sensor is available, false otherwise.

        """
        return self.coordinator.data[self.idx].online

    @property
    def native_value(self) -> Any | None:
        """Return the state of the sensor.

        Returns
        -------
            The current state value of the sensor.

        """
        thermostat = self.coordinator.data[self.idx]
        val = _get_value(thermostat, self.entity_description, self.value_getter)
        if self.formatter is not None:
            return self.formatter(val)
        return val
