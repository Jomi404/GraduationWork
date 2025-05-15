from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger

from app.core.database import Base, str_uniq


class Admin(Base):
    """A model for storing admin information.
    Fields:
        id: int - The unique identifier of the record.
        tg_id: bigint - Telegram user ID associated with the admin.
        name: str - The name of the admin.
        created_at: datetime - Time when the admin record was created.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str_uniq]

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
