from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
import json

class GetWeatherArgs(BaseModel):
    location: str = Field(..., description="City name or 'City, Country' or 'lat,lon'")
    units: Literal["metric", "imperial"] = Field("metric", description="Unit system")

class GetWeatherForecastArgs(BaseModel):
    location: str = Field(..., description="City name or 'City, Country' or 'lat,lon'")
    days_ahead: int = Field(..., ge=1, le=7, description="Number of days ahead for forecast (1-7)")

class GetNewsArgs(BaseModel):
    topic: Optional[str] = Field("general", description="News topic keyword or 'general' for top headlines")
    limit: int = Field(3, ge=1, le=10, description="Number of articles")

class WebSearchArgs(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(5, ge=1, le=10, description="Number of results")

class GetSchoolInfoArgs(BaseModel):
    school_name: str = Field(..., description="Name of the school")

class GetDeveloperInfoArgs(BaseModel):
    developer_name: str = Field(..., description="Name of the developer")

class SearchPersonArgs(BaseModel):
    person_name: str = Field(..., description="Name of the person to search for")

class GetRobotInfoArgs(BaseModel):
    query: str = Field(..., description="Query about the robot (e.g., 'who are you', 'what are you', 'tell me about yourself', etc.)")

class ControlDeviceArgs(BaseModel):
    device_id: str = Field(..., description="Device ID")
    action: str = Field(..., description="Action to perform")
    params: Optional[Union[dict, str]] = Field(default_factory=dict, description="Action parameters. Can be a dict or JSON string.")
    
    @field_validator('params', mode='before')
    @classmethod
    def parse_params(cls, v):
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if isinstance(v, dict) else {}
