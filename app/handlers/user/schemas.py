from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


class AgreePolicyModel(BaseModel):
    id: Optional[int] = None
    telegram_id: int
    name: str
    created_at: Optional[datetime] = Field(None, description="Policy creation time")
    updated_at: Optional[datetime] = Field(None, description="Time of the last policy update")

    model_config = ConfigDict(from_attributes=True)
