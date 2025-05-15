from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger

from app.core.database import Base, str_uniq


class Agree_Policy(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str_uniq]

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"
