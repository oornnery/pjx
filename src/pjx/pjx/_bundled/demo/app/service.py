from __future__ import annotations

from fastapi import HTTPException

from .models import CreateUserForm, UpdateUserForm, User


class UserService:
    def __init__(self) -> None:
        self._users: list[User] = [
            User(id=1, name="Alice", email="alice@example.com", role="admin"),
            User(id=2, name="Bob", email="bob@example.com", role="user"),
        ]
        self._next_id = 3

    def list_all(self) -> list[User]:
        return list(self._users)

    def get(self, user_id: int) -> User:
        user = next((u for u in self._users if u.id == user_id), None)
        if user is None:
            raise HTTPException(status_code=404)
        return user

    def create(self, data: CreateUserForm) -> User:
        user = User(id=self._next_id, name=data.name, email=data.email, role=data.role)
        self._users.append(user)
        self._next_id += 1
        return user

    def update(self, user_id: int, data: UpdateUserForm) -> User:
        user = self.get(user_id)
        user.name = data.name
        user.email = data.email
        user.role = data.role
        return user

    def delete(self, user_id: int) -> None:
        self._users = [u for u in self._users if u.id != user_id]
