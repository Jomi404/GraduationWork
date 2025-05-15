from pydantic import BaseModel, ConfigDict


class TelegramIDModel(BaseModel):
    telegram_id: int

    model_config = ConfigDict(from_attributes=True)


class PrivacyPolicyFilter(BaseModel):
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
