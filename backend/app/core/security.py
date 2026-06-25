from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str


def principal_from_authorization(
    authorization: str | None,
    settings: Settings,
) -> Principal:
    if settings.is_development and (not authorization or authorization == "Bearer demo-token"):
        return Principal(user_id=settings.DEMO_USER_ID, email=settings.DEMO_USER_EMAIL)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY:
        try:
            response = httpx.get(
                f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.SUPABASE_ANON_KEY,
                },
                timeout=10,
            )
            response.raise_for_status()
            user = response.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Supabase access token.",
            ) from exc

        user_id = user.get("id")
        email = user.get("email")
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase user is missing identity.",
            )
        return Principal(user_id=str(user_id), email=str(email))

    try:
        import jwt

        payload = jwt.decode(
            token,
            settings.SUPABASE_SECRET_KEY,
            algorithms=["HS256"],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=settings.SUPABASE_JWT_ISSUER,
            options={"verify_iss": bool(settings.SUPABASE_JWT_ISSUER)},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc

    user_id = payload.get("sub")
    email = payload.get("email") or payload.get("user_metadata", {}).get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is missing user identity.",
        )
    return Principal(user_id=str(user_id), email=str(email))


def get_current_principal(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> Principal:
    return principal_from_authorization(authorization, settings)
