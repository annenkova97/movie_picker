from telegram import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ApplicationHandlerStop, ContextTypes

from backend import database as db
from backend.config import MINI_APP_URL
from backend.services import book_search
from backend.services.omdb import omdb_service
from backend.services.llm import llm_service
from handlers.formatting import imdb_suffix


def _saved_confirmation_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard for the design §6.3 Save Confirmation card.

    Row 1: open the Mini-App (WebApp button) — only added if MINI_APP_URL
    is configured; otherwise users open the app via BotFather's menu.
    Row 2: corrective actions — "Не тот фильм?" and "Удалить".
    """
    rows: list[list[InlineKeyboardButton]] = []
    if MINI_APP_URL:
        rows.append([
            InlineKeyboardButton(
                "📖 Открыть в Lentochka",
                web_app=WebAppInfo(url=MINI_APP_URL),
            ),
        ])
    rows.append([
        InlineKeyboardButton("Не тот фильм?", callback_data=f"wrong:{movie_id}"),
        InlineKeyboardButton("Удалить", callback_data=f"delete:{movie_id}"),
    ])
    return InlineKeyboardMarkup(rows)


async def _get_or_create_user(tg_user) -> dict:
    """Находит или создаёт юзера в БД по telegram_id из callback'а.

    Telegram не отдаёт email, поэтому выдаём синтетический ``tg<id>@telegram.local``.
    Тот же подход используется в /auth/telegram-webapp на фронте — поэтому
    юзер, добавивший фильмы в боте, видит их же при открытии Mini App.
    """
    telegram_id = int(tg_user.id)
    row = await db.get_user_by_telegram_id(telegram_id)
    if row:
        return row

    name_parts = [tg_user.first_name or "", tg_user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p).strip() or (tg_user.username or "")
    return await db.create_user(
        # Synthetic email — example.com зарезервирован RFC 2606.
        email=f"tg{telegram_id}@tg.example.com",
        telegram_id=telegram_id,
        name=full_name or None,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback-кнопок"""
    query = update.callback_query
    await query.answer()

    user_row = await _get_or_create_user(query.from_user)
    user_id = user_row["id"]

    data = query.data
    action, value = data.split(":", 1)

    if action == "add":
        await _handle_add(query, value, user_id=user_id)
    elif action == "watch":
        await _handle_watch(query, int(value), user_id=user_id, watched=True)
    elif action == "unwatch":
        await _handle_watch(query, int(value), user_id=user_id, watched=False)
    elif action == "delete":
        await _handle_delete(query, int(value), user_id=user_id)
    elif action == "wrong":
        await _handle_wrong(query, int(value), user_id=user_id)
    elif action == "addbook":
        await _handle_add_book(query, value, user_id=user_id)
    elif action == "readbook":
        await _handle_read(query, int(value), user_id=user_id, read=True)
    elif action == "unreadbook":
        await _handle_read(query, int(value), user_id=user_id, read=False)
    elif action == "rate":
        await _handle_rate(query, value, user_id=user_id, context=context)


async def _handle_add(query, imdb_id: str, *, user_id: int):
    """Сохраняет фильм в библиотеку и переключает карточку в Save Confirmation.

    На карточке-превью кнопка «+ Сохранить» меняется на дизайн-спека ряд
    «Открыть в Lentochka / Не тот фильм? / Удалить». Дополнительно
    отправляется короткое подтверждение в голосе бренда («сохранила»).
    """
    existing = await db.get_user_movie_by_imdb_id(imdb_id, user_id)
    if existing:
        await query.edit_message_reply_markup(
            reply_markup=_saved_confirmation_keyboard(existing.id),
        )
        await query.message.reply_text(
            f"«{existing.title}» уже в твоём списке."
        )
        return

    movie_base = await omdb_service.get_movie_by_id(imdb_id)
    if not movie_base:
        await query.message.reply_text("Не получилось загрузить фильм.")
        return

    if movie_base.plot:
        try:
            description = await llm_service.generate_short_description(
                movie_base.plot, movie_base.title
            )
            movie_base.description = description
        except Exception:
            pass

    movie = await db.add_movie(movie_base, user_id=user_id, source="telegram")

    # Swap the preview keyboard for the Save Confirmation row.
    await query.edit_message_reply_markup(
        reply_markup=_saved_confirmation_keyboard(movie.id),
    )

    rating = imdb_suffix(movie.imdb_rating, ", IMDb ")
    await query.message.reply_text(
        f"*{movie.title}* — сохранила{rating}.",
        parse_mode="Markdown",
    )


async def _handle_wrong(query, movie_id: int, *, user_id: int):
    """«Не тот фильм?» — удаляет сохранение и подсказывает, как переподобрать."""
    movie = await db.get_movie_by_id(movie_id, user_id=user_id)
    title = movie.title if movie else "Фильм"

    await db.delete_movie(movie_id, user_id=user_id)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"Убрала «{title}» из списка. Напиши название текстом — поищу заново."
    )


