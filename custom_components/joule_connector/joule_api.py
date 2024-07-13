"""Asynchronous Python client communicating with the JCC API."""
from __future__ import annotations
import asyncio

import asyncio
import json
import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import async_timeout
from aiohttp import ClientError, ClientSession, hdrs
from yarl import URL

from .exceptions import (
    JCCConnectionError,
    JCCError,
    JCCTimeoutError,
)

@dataclass
class Thermostat:
    """Object representing a Thermostat model response from the API."""

    model: str
    serial_number: str
    software_version: str
    name: str
    online: bool
    heating: bool | None
    temperature: int = 0
    set_point_temperature: int = 0
    regulation_mode: int = 0
    supported_regulation_modes: list[int] = field(default_factory=list)
    guid: str = ""
    
    
    def get_current_temperature(self) -> int:
        """Return the current temperature for the thermostat.

        For WD5-series thermostats, the current temperature based on the
        sensor type. If it is set to room/floor, then the average is used.

        Returns
        -------
            The current temperature.

        """
        # Once again, this is easy with the WG4 API:
    
        return self.temperature
    

    def get_target_temperature(self) -> int:
        """Return the current temperature for the thermostat.

        For WD5-series thermostats, the current temperature based on the
        sensor type. If it is set to room/floor, then the average is used.

        Returns
        -------
            The current temperature.

        """
        # Once again, this is easy with the WG4 API:
    
        return self.set_point_temperature

    @classmethod
    def from_wg4_json(cls, data: dict[str, Any]) -> Thermostat:
        """Return a new Thermostat instance based on JSON from the WG4-series API.

        The WG4 API does return schedule data but it is currently ignored.

        Args:
        ----
            data: The JSON data from the API.

        Returns:
        -------
            A Thermostat Object.

        """
        return cls(
            # Technically this could be a UWG4 or AWG4:
            model=data["type"],
            serial_number=data["sn"],
            heating=False,
            software_version=data["current_version"],
            name=data["display_name"],
            regulation_mode=0,
            supported_regulation_modes=[],
            online=data["connected"],
            guid=data["device_id"],
        ) 
    

    @classmethod
    def from_history(cls, thermostat: Thermostat, data: dict[str, Any]) -> Thermostat:
        """Return a new Thermostat instance based on JSON from the JCC History API."""
        thermostat.set_point_temperature = int(data["room_setpoint"]["data"][0]["value"]) * 100
        thermostat.temperature = int(data["ambient_temperature"]["data"][0]["value"]) * 100
        thermostat.name = thermostat.name + " " + thermostat.serial_number


        return thermostat
        


@dataclass
class JouleConnector:
    """Main class for handling data from JCC API."""    

    _auth_host : str = "joule-technologies-dev.eu.auth0.com"
    _host : str = "user-api.dev.joule-cloud.com"
    _token : str = ""

    __request_timeout: float = 30.0
    __http_session: ClientSession | None = None

    async def _request(
        self,
        uri: str,
        *,
        method: str = hdrs.METH_GET,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to the Joule API.

        Args:
        ----
            uri: Request URI, without '/', for example, 'status'
            method: HTTP method to use, for example, 'GET'
            params: Extra options to improve or limit the response.
            body: Data can be used in a POST and PATCH request.

        Returns:
        -------
            A Python dictionary (text) with the response from
            the API.
        """
        try:
            if self.__http_session is None:
                self.__http_session = ClientSession()


            # Reduce the number of calls left by 1.

            usedHost =  self._host

            jsonData = None
            formData = None

            headers = {
                        'Content-Type':  'application/json',
                        'Accept': '*/*',
                    }
            
            if self._token!= "":
                headers['Authorization'] = 'Bearer '+ self._token

            if "/oauth/token" in uri:
                usedHost = self._auth_host
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                formData = body
            else:
                jsonData = body

            url = URL.build(scheme="https", host=usedHost, path="/").join(
                URL(uri)
            )

            async with async_timeout.timeout(self.__request_timeout):
                response = await self.__http_session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=jsonData,
                    data=formData,
                    ssl=True,
                )

            if response.status < 200 | response.status > 300:  
                errorMsg = await response.text()
                raise JCCError(errorMsg)
                
        except asyncio.TimeoutError as exception:
            msg = "Timeout occurred while connecting to the Joule API."
            raise JCCTimeoutError(msg) from exception
        except (ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the Joule API."
            raise JCCConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if not any(item in content_type for item in ["application/json"]):
            text = await response.text()
            msg = "Unexpected content type response from the Joule API"
            raise JCCError(
                msg, {"Content-Type": content_type, "response": text}
            )

        return json.loads(await response.text())

    async def login(self, creds: dict[str, Any]) -> None:
        """Get a valid session to do requests with the Joule API.

        Raises
        ------
            JouleAuthError: An error occurred while authenticating.

        """
        
        # Get a new session.
        data = await self._request(
            "/oauth/token",
            method=hdrs.METH_POST,
            body=creds,
        )

        self._token = data["access_token"]

    async def get_thermostats(self) -> list[Any]:
        """Get a list of thermostats from the JCC API."""

        data = await self._request(
            "/v2/consumer/devices",
            method=hdrs.METH_GET,
        )

        results: list[Thermostat] = []


        for item in data["devices"]:
            if len(item):
                historicalData = await get_thermostat_history(self, Thermostat.from_wg4_json(item))
                results.append(historicalData)

        return results


    async def set_regulation_mode(self, resource: Thermostat, regulation_mode: int, temperature: int, duration: int) -> None:
        """Set the regulation mode for a thermostat."""

        data = await self._request(
            "/v2/consumer/devices/" + resource.guid + "/config",
            method=hdrs.METH_PATCH,
            body={
                "room_setpoint": {
                    "temperature": temperature / 100
                }
            }
        )


async def get_thermostat_history(self, resource: Thermostat) -> Thermostat:
    # /v2/consumer/history/004856b5-20ed-4168-96a5-da316d265a69/latest?filter=ambient_temperature,ambient_humidity,ambient_eco2,ambient_offset,boiler_control_mode,room_setpoint,weekschedule_state,ventilation_level,flame_state

    data = await self._request(
        "/v2/consumer/history/" + resource.guid + "/latest?filter=ambient_temperature,ambient_humidity,ambient_eco2,ambient_offset,boiler_control_mode,room_setpoint,weekschedule_state,ventilation_level,flame_state",
        method=hdrs.METH_GET,
    )

    return Thermostat.from_history(resource, data)