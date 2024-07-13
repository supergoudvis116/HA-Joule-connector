"""Asynchronous Python client controlling an Joule Thermostat."""


class JCCError(Exception):
    """Generic API exception."""


class JCCAuthError(JCCError):
    """API authentication/authorization exception."""


class JCCConnectionError(JCCError):
    """API connection exception."""


class JCCResultsError(JCCError):
    """API results exception."""


class JCCTimeoutError(JCCError):
    """API request timed out."""