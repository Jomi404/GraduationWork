from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class AdminModel(BaseModel):
    id: int
    telegram_id: int
    name: str
    created_at: datetime = Field(..., description="Policy creation time")
    updated_at: datetime = Field(..., description="Time of the last policy update")

    model_config = ConfigDict(from_attributes=True)
