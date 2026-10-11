import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from schemas import UserCreate, UserResponse, TokenResponse





from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from models import User
from db import SessionLocal


router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
TOKEN_EXPIRE_MINUTES = 30
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "development-only-change-this-secret-before-deployment",
)
JWT_ALGORITHM = "HS256"




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${_encode_segment(salt)}${_encode_segment(digest)}"


def _verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, rounds_text, salt_text, digest_text = encoded_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        salt = _decode_segment(salt_text)
        expected = _decode_segment(digest_text)
    except (TypeError, ValueError, binascii.Error):
        return False
    try:
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
    except (TypeError, ValueError, OverflowError):
        return False
    return hmac.compare_digest(actual, expected)


def _create_access_token(username: str) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": username,
        "exp": int(
            (datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)).timestamp()
        ),
    }
    header_segment = _encode_segment(json.dumps(header, separators=(",", ":")).encode())
    payload_segment = _encode_segment(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_segment}.{payload_segment}.{_encode_segment(signature)}"


def _decode_access_token(token: str) -> str:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
        expected_signature = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(
            expected_signature, _decode_segment(signature_segment)
        ):
            raise ValueError("Invalid token signature")
        header = json.loads(_decode_segment(header_segment))
        payload = json.loads(_decode_segment(payload_segment))
        if header.get("alg") != JWT_ALGORITHM or header.get("typ") != "JWT":
            raise ValueError("Invalid token header")
        if not isinstance(payload.get("sub"), str) or payload["exp"] <= datetime.now(
            timezone.utc
        ).timestamp():
            raise ValueError("Expired token")
        return payload["sub"]
    except (
        KeyError,
        TypeError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def _authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not _verify_password(password, user.password_hash):
        return None
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
        )
    user = User(
        username=user_data.username,
        password_hash=_hash_password(user_data.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
        ) from None
    db.refresh(user)
    return user


@router.post("/token", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = _authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=_create_access_token(user.username),
        token_type="bearer",
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    username = _decode_access_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user
