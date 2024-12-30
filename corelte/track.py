"""Module for handling GPS track data and processing."""

from datetime import datetime
from typing import List, Optional
from xml.dom import minidom
from xml.dom.minidom import Element

from .argument import Argument
from .cursor import Cursor
from .datetime_local import convert_utc_to_local
from .reading import Reading

class Track:
    """Handles GPS track data processing and manipulation."""
    
    def __init__(self, argument: Argument):
        """Initialize Track instance.
        
        Args:
            argument: Configuration object containing survey parameters
        """
        self.argument = argument
        self.lines_gps: List[Reading] = []
        self.cursor = Cursor()

    def read_gpx_file_into_lines_gps(self) -> None:
        """Read and parse GPX file into GPS readings.
        
        Raises:
            FileNotFoundError: If GPX file doesn't exist
            xml.parsers.expat.ExpatError: If GPX file is malformed
            ValueError: If required GPS data is missing or invalid
        """
        try:
            # Parse GPX file
            gpx_doc = minidom.parse(str(self.argument.gps_filename))
            track_points = gpx_doc.getElementsByTagName('trkpt')
            
            if not track_points:
                raise ValueError("No track points found in GPX file")
            
            # Process each track point
            for point in track_points:
                reading = self._process_track_point(point)
                if reading:
                    self.lines_gps.append(reading)
            
            if not self.lines_gps:
                raise ValueError("No valid GPS readings could be extracted")
            
            # Set cursor to first valid reading
            self._initialize_cursor()
            
            print(f"Successfully processed {len(self.lines_gps)} GPS points")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"GPX file not found: {self.argument.gps_filename}")
        except Exception as e:
            raise ValueError(f"Failed to process GPX file: {str(e)}") from e

    def extend_gps_records_to_every_second(self) -> None:
        """Interpolate GPS points to ensure one reading per second.
        
        This method fills gaps between GPS readings by linear interpolation.
        """
        if not self.lines_gps:
            return
            
        new_lines: List[Reading] = []
        
        for idx in range(len(self.lines_gps) - 1):
            r1 = self.lines_gps[idx]
            r2 = self.lines_gps[idx + 1]
            
            # Add original point
            new_lines.append(r1)
            
            # Calculate time difference and interpolate if needed
            time_diff = (r2.reading_time - r1.reading_time).seconds
            if time_diff > 1:
                new_lines.extend(self._interpolate_points(r1, r2, time_diff))
        
        # Add last point
        if self.lines_gps:
            new_lines.append(self.lines_gps[-1])
            
        self.lines_gps = new_lines

    def calculate_speed_and_direction(self) -> None:
        """Calculate speed and direction for each GPS point.
        
        This method updates each reading with calculated speed and azimuth
        based on the next point in the sequence.
        """
        if len(self.lines_gps) < 2:
            return
            
        for idx in range(len(self.lines_gps) - 1):
            r1 = self.lines_gps[idx]
            r2 = self.lines_gps[idx + 1]
            r1.calculate_azimuth_and_speed(r2)

    def _process_track_point(self, point: Element) -> Optional[Reading]:
        """Process a single track point from GPX data.
        
        Args:
            point: XML element containing track point data
            
        Returns:
            Reading object if successful, None if point data is invalid
        """
        try:
            reading = Reading(self.argument.survey_id)
            
            # Extract and convert time
            time_elements = point.getElementsByTagName('time')
            if not time_elements:
                return None
                
            time_str = time_elements[0].firstChild.data
            reading.set_datetime_naive_from_str(time_str)
            reading.reading_time = convert_utc_to_local(reading.reading_time).replace(tzinfo=None)
            
            # Extract coordinates
            reading.set_latitude_from_str(point.attributes['lat'].value)
            reading.set_longitude_from_str(point.attributes['lon'].value)
            
            return reading if reading.latitude and reading.longitude else None
            
        except (AttributeError, KeyError, ValueError):
            return None

    def _interpolate_points(self, r1: Reading, r2: Reading, time_diff: int) -> List[Reading]:
        """Create interpolated points between two readings.
        
        Args:
            r1: First reading
            r2: Second reading
            time_diff: Time difference in seconds
            
        Returns:
            List of interpolated Reading objects
        """
        interpolated: List[Reading] = []
        
        for i in range(1, time_diff):
            r = Reading(self.argument.survey_id)
            r.init_ratio(r1, r2, i/time_diff)
            interpolated.append(r)
            
        return interpolated

    def _initialize_cursor(self) -> None:
        """Initialize cursor with first valid GPS reading."""
        if self.lines_gps:
            self.cursor.first_non_null_idx = 0
            self.cursor.first_non_null_reading_time = self.lines_gps[0].reading_time

