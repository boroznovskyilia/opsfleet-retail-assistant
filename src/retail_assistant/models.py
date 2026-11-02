"""Local ORM mappings; column names and JSON encoding preserve existing databases."""

from sqlalchemy import JSON, CheckConstraint, Integer, Text, column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text)
    period: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(Text)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text)
    thread: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    hash: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(Text)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text)
    thread: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    selection: Mapped[list] = mapped_column(JSON)
    receipt: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    created: Mapped[str] = mapped_column(Text)


class Spend(Base):
    __tablename__ = "spend"
    __table_args__ = (CheckConstraint(column("micros") >= 0),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    micros: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(Text)
