import secrets

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "__Host-shulelink_access"
REFRESH_COOKIE = "__Host-shulelink_refresh"
CSRF_COOKIE = "__Host-shulelink_csrf"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str | None = None) -> str:
    csrf = csrf_token or secrets.token_urlsafe(settings.csrf_token_bytes)
    common = {
        "secure": settings.auth_cookie_secure,
        "httponly": True,
        "samesite": settings.auth_cookie_samesite.lower(),
        "path": "/",
    }
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.access_token_minutes * 60, **common)
    response.set_cookie(REFRESH_COOKIE, refresh_token, max_age=settings.refresh_token_days * 86400, **common)
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=settings.refresh_token_days * 86400,
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite=settings.auth_cookie_samesite.lower(),
        path="/",
    )
    return csrf


def clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")
