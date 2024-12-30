from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List
import os
import yaml

# !!! A corriger, et tester la configuration au démarrage.
MYOCR_SWIFT_PRG = Path('/Volumes/HOME/kDrive/DEV/LTE/Swift/MyOCR/myocr')

class OCRMode(Enum):
    TESSERACT = 1
    MYOCR = 2
    MYOCR_PLUS = 3

@dataclass
class Argument:
    """Handles survey configuration and file management for OCR processing."""
    # Required parameters
    network_id: int
    survey_id: int
    
    # Optional parameters with defaults
    ocr_mode: OCRMode = OCRMode.MYOCR_PLUS
    verbose: bool = True
    device: str = ""
    erase_png: bool = False
    erase_txt: bool = False
    exclusions: List[str] = None
    os_version: str = ""
    model: str = ""
    save_to_db: bool = False
    scale_factor: float = 0.5
    survey_comment: str = ""
    time_scan_probe: int = 90

    def __post_init__(self):
        """Initialize paths and load configuration."""
        self.exclusions = self.exclusions or []
        self._setup_survey_paths()
        self._setup_file_paths()
        self._validate_required_files()
        self._load_yaml_config()
        self._extract_mp4_create_date()

    def _setup_survey_paths(self):
        """Set up the survey directory structure."""
        net_str = f'{self.network_id:02}'
        survey_str = f'{self.survey_id:04}'
        centaine = f'{self.survey_id // 100:02}'
        dizaine = f'{(self.survey_id % 100) // 10}0'

        surveys_root = Path('/Volumes/HOME/kDrive/DATA/LTE/SURVEYS')
        self.survey_dir = surveys_root / f'Net_{net_str}' / centaine / dizaine / f'Survey_{survey_str}'
        self.survey_img_dir = self.survey_dir / 'img'
        self.survey_tmp_dir = self.survey_dir / 'tmp'
        self.survey_tmp_dir.mkdir(exist_ok=True)

    def _setup_file_paths(self):
        """Set up paths for all required files."""
        net_str = str(self.network_id).zfill(2)
        survey_str = str(self.survey_id).zfill(4)
        base_name = f'Survey_{net_str}_{survey_str}'

        # Main files
        self.mp4_filename = self.survey_dir / f'{base_name}.mp4'
        self.gps_filename = self.survey_dir / f'{base_name}.gpx'
        self.csv_filename = self.survey_dir / f'{base_name}.csv'
        self.arg_filename = self.survey_dir / 'args.yaml'

        # Temporary files
        self.tmp_mp4_filename = self.survey_tmp_dir / f'{base_name}_mp4.csv'
        self.tmp_gps_filename = self.survey_tmp_dir / f'{base_name}_gps.csv'

        # OCR files
        self.tmp_frames_to_ocr_filename_txt = self.survey_tmp_dir / f'{base_name}_ocr_frames.txt'
        self.tmp_frames_to_ocr_filename_json = self.survey_tmp_dir / f'{base_name}_ocr_frames.json'
        self.tmp_times_to_ocr_filename_txt = self.survey_tmp_dir / f'{base_name}_ocr_times.txt'
        self.tmp_times_to_ocr_filename_json = self.survey_tmp_dir / f'{base_name}_ocr_times.json'

    def _validate_required_files(self):
        """Validate existence of required files."""
        if not self.mp4_filename.exists():
            raise FileNotFoundError(f"Screencast file not found: {self.mp4_filename}")
        
        if not self.gps_filename.exists():
            raise FileNotFoundError(f"GPS file not found: {self.gps_filename}")

    def _load_yaml_config(self):
        """Load and parse arguments from YAML configuration file."""
        try:
            with open(self.arg_filename, 'r') as f:
                args = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Arguments file not found: {self.arg_filename}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}")

        self._update_from_yaml(args)
        self._print_config_if_verbose()

    def _update_from_yaml(self, args: dict):
        """Update instance attributes from YAML configuration."""
        survey_config = args['survey']
        self.survey_comment = survey_config['comment']
        self.device = survey_config['device']
        self.model = survey_config['model']
        self.os_version = survey_config['os_version']
        self.exclusions = args['exclusions']

    def _print_config_if_verbose(self):
        """Print configuration details if verbose mode is enabled."""
        if not self.verbose:
            return

        print(f'OCR Mode: {self.ocr_mode.name}')
        print(f'Comment: {self.survey_comment}')
        print(f'Exclusions: {self.exclusions}')
        print(f'Survey Number: {self.survey_id}')
        print(f'Screencast file: {self.mp4_filename}')
        print(f'GPS file: {self.gps_filename}')

    def _extract_mp4_create_date(self):
        """Extract and validate creation date from MP4 file."""
        cmd = f'exiftool "{self.mp4_filename}" | grep "Media Create Date"'
        date_str = os.popen(cmd).read().strip()[-19:]
        
        try:
            self.mp4_create_date = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except ValueError as e:
            raise ValueError(
                f"Failed to extract creation date from screencast.\n"
                f"File: {self.mp4_filename}\n"
                f"Date string: {date_str}\n"
                f"Error: {str(e)}"
            )


