from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["admin", "user", "agent"]


class User(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Role = "user"


class CreateUserForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Role = "user"


class UpdateUserForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: Role = "user"


class HomeProps(BaseModel):
    title: str = "PJX Demo"
    users: list[User] = []


class UserCardProps(BaseModel):
    id: int
    name: str
    email: str
    role: Role


class UserDetailProps(BaseModel):
    user: User
