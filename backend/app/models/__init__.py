"""Import every model here so Alembic autogenerate sees the full metadata."""
from app.models.base import Base
from app.models.user import User, UserRole

__all__ = ["Base", "User", "UserRole"]
