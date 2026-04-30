from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend import database as db
from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_google_id_token,
    verify_password,
    _user_dict_to_model,
)
from backend.models import (
    AuthResponse,
    GoogleLogin,
    User,
    UserCreate,
    UserLogin,
)
from backend.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue(user_row: dict) -> AuthResponse:
    user = _user_dict_to_model(user_row)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user)


@router.post("/register", response_model=AuthResponse)
@limiter.limit("5/hour")
async def register(request: Request, payload: UserCreate):
    existing = await db.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже есть. Войдите или используйте Google.",
        )
    user_row = await db.create_user(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    return await _issue(user_row)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin):
    user_row = await db.get_user_by_email(payload.email)
    if not user_row or not user_row["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not verify_password(payload.password, user_row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    return await _issue(user_row)


@router.post("/google", response_model=AuthResponse)
@limiter.limit("20/minute")
async def google_login(request: Request, payload: GoogleLogin):
    claims = verify_google_id_token(payload.id_token)
    google_sub = claims["sub"]
    email = claims.get("email", "").lower()
    name = claims.get("name")
    picture = claims.get("picture")

    user_row = await db.get_user_by_google_sub(google_sub)
    if not user_row and email:
        # пользователь уже есть по email — прилинкуем Google
        user_row = await db.get_user_by_email(email)
        if user_row:
            await db.attach_google_sub(user_row["id"], google_sub, picture)
            user_row = await db.get_user_by_id(user_row["id"])

    if not user_row:
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google не вернул email",
            )
        user_row = await db.create_user(
            email=email,
            google_sub=google_sub,
            name=name,
            avatar_url=picture,
        )

    return await _issue(user_row)


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
