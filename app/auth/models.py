"""SQLAlchemy model for authenticated users."""

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import Role
from app.common.models import TimestampMixin, UUIDMixin
from app.core.database import Base


class User(UUIDMixin, TimestampMixin, Base):
    """An account that can authenticate and act with a given role."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="user_role"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
