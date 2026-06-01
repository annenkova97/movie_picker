import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend import database as db
from backend.config import TELEGRAM_BOT_TOKEN
from backend.rate_limit import limiter
from backend.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_google_id_token,
    verify_password,
    verify_telegram_init_data,
    verify_telegram_login_widget,
    _user_dict_to_model,
)
from backend.models import (
    AuthResponse,
    GoogleLogin,
    TelegramWebAppLogin,
    TelegramWidgetLogin,
    User,
    UserCreate,
    UserLogin,
)


router = APIRouter(prefix="/auth", tags=["auth"])


# Кэш юзернейма бота — вытаскиваем один раз через /getMe, дальше отдаём из памяти.
_bot_username_cache: dict[str, str | None] = {}


async def _get_bot_username() -> str | None:
    if "username" in _bot_username_cache:
        return _bot_username_cache["username"]
    if not TELEGRAM_BOT_TOKEN:
        _bot_username_cache["username"] = None
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
            )
        data = r.json() if r.status_code == 200 else {}
        username = data.get("result", {}).get("username") if data.get("ok") else None
    except Exception:
        username = None
    _bot_username_cache["username"] = username
    return username


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


async def _issue_for_telegram_user(tg_user: dict) -> AuthResponse:
    """Общий хвост для /telegram-webapp и /telegram-widget.

    Принимает уже проверенный TG-payload (id обязателен, остальное — best-effort)
    и либо логинит существующего юзера, либо создаёт нового с синтетическим email.
    """
    telegram_id = int(tg_user["id"])

    user_row = await db.get_user_by_telegram_id(telegram_id)
    if user_row:
        return await _issue(user_row)

    # Telegram не отдаёт email — выдаём синтетический.
    # example.com зарезервирован RFC 2606 и проходит EmailStr-валидацию.
    synthetic_email = f"tg{telegram_id}@tg.example.com"
    name_parts = [tg_user.get("first_name") or "", tg_user.get("last_name") or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or tg_user.get("username")

    user_row = await db.create_user(
        email=synthetic_email,
        telegram_id=telegram_id,
        name=full_name,
        avatar_url=tg_user.get("photo_url"),
    )

    return await _issue(user_row)


@router.post("/telegram-webapp", response_model=AuthResponse)
async def telegram_webapp_login(payload: TelegramWebAppLogin):
    """Логин через Telegram Mini App initData (юзер открыл наш Mini App в Telegram)."""
    data = verify_telegram_init_data(payload.init_data)
    return await _issue_for_telegram_user(data["user"])


@router.post("/telegram-widget", response_model=AuthResponse)
async def telegram_widget_login(payload: TelegramWidgetLogin):
    """Логин через Telegram Login Widget (юзер на внешнем сайте нажал «Войти через Telegram»).

    Подпись здесь считается по-другому (см. verify_telegram_login_widget), но
    конечный flow тот же: находим/создаём юзера по telegram_id и выдаём JWT.
    """
    tg_user = verify_telegram_login_widget(payload.model_dump())
    return await _issue_for_telegram_user(tg_user)


@router.get("/telegram-bot-info")
async def telegram_bot_info():
    """Отдаёт юзернейм бота, нужный фронту для рендера Telegram Login Widget.

    Кнопка-виджет создаётся скриптом с ``data-telegram-login="<username>"``;
    мы достаём username из /getMe, чтобы не дублировать его в env-переменных фронта.
    """
    username = await _get_bot_username()
    return {"username": username, "enabled": bool(username)}


@router.get("/me", response_model=User)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
