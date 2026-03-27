"""Data models — Pydantic schemas and domain objects."""

from pydantic import BaseModel


class User(BaseModel):
    """User card data."""

    id: int
    name: str
    email: str
    avatar: str = "/static/images/default.svg"


class Todo(BaseModel):
    """Single todo entry."""

    text: str
    done: bool = False
