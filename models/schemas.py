from pydantic import BaseModel
from typing import Optional

class WeatherData(BaseModel):
    temp: int
    humidity: int
    description: str
    rainfall: float = 0.0

class RecommendationResult(BaseModel):
    county: str
    farm_type: str
    soil_type: Optional[str] = None
    avg_rainfall: Optional[float] = None
    avg_temp: Optional[float] = None
    recommendation: str
    advice: str
    weather: Optional[WeatherData] = None
