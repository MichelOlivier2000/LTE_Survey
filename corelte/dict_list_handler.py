"""Utility class for saving and loading lists of dictionaries to/from JSON and pickle files."""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

class DictListHandler:
    """Handles serialization and deserialization of dictionary lists to/from files."""
    
    @staticmethod
    def save_to_json(data: List[Dict[str, Any]], filepath: str | Path, pretty: bool = True) -> None:
        """Save a list of dictionaries to a JSON file.
        
        Args:
            data: List of dictionaries to save
            filepath: Path to save the file
            pretty: If True, format JSON with indentation (default: True)
            
        Raises:
            IOError: If there's an error writing to the file
            TypeError: If data cannot be serialized to JSON
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with filepath.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4 if pretty else None)
        except (IOError, TypeError) as e:
            raise IOError(f"Failed to save JSON to {filepath}: {str(e)}")

    @staticmethod
    def read_from_json(filepath: str | Path) -> List[Dict[str, Any]]:
        """Read a list of dictionaries from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            List of dictionaries loaded from the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
            
        try:
            with filepath.open('r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {filepath}: {str(e)}", 
                e.doc, 
                e.pos
            )

    @staticmethod
    def save_to_pickle(data: List[Dict[str, Any]], filepath: str | Path) -> None:
        """Save a list of dictionaries to a pickle file.
        
        Args:
            data: List of dictionaries to save
            filepath: Path to save the file
            
        Raises:
            IOError: If there's an error writing to the file
            pickle.PicklingError: If data cannot be pickled
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with filepath.open('wb') as f:
                pickle.dump(data, f)
        except (IOError, pickle.PicklingError) as e:
            raise IOError(f"Failed to save pickle to {filepath}: {str(e)}")

    @staticmethod
    def read_from_pickle(filepath: str | Path) -> List[Dict[str, Any]]:
        """Read a list of dictionaries from a pickle file.
        
        Args:
            filepath: Path to the pickle file
            
        Returns:
            List of dictionaries loaded from the file
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            pickle.UnpicklingError: If the file contains invalid pickle data
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
            
        try:
            with filepath.open('rb') as f:
                return pickle.load(f)
        except pickle.UnpicklingError as e:
            raise pickle.UnpicklingError(f"Invalid pickle data in {filepath}: {str(e)}")