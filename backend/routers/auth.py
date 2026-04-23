from fastapi import APIRouter, Depends, HTTPException, status

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


router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue(user_row: dict) -> AuthResponse:
    user = _user_dict_to_model(user_row)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=user)


@router.post("/register", response_model=AuthResponse)
async def register(payload: UserCreate):
    existing = await db.get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже есть. Войдите или используйте Google.",
        )
    # Первый зарегистрировавшийся забирает себе историческую библиотеку (62 фильма без владельца).
    is_first_user = not await db.has_any_users()

    user_row = await db.create_user(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )

    if is_first_user:
        claimed = await db.claim_orphan_library_for_user(user_row["id"])
        if claimed:
            print(f"[auth] первый юзер {user_row['email']} забрал {claimed} фильмов")

    return await _issue(user_row)


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin):
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
async def google_login(payload: GoogleLogin):
    claims = verify_google_id_token(payload.id_token)
    google_sub = claims["sub"]
    email = claims.get("email", "").lower()
    name = claims.get("name")
    picture = claims.get("picture")

    is_first_user = not await db.has_any_users()

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
        if is_first_user:
            claimed = await db.claim_orphan_library_for_user(user_row["id"])
            if claimed:
                print(f"[auth] первый юзер {user_row['email']} забрал {claimed} фильмов")

    return await _issue(user_row)


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
