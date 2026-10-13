import hashlib
import hmac
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from guard.config import settings
from guard.db import LoginAttempt, Session, User, db

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("not-a-real-account-password")


def digest(token: str) -> str:
    return hmac.new(settings().session_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def issue_session(s, user: User, response: Response) -> dict:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    s.add(Session(token_hash=digest(token), user_id=user.id, csrf=csrf, expires=time.time() + 28800))
    s.commit()
    response.set_cookie("skg_session", token, httponly=True, secure=settings().cookie_secure,
                        samesite="strict", max_age=28800, path="/")
    return {"id": user.id, "username": user.username, "role": user.role, "csrf": csrf}


def login(username: str, password: str, request: Request, response: Response) -> dict:
    source = request.client.host if request.client else "unknown"
    with db() as s:
        s.execute(delete(LoginAttempt).where(LoginAttempt.created < time.time() - 300))
        count = s.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.source == source))
        if count >= 8:
            raise HTTPException(429, "Too many login attempts; try again in five minutes")
        s.add(LoginAttempt(source=source))
        s.commit()
        user = s.scalar(select(User).where(User.username == username))
        try:
            valid = hasher.verify(user.password_hash if user else DUMMY_HASH, password)
        except VerificationError:
            valid = False
        if not valid or not user:
            raise HTTPException(401, "Invalid username or password")
        return issue_session(s, user, response)


def current_user(request: Request) -> User:
    token = request.cookies.get("skg_session", "")
    with db() as s:
        session = s.get(Session, digest(token))
        if not session or session.expires < time.time():
            raise HTTPException(401, "Session expired; sign in")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("x-csrf-token", "")
            if not hmac.compare_digest(supplied, session.csrf):
                raise HTTPException(403, "CSRF validation failed")
            origin = request.headers.get("origin")
            if origin and origin != settings().app_base_url.rstrip("/"):
                raise HTTPException(403, "Origin not allowed")
        user = s.get(User, session.user_id)
        if not user:
            raise HTTPException(401, "Account unavailable")
        return user


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")


def register(username: str, password: str, request: Request, response: Response):
    source = "register:" + (request.client.host if request.client else "unknown")
    with db() as s:
        s.execute(delete(LoginAttempt).where(LoginAttempt.created < time.time() - 300))
        count = s.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.source == source))
        if count >= 8:
            raise HTTPException(429, "Too many signup attempts; try again in five minutes")
        s.add(LoginAttempt(source=source))
        s.commit()
        user = User(username=username, password_hash=hasher.hash(password), role="user")
        s.add(user)
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            raise HTTPException(409, "This username is unavailable")
        return issue_session(s, user, response)


def require_operator(user: User):
    if user.role not in ("admin", "operator"):
        raise HTTPException(403, "A controlled operator account is required for supplier submissions")
