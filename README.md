from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Integer, String, Boolean

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    uid: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    gender: Mapped[str] = mapped_column(String(20), default="")

    age: Mapped[int] = mapped_column(Integer, default=0)

    language: Mapped[str] = mapped_column(String(5), default="ru")

    reputation: Mapped[int] = mapped_column(Integer, default=100)

    premium: Mapped[bool] = mapped_column(Boolean, default=False)

    banned: Mapped[bool] = mapped_column(Boolean, default=False)
