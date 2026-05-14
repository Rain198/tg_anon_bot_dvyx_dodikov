from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    uid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    gender: Mapped[str] = mapped_column(String(20), default="")
    preferred_gender: Mapped[str] = mapped_column(String(20), default="any")
    age: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    interests: Mapped[str] = mapped_column(Text, default="")
    reputation: Mapped[int] = mapped_column(Integer, default=100)
    premium: Mapped[bool] = mapped_column(Boolean, default=False)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    shadow_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_emoji: Mapped[str] = mapped_column(String(16), default="⭐")
    custom_status: Mapped[str] = mapped_column(String(120), default="")
    theme: Mapped[str] = mapped_column(String(40), default="default")
    chats_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    reports: Mapped[list["Report"]] = relationship(back_populates="reported_user")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, index=True)
    reported_id: Mapped[int] = mapped_column(ForeignKey("users.uid"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

    reported_user: Mapped[User] = relationship(back_populates="reports")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    partner_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
