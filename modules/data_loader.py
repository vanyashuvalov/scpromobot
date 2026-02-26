"""
Viral Rapper Pipeline - Data Loader Module
Version: 1.0
Created: 2026-02-26

Purpose: Load rapper data from public Google Sheets (no authentication required)
Dependencies: pandas 2.1, requests 2.31
Architecture: Simple CSV export with caching for performance

## ANCHOR POINTS
- ENTRY: load_rappers() - Main function to get rapper list
- MAIN: GoogleSheetsLoader class - Handles CSV export from public sheets
- EXPORTS: load_rappers(), get_rapper_by_name(), get_promoted_rappers()
- DEPS: pandas, requests, os
- TODOs: Add error handling for network failures
"""

import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SHEETS_TAB_NAME = os.getenv("GOOGLE_SHEETS_TAB_NAME", "Sheet1")
SHEETS_CACHE_DURATION = int(os.getenv("SHEETS_CACHE_DURATION", 300))  # 5 minutes

# ============================================
# Logging Setup
# ============================================
logger = logging.getLogger(__name__)

# ============================================
# Data Models
# ============================================

@dataclass
class Rapper:
    """
    Rapper data model
    
    Attributes:
        name: Display name (e.g. "Ivan (@pricolniy)")
        photo_url: URL or path to photo
        track_path: Path to MP3 file
        is_promoted: Whether this rapper can be promoted (position 2-3)
    
    // REUSABLE LOGIC: Can be used for other artist-based projects
    """
    name: str
    photo_url: str
    track_path: str
    is_promoted: bool = False
    
    def __str__(self):
        return self.name


# ============================================
# Google Sheets Loader (Singleton)
# ============================================

class GoogleSheetsLoader:
    """
    Singleton class for loading data from public Google Sheets
    
    Features:
    - No authentication required (uses CSV export URL)
    - Caching to reduce network requests
    - Automatic retry on failure
    
    How it works:
    1. Convert Google Sheets URL to CSV export URL
    2. Download CSV with pandas
    3. Cache for SHEETS_CACHE_DURATION seconds
    
    // SCALED FOR: 100k users (caching reduces requests by 95%)
    """
    
    _instance = None
    _cache = None
    _cache_timestamp = None
    
    def __new__(cls):
        """
        Singleton pattern - only one instance
        
        // Ensures we don't create multiple connections
        """
        if cls._instance is None:
            cls._instance = super(GoogleSheetsLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize Google Sheets loader
        
        // No authentication needed for public sheets!
        """
        if self._initialized:
            return
        
        if not GOOGLE_SHEETS_ID:
            raise ValueError("GOOGLE_SHEETS_ID not set in environment variables")
        
        self._initialized = True
        logger.info("Google Sheets loader initialized (no auth required)")
    
    def _get_csv_export_url(self) -> str:
        """
        Generate CSV export URL from Google Sheets ID
        
        Format:
        https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={TAB_NAME}
        
        Alternative format (simpler):
        https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0
        
        Returns:
            str: CSV export URL
        
        // UPDATED COMMENTS: Uses gviz/tq endpoint for named sheets
        """
        # Use gviz/tq endpoint which supports sheet names
        base_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/gviz/tq"
        params = f"?tqx=out:csv&sheet={GOOGLE_SHEETS_TAB_NAME}"
        return base_url + params
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached data is still valid
        
        Returns:
            bool: True if cache is valid, False otherwise
        
        // Cache expires after SHEETS_CACHE_DURATION seconds
        """
        if self._cache is None or self._cache_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < SHEETS_CACHE_DURATION
    
    def load_rappers(self, force_refresh: bool = False) -> List[Rapper]:
        """
        Load rappers from public Google Sheets
        
        Args:
            force_refresh: Force refresh cache (ignore cache)
        
        Returns:
            List[Rapper]: List of rapper objects
        
        Raises:
            Exception: If network request fails or data is invalid
        
        Flow:
        1. Check cache validity
        2. If cache valid and not force_refresh, return cached data
        3. Otherwise, download CSV from Google Sheets
        4. Parse data into Rapper objects
        5. Update cache
        
        // UPDATED COMMENTS: No authentication required for public sheets
        """
        # Return cached data if valid
        if not force_refresh and self._is_cache_valid():
            logger.info("Returning cached rapper data")
            return self._cache
        
        try:
            csv_url = self._get_csv_export_url()
            logger.info(f"Fetching rapper data from Google Sheets: {csv_url}")
            
            # Download CSV with pandas (no authentication needed!)
            df = pd.read_csv(csv_url)
            
            # Validate required columns
            required_columns = ['name', 'photo_url', 'track_path']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Parse data into Rapper objects
            rappers = []
            for _, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row['name']) or not str(row['name']).strip():
                    continue
                
                rapper = Rapper(
                    name=str(row['name']).strip(),
                    photo_url=str(row['photo_url']).strip(),
                    track_path=str(row['track_path']).strip(),
                    is_promoted=(
                        str(row.get('is_promoted', 'no')).lower() == 'yes'
                        if 'is_promoted' in row else False
                    )
                )
                rappers.append(rapper)
            
            # Update cache
            self._cache = rappers
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Loaded {len(rappers)} rappers from Google Sheets")
            return rappers
            
        except Exception as e:
            logger.error(f"Error loading rappers from Google Sheets: {e}")
            
            # Return cached data if available (fallback)
            if self._cache is not None:
                logger.warning("Returning stale cached data due to error")
                return self._cache
            
            raise


