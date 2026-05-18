from fastapi import APIRouter, Depends, HTTPException, status

from backend import database as db
from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_google_id_token,
    verify_password,
    verify_telegram_init_data,
    _user_dict_to_model,
)
from backend.models import (
    AuthResponse,
    GoogleLogin,
    TelegramWebAppLogin,
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
    if not user_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not user_row["password_hash"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Этот аккаунт привязан к Google. Нажми «Войти через Google».",
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


@router.post("/telegram-webapp", response_model=AuthResponse)
async def telegram_webapp_login(payload: TelegramWebAppLogin):
    """Логин через Telegram Mini App initData.

    Фронт отдаёт нам ровно ту строку, что лежит в ``window.Telegram.WebApp.initData``.
    Мы проверяем HMAC-подпись токеном бота, и если она валидна — ищем юзера по
    ``telegram_id`` или создаём нового (с синтетическим email вида
    ``tg<id>@telegram.local``, у Telegram email не выдаётся).
    """
    data = verify_telegram_init_data(payload.init_data)
    tg_user = data["user"]
    telegram_id = int(tg_user["id"])

    user_row = await db.get_user_by_telegram_id(telegram_id)
    if user_row:
        return await _issue(user_row)

    # Первый в системе юзер забирает «бесхозную» библиотеку.
    is_first_user = not await db.has_any_users()

    # Telegram не отдаёт email — выдаём синтетический. Если юзер потом
    # привяжет реальный email/Google, мы просто перепишем поле.
    synthetic_email = f"tg{telegram_id}@telegram.local"
    name_parts = [tg_user.get("first_name") or "", tg_user.get("last_name") or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or tg_user.get("username")

    user_row = await db.create_user(
        email=synthetic_email,
        telegram_id=telegram_id,
        name=full_name,
        avatar_url=tg_user.get("photo_url"),
    )
    if is_first_user:
        claimed = await db.claim_orphan_library_for_user(user_row["id"])
        if claimed:
            print(f"[auth] первый юзер tg:{telegram_id} забрал {claimed} фильмов")

    return await _issue(user_row)


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