async def _handle_watch(query, movie_id: int, *, user_id: int, watched: bool):
    """Отметить фильм просмотренным/непросмотренным."""
    movie = await db.update_movie(movie_id, user_id=user_id, is_watched=watched)
    if not movie:
        await query.message.reply_text("Фильм не нашла.")
        return

    status = "посмотрен ✅" if watched else "вернула в список 🎬"
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"*{movie.title}* — {status}", parse_mode="Markdown"
    )
    if watched:
        await query.message.reply_text(
            "Как тебе? Поставь оценку:",
            reply_markup=_rating_keyboard("movie", movie.id),
        )


# ── books ──────────────────────────────────────────────────────────────────


async def _handle_add_book(query, work_key: str, *, user_id: int):
    """Сохраняет книгу в библиотеку и переключает карточку в подтверждение."""
    existing = await db.get_user_book_by_work_key(work_key, user_id)
    if existing:
        await query.edit_message_reply_markup(
            reply_markup=_book_saved_keyboard(existing.id, existing.is_read),
        )
        await query.message.reply_text(f"«{existing.title}» уже в твоих книгах.")
        return

    book_base = await book_search.get_book_by_key(work_key)
    if not book_base:
        await query.message.reply_text("Не получилось загрузить книгу.")
        return

    book = await db.add_book(book_base, user_id=user_id, source="telegram")
    await query.edit_message_reply_markup(
        reply_markup=_book_saved_keyboard(book.id, book.is_read),
    )
    await query.message.reply_text(
        f"*{book.title}* — сохранила в книги.", parse_mode="Markdown",
    )


async def _handle_read(query, book_id: int, *, user_id: int, read: bool):
    """Отметить книгу прочитанной/непрочитанной."""
    book = await db.update_book(book_id, user_id=user_id, is_read=read)
    if not book:
        await query.message.reply_text("Книгу не нашла.")
        return

    status = "прочитана ✅" if read else "вернула к чтению 📚"
    await query.edit_message_reply_markup(
        reply_markup=_book_saved_keyboard(book.id, book.is_read),
    )
    await query.message.reply_text(f"*{book.title}* — {status}", parse_mode="Markdown")
    if read:
        await query.message.reply_text(
            "Как тебе? Поставь оценку:",
            reply_markup=_rating_keyboard("book", book.id),
        )


def _book_saved_keyboard(book_id: int, is_read: bool) -> InlineKeyboardMarkup:
    """Ряд действий под сохранённой книгой."""
    read_btn = (
        InlineKeyboardButton("↺ Не прочитана", callback_data=f"unreadbook:{book_id}")
        if is_read
        else InlineKeyboardButton("✓ Прочитана", callback_data=f"readbook:{book_id}")
    )
    return InlineKeyboardMarkup([[read_btn]])


# ── rating (diary on bot) ───────────────────────────────────────────────────


def _rating_keyboard(kind: str, item_id: int) -> InlineKeyboardMarkup:
    """Ряд из пяти звёзд. callback ``rate:<kind>:<id>:<n>``."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐" * n, callback_data=f"rate:{kind}:{item_id}:{n}")
        for n in range(1, 6)
    ]])


async def _handle_rate(query, value: str, *, user_id: int, context):
    """Сохраняет личную оценку и предлагает добавить заметку (ForceReply)."""
    try:
        kind, id_str, n_str = value.split(":")
        item_id, rating = int(id_str), int(n_str)
    except ValueError:
        return

    if kind == "movie":
        await db.update_movie(item_id, user_id=user_id, user_rating=rating)
    else:
        await db.update_book(item_id, user_id=user_id, user_rating=rating)

    await query.edit_message_text(f"Оценка {'⭐' * rating} сохранена.")
    # Запоминаем, к чему относится следующая текстовая заметка-ответ.
    context.user_data["await_note"] = (kind, item_id)
    await query.message.reply_text(
        "Хочешь оставить заметку на память? Ответь на это сообщение "
        "(или просто пропусти).",
        reply_markup=ForceReply(selective=True),
    )


async def note_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ловит ответ-заметку после оценки. Регистрируется в группе -1.

    Если ждём заметку (``await_note`` в user_data) — сохраняем и стопаем
    дальнейшую обработку; иначе молча пропускаем, чтобы обычный текст ушёл
    в text_handler.
    """
    pending = context.user_data.get("await_note")
    if not pending:
        return
    kind, item_id = pending
    context.user_data.pop("await_note", None)

    note = (update.message.text or "").strip()
    user_row = await _get_or_create_user(update.effective_user)
    uid = user_row["id"]
    if kind == "movie":
        await db.update_movie(item_id, user_id=uid, user_note=note)
    else:
        await db.update_book(item_id, user_id=uid, user_note=note)

    await update.message.reply_text("Записала ✍️")
    raise ApplicationHandlerStop


async def _handle_delete(query, movie_id: int, *, user_id: int):
    """Удаление фильма из библиотеки юзера."""
    movie = await db.get_movie_by_id(movie_id, user_id=user_id)
    title = movie.title if movie else "Фильм"

    success = await db.delete_movie(movie_id, user_id=user_id)
    if not success:
        await query.message.reply_text("Фильм не нашла.")
        return

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"«{title}» — удалила из списка.")
