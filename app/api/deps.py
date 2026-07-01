import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _CREDENTIALS_EXC

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if current.role != UserRole.CENTRAL_ADMIN:
        raise HTTPException(status_code=403, detail="Central Admin role required")
    return current


def require_picker(current: User = Depends(get_current_user)) -> User:
    if current.role != UserRole.HUB_PICKER:
        raise HTTPException(status_code=403, detail="Hub Picker role required")
    return current