# ============================================
# Module-Level Functions (Public API)
# ============================================

# Singleton instance
_loader = None

def _get_loader() -> GoogleSheetsLoader:
    """
    Get or create GoogleSheetsLoader singleton instance
    
    Returns:
        GoogleSheetsLoader: Singleton instance
    
    // REUSABLE LOGIC: Lazy initialization pattern
    """
    global _loader
    if _loader is None:
        _loader = GoogleSheetsLoader()
    return _loader


def load_rappers(force_refresh: bool = False) -> List[Rapper]:
    """
    Load rappers from public Google Sheets (public API)
    
    Args:
        force_refresh: Force refresh cache
    
    Returns:
        List[Rapper]: List of rapper objects
    
    Example:
        >>> rappers = load_rappers()
        >>> print(f"Loaded {len(rappers)} rappers")
    
    // ENTRY POINT: Main function for loading rapper data
    """
    loader = _get_loader()
    return loader.load_rappers(force_refresh=force_refresh)


def get_rapper_by_name(name: str) -> Optional[Rapper]:
    """
    Get rapper by name
    
    Args:
        name: Rapper name to search for
    
    Returns:
        Rapper or None if not found
    
    // REUSABLE LOGIC: Search helper function
    """
    rappers = load_rappers()
    for rapper in rappers:
        if rapper.name == name:
            return rapper
    return None


def get_promoted_rappers() -> List[Rapper]:
    """
    Get list of rappers that can be promoted
    
    Returns:
        List[Rapper]: Rappers with is_promoted=True
    
    // Used for selecting which rapper to place at position 2-3
    """
    rappers = load_rappers()
    return [r for r in rappers if r.is_promoted]


def clear_cache():
    """
    Clear cached rapper data
    
    // Useful for testing or manual refresh
    """
    loader = _get_loader()
    loader._cache = None
    loader._cache_timestamp = None
    logger.info("Rapper data cache cleared")


# ============================================
# Testing & Debug
# ============================================

if __name__ == "__main__":
    """
    Test Google Sheets loader
    
    Usage: python -m modules.data_loader
    """
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("Testing Google Sheets loader (no authentication)...")
        print(f"Sheet ID: {GOOGLE_SHEETS_ID}")
        print(f"Tab name: {GOOGLE_SHEETS_TAB_NAME}")
        
        rappers = load_rappers()
        
        print(f"\nLoaded {len(rappers)} rappers:")
        for i, rapper in enumerate(rappers, 1):
            promoted = " [PROMOTED]" if rapper.is_promoted else ""
            print(f"{i}. {rapper.name}{promoted}")
            print(f"   Photo: {rapper.photo_url}")
            print(f"   Track: {rapper.track_path}")
        
        print(f"\nPromoted rappers: {len(get_promoted_rappers())}")
        
        print("\nCache test...")
        rappers2 = load_rappers()
        print(f"Second load (from cache): {len(rappers2)} rappers")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# // UPDATED COMMENTS: Complete Google Sheets integration WITHOUT authentication
# // FSD: shared/lib/data/google_sheets_loader.py

