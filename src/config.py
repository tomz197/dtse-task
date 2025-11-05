"""Application state management."""
from typing import Optional

from src.database import DatabaseManager
from src.model import HousingModel

housing_model: Optional[HousingModel] = None
db_manager: Optional[DatabaseManager] = None

