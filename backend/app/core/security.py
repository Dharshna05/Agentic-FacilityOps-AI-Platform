"""
Auth primitives: bcrypt password hashing + JWT issue/verify, plus the
`get_current_user` FastAPI dependency used to protect mutation endpoints
(see app/api/*_routes.py's /records POST/DELETE routes).

Scope decision (documented here since it's not obvious from the code
alone): this protects the DATA-MANAGEMENT actions (manually adding/
deleting a record) across all five domains — not the read-only dashboard
GETs, and not /ingest or /ingest/upload (bulk-loading a dataset is closer
to "system setup" than an end-user action, and gating it would have meant
rewriting the auth flow into every existing test file's setup step rather
than just the ones that actually exercise manual record management).
"""
import os
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.auth_models import User

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB (shouldn't happen via normal seeding,
        # but fail closed rather than raising a 500 for a bad login attempt)
        return False


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Returns the username, or raises jwt exceptions on invalid/expired tokens."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    return payload["sub"]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — add `Depends(get_current_user)` to any route that
    should require a valid Bearer token. Raises 401 with a clear reason
    (missing/invalid/expired) rather than a bare 401 with no detail, since
    "why did my request just get rejected" is exactly the kind of thing
    that's frustrating to debug blind (same philosophy as the AI-provider
    /api/system/ai-status diagnostic added earlier in this project).
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header — log in via /api/auth/login first.")
    try:
        username = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired — please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token.")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")
    return user


def require_role(*allowed_roles: str):
    """
    FastAPI dependency FACTORY — `Depends(require_role("admin"))` requires
    a valid token AND that user's role in `allowed_roles`. Layered on top
    of get_current_user rather than duplicating it, so every route that
    needs a specific role still gets the same missing/expired/invalid
    error messages for free.

    Roles (see User.role): "admin" (full access, including user
    management) and "technician" (can manage records but not create/
    delete other users). There's no separate "viewer" role with its own
    restrictions YET — every dashboard GET is already unauthenticated by
    design (see this module's docstring), so a read-only role has nothing
    left to restrict until/unless the read side also moves behind auth.
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)} (you are '{current_user.role}').",
            )
        return current_user
    return dependency
