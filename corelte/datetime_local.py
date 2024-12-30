"""Utilities for converting between UTC and local timezone (Zurich) timestamps."""

from datetime import datetime
import pytz
from typing import Optional

# Constants
ZURICH_TIMEZONE = 'Europe/Zurich'

def convert_utc_to_local(utc_datetime: datetime) -> datetime:
    """Convert a UTC datetime to local Zurich time.

    Args:
        utc_datetime: A naive datetime object assumed to be in UTC.

    Returns:
        datetime: A naive datetime object converted to Zurich local time.

    Example:
        >>> utc_time = datetime(2024, 1, 1, 12, 0)  # noon UTC
        >>> local_time = convert_utc_to_local(utc_time)  # 13:00 in winter, 14:00 in summer
    """
    if not isinstance(utc_datetime, datetime):
        raise TypeError("Input must be a datetime object")

    utc_tz = pytz.UTC
    local_tz = pytz.timezone(ZURICH_TIMEZONE)

    # Localize the datetime to UTC
    utc_datetime = utc_tz.localize(utc_datetime)

    # Convert to local time
    local_datetime = utc_datetime.astimezone(local_tz)

    # Return naive datetime for compatibility
    return local_datetime.replace(tzinfo=None)

def convert_local_to_utc(local_datetime: datetime) -> datetime:
    """Convert a local Zurich time to UTC.

    Args:
        local_datetime: A naive datetime object assumed to be in Zurich time.

    Returns:
        datetime: A naive datetime object converted to UTC.

    Example:
        >>> local_time = datetime(2024, 1, 1, 13, 0)  # 1 PM Zurich time
        >>> utc_time = convert_local_to_utc(local_time)  # noon UTC in winter
    """
    if not isinstance(local_datetime, datetime):
        raise TypeError("Input must be a datetime object")

    local_tz = pytz.timezone(ZURICH_TIMEZONE)
    
    # Localize the datetime to Zurich time
    local_datetime = local_tz.localize(local_datetime)
    
    # Convert to UTC
    utc_datetime = local_datetime.astimezone(pytz.UTC)
    
    # Return naive datetime for compatibility
    return utc_datetime.replace(tzinfo=None)