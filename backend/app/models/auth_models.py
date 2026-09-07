from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class User(Base):
    """
    Single-admin demo auth (see main.py's lifespan for the seeding logic
    and Settings.ADMIN_USERNAME/ADMIN_PASSWORD for the seeded credentials).
    Not a public-registration system — there's no POST /auth/register
    endpoint by design, since this project has one operator role, not a
    multi-tenant user base. password_hash is a bcrypt hash, never the raw
    password (see app/core/security.py).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime, server_default=func.now())
