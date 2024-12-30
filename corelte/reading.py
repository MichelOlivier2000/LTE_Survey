"""Module for handling individual GPS and cellular network readings."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from pyproj import Geod
from typing import Optional

@dataclass
class Reading:
    """Represents a single reading combining GPS and cellular network data.
    
    Attributes:
        band: Network band (e.g., 3, 7, 20)
        bwd_azimuth: Backward azimuth in degrees
        calculated: Whether values were calculated/interpolated
        carrier: Network carrier name
        cellid: Cell identifier
        reading_time: Timestamp of the reading
        earfcn: E-UTRA Absolute Radio Frequency Channel Number
        file_idx: Index in the source file
        fwd_azimuth: Forward azimuth in degrees
        fwd_distance: Forward distance in meters
        latitude: GPS latitude
        longitude: GPS longitude
        pci: Physical Cell ID
        rsrp: Reference Signal Received Power
        speed: Movement speed in m/s
        survey_id: Survey identifier
        tac: Tracking Area Code
    """
    band: Optional[int] = None
    bwd_azimuth: Optional[int] = None
    calculated: bool = False
    carrier: str = ""
    cellid: Optional[int] = None
    reading_time: Optional[datetime] = None
    earfcn: str = ""
    file_idx: Optional[int] = None
    fwd_azimuth: Optional[int] = None
    fwd_distance: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pci: Optional[int] = None
    rsrp: str = ""
    speed: Optional[float] = None
    survey_id: Optional[int] = None
    tac: Optional[int] = None

    def __init__(self, survey_id: int) -> None:
        """Initialize a new Reading instance.
        
        Args:
            survey_id: The survey identifier
        """
        self.survey_id = survey_id

    def set_datetime_naive_from_str(self, datestr: str) -> None:
        """Parse a naive datetime from string.
        
        Args:
            datestr: Date string in format "YYYY-MM-DDThh:mm:ssZ"
        """
        if len(datestr) < 19:
            return        
        self.reading_time = datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)

    def set_datetime_aware_from_str(self, datestr: str) -> None:
        """Parse an aware datetime from string.
        
        Args:
            datestr: Date string in format "YYYY-MM-DDThh:mm:ss.uuuuuu+zz:zz"
        """
        if len(datestr) < 19:
            return
        self.reading_time = datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=None)

    def init_ratio(self, r1: 'Reading', r2: 'Reading', ratio: float) -> None:
        """Interpolate reading values between two points.
        
        Args:
            r1: First reading point
            r2: Second reading point
            ratio: Interpolation ratio between 0 and 1
        """
        self.calculated = True
        self.reading_time = r1.reading_time + (r2.reading_time - r1.reading_time) * ratio
        self.file_idx = r1.file_idx
        self._interpolate_coordinates(r1, r2, ratio)

    def _interpolate_coordinates(self, r1: 'Reading', r2: 'Reading', ratio: float) -> None:
        """Helper method to interpolate geographical coordinates."""
        self.latitude = r1.latitude + (r2.latitude - r1.latitude) * ratio
        self.longitude = r1.longitude + (r2.longitude - r1.longitude) * ratio

    def calculate_azimuth_and_speed(self, r2: 'Reading') -> None:
        """Calculate azimuth and speed between this reading and another point."""
        if not self._has_valid_coordinates() or not r2._has_valid_coordinates():
            return

        geod = Geod(ellps="WGS84")
        self.fwd_azimuth, self.bwd_azimuth, self.fwd_distance = \
            geod.inv(self.longitude, self.latitude, r2.longitude, r2.latitude)    
        
        self._calculate_speed(r2)

    def _calculate_speed(self, r2: 'Reading') -> None:
        """Calculate speed based on time difference and distance."""
        if not self.reading_time or not r2.reading_time:
            self.speed = None
            return

        diff_dt = r2.reading_time - self.reading_time
        try:
            self.speed = self.fwd_distance / diff_dt.total_seconds()
        except (ZeroDivisionError, TypeError):
            self.speed = None

    def _has_valid_coordinates(self) -> bool:
        """Check if reading has valid coordinates."""
        return self.latitude is not None and self.longitude is not None

    def apply_time_compensation(self) -> None:
        """Compensate for measurement reaction time based on speed (3m per m/s)."""
        if not self.speed or not self._has_valid_coordinates():
            return

        distance = self.speed * 3
        geod = Geod(ellps="WGS84")
        compensated_coords = geod.fwd(
            lons=self.longitude,
            lats=self.latitude,
            az=self.bwd_azimuth,
            dist=distance,
            radians=False
        )
        self.longitude, self.latitude = compensated_coords[0:2]

    def set_latitude_from_str(self, latstr: str) -> None:
        """Set latitude from string value.
        
        Args:
            latstr: String representation of latitude
        """
        try:
            self.latitude = float(latstr)
        except (ValueError, TypeError):
            self.latitude = None

    def set_longitude_from_str(self, lonstr: str) -> None:
        """Set longitude from string value.
        
        Args:
            lonstr: String representation of longitude
        """
        try:
            self.longitude = float(lonstr)
        except (ValueError, TypeError):
            self.longitude = None

    def check_errors(self) -> None:
        """Correct typical Tesseract reading errors."""
        self._correct_band_errors()
        self._validate_numeric_fields()

    def _correct_band_errors(self) -> None:
        """Apply specific corrections for band field errors."""
        band_corrections = {'S': 5, '}': 3, 'S)': 3}
        if str(self.band) in band_corrections:
            self.band = band_corrections[str(self.band)]

    def _validate_numeric_fields(self) -> None:
        """Validate numeric fields have correct values."""
        if not str(self.band).isnumeric():
            print(f"band is not numeric: {self.band}")
        if not str(self.pci).isnumeric():
            print(f"pci is not numeric: {self.pci}")

    def is_valid(self) -> bool:
        """Check if the reading has valid data.
        
        Returns:
            bool: True if reading has valid cellid, False otherwise
        """
        return bool(self.cellid and self.cellid >= 99999)

    def fields(self) -> list[str]:
        """Get list of field names for CSV export.
        
        Returns:
            List of field names
        """
        return ["survey_id", "carrier",
                "cell_id", "pci", "tac", "band", 
                "reading_timestamp", 
                "fwd_azimuth", "bwd_azimuth", "speed", 
                "file_idx", "calculated", 
                "latitude", "longitude"]

    def csv_row(self) -> list:
        """Get values formatted for CSV export.
        
        Returns:
            List of values corresponding to fields()
        """
        dt = self.reading_time if self.reading_time is not None else 0    
        return [self.survey_id, self.carrier,
                self.cellid, self.pci, self.tac, self.band, 
                dt, 
                self.fwd_azimuth, self.bwd_azimuth, self.speed, 
                self.file_idx, self.calculated,
                round(self.latitude, 6) if self.latitude else '', 
                round(self.longitude, 6) if self.longitude else '']


