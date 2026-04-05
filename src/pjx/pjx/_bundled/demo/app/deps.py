from .service import UserService

_user_service = UserService()


def get_user_service() -> UserService:
    return _user_service
