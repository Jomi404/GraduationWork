from sqlalchemy import String, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Privacy_Policy(Base):
    """A model for storing a privacy policy.
    Fields:
        id: int is the unique identifier of the record.
        content_json: jsonb - Policy sections in the format {"introduction": "Text", ...}.
        version: str - Policy version (for example, "1.0").
        created_at: datetime - Policy creation time.
        updated_at: datetime - Time of the last policy update.
        is_active: boolean - Flag indicating the active version of the policy.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
